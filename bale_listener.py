#!/usr/bin/env python3

from pathlib import Path
import os
import time
import requests
import json
from bale_transport import send_message as transport_send

MENU_MARKUP = {
    "inline_keyboard": [
        [{"text": "📊 گزارش ۱۵ فرصت برتر", "callback_data": "report_ranked_15"}],
        [{"text": "📈 گزارش ۱۵ قرارداد فعال", "callback_data": "report_activity_15"}],
        [{"text": "📋 وضعیت سیستم", "callback_data": "system_status"}],
    ]
}

REPLY_MENU_MARKUP = {
    "keyboard": [
        [{"text": "📊 گزارش ۱۵ فرصت برتر"}],
        [{"text": "📈 گزارش ۱۵ قرارداد فعال"}],
        [{"text": "🔎 انتخاب نماد"}],
        [{"text": "📋 وضعیت سیستم"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

REPLY_MENU_COMMANDS = {
    "📊 گزارش ۱۵ فرصت برتر": "گزارش",
    "📈 گزارش ۱۵ قرارداد فعال": "فعالیت",
    "🔎 انتخاب نماد": "نمادها",
    "📋 وضعیت سیستم": "وضعیت",
}

SYMBOLS_PER_PAGE = 12
SYMBOL_PAGE_PREFIX = "نمادها صفحه "
SYMBOL_SELECT_PREFIX = "نماد: "

CALLBACK_COMMANDS = {
    "report_ranked_15": "گزارش",
    "report_activity_15": "فعالیت",
    "system_status": "وضعیت",
}

from report_engine import build_tsetmc_report, save_tsetmc_report
from tsetmc_first_source import build_tsetmc_snapshot

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
REPORT_FILE = OUTPUT / "latest_report.txt"
STATE_FILE = OUTPUT / "bale_listener_state.json"

TOKEN = os.getenv("BALE_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("BALE_CHAT_ID", "").strip()

API = f"https://tapi.bale.ai/bot{TOKEN}"


def load_offset():
    if not STATE_FILE.exists():
        return None
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        value = payload.get("next_offset")
        return int(value) if value is not None else None
    except (OSError, ValueError, TypeError):
        raise RuntimeError("Bale listener state قابل خواندن نیست")


def save_offset(next_offset):
    OUTPUT.mkdir(exist_ok=True)
    temporary = STATE_FILE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"next_offset": int(next_offset)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(STATE_FILE)


def normalize_command(text):
    if not text:
        return ""

    return (
        str(text)
        .strip()
        .replace("ي", "ی")
        .replace("ك", "ک")
        .replace("‌", "")
    )


def send_message(chat_id, text, reply_markup=None):
    count = transport_send(TOKEN, chat_id, text, reply_markup=reply_markup)
    print(f"SENT {count}/{count}")


def system_status():
    audit_path = OUTPUT / "latest_audit.json"
    report_path = OUTPUT / "latest_report.txt"

    if not audit_path.exists():
        return "⚠️ وضعیت V4.1\n\nAudit موجود نیست؛ هنوز اجرای معتبر گزارش ثبت نشده است."

    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return "⚠️ وضعیت V4.1\n\nفایل Audit قابل خواندن نیست."

    integrity = audit.get("audit_integrity", {})
    status = integrity.get("status") or audit.get("status") or "UNKNOWN"
    failures = integrity.get("failures") or []
    missing = integrity.get("missing_fields") or []

    lines = [
        "📊 وضعیت OptimusAI V4.1",
        "",
        f"Audit: {status}",
        f"Source: {audit.get('source_of_truth') or 'داده موجود نیست'}",
        f"Data Mode: {audit.get('data_mode') or 'داده موجود نیست'}",
        f"Refresh: {audit.get('live_refresh_status') or 'داده موجود نیست'}",
        f"Scoring: {audit.get('scoring_status') or 'داده موجود نیست'}",
        f"Ranking: {audit.get('ranking_status') or 'داده موجود نیست'}",
        f"Snapshot SHA: {audit.get('snapshot_sha256') or 'داده موجود نیست'}",
        f"Report SHA: {audit.get('report_sha256') or 'داده موجود نیست'}",
    ]

    if failures:
        lines.append("Audit Failures: " + ", ".join(str(x) for x in failures))
    else:
        lines.append("Audit Failures: 0")

    if missing:
        lines.append("Audit Missing Fields: " + ", ".join(str(x) for x in missing))
    else:
        lines.append("Audit Missing Fields: 0")

    if not report_path.exists():
        lines.append("Report File: MISSING")
    else:
        lines.append("Report File: READY")

    return "\n".join(lines)


def generate_report(command):
    if command in ("گزارش", "همه", "کل"):
        report, snapshot = build_tsetmc_report(
            top_count=15,
            flow=None,
            report_mode="RANKED",
        )
    elif command in ("فعالیت", "معاملات", "تاپ"):
        report, snapshot = build_tsetmc_report(
            top_count=15,
            flow=None,
            report_mode="TRADING_ACTIVITY",
        )
    else:
        report, snapshot = build_tsetmc_report(
            top_count=5,
            underlying_symbol=command,
            flow=None,
            report_mode="RANKED",
        )

    save_tsetmc_report(report, snapshot)
    return report


def get_updates(offset=None):
    params = {
        "timeout": 30,
    }

    if offset is not None:
        params["offset"] = offset

    r = requests.get(
        f"{API}/getUpdates",
        params=params,
        timeout=40,
    )

    r.raise_for_status()

    data = r.json()

    if not data.get("ok"):
        raise RuntimeError(f"Bale getUpdates error: {data}")

    return data.get("result", [])


def answer_callback_query(callback_query_id):
    r = requests.post(
        f"{API}/answerCallbackQuery",
        data={"callback_query_id": callback_query_id},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError("Bale answerCallbackQuery rejected")


def _underlying_symbols():
    """Build selectable underlying symbols from the current TSETMC option universe."""
    snapshot = build_tsetmc_snapshot(flow=None, max_instruments=None, symbol_prefix=None)
    symbols = {
        str((row.get("identity") or {}).get("underlying_symbol") or "").strip()
        for row in snapshot.get("rows", [])
    }
    return sorted((symbol for symbol in symbols if symbol), key=lambda value: value)


def send_symbol_menu(chat_id, page=0):
    symbols = _underlying_symbols()
    total_pages = max(1, (len(symbols) + SYMBOLS_PER_PAGE - 1) // SYMBOLS_PER_PAGE)
    page = max(0, min(int(page), total_pages - 1))
    page_symbols = symbols[page * SYMBOLS_PER_PAGE:(page + 1) * SYMBOLS_PER_PAGE]
    keyboard = []
    for index in range(0, len(page_symbols), 2):
        keyboard.append([{"text": f"{SYMBOL_SELECT_PREFIX}{symbol}"} for symbol in page_symbols[index:index + 2]])
    navigation = []
    if page > 0:
        navigation.append({"text": f"{SYMBOL_PAGE_PREFIX}{page}"})
    if page < total_pages - 1:
        navigation.append({"text": f"{SYMBOL_PAGE_PREFIX}{page + 2}"})
    if navigation:
        keyboard.append(navigation)
    keyboard.append([{"text": "🏠 منوی اصلی"}])
    markup = {"keyboard": keyboard, "resize_keyboard": True, "one_time_keyboard": False}
    send_message(chat_id, f"🔎 انتخاب نماد پایه\n\nتعداد نمادهای دارای اختیار معامله در TSETMC: {len(symbols)}\nصفحه {page + 1} از {total_pages}\n\nبا انتخاب هر نماد، ۵ قرارداد برتر آن نماد بر اساس Ranking شش‌بلوک نمایش داده می‌شود:", reply_markup=markup)


def send_report_menu(chat_id):
    send_message(
        chat_id,
        "📋 منوی گزارش‌های OptimusAI V4.1\n\nاز منوی پایین، گزارش موردنظر را انتخاب کنید:",
        reply_markup=REPLY_MENU_MARKUP,
    )


def main():
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("BALE_BOT_TOKEN و BALE_CHAT_ID باید از قبل تنظیم شوند")

    print("====================================")
    print("OptimusAI V4.1 Bale Listener")
    print("====================================")
    print("منو -> دکمه‌های شیشه‌ای گزارش‌های از پیش تعریف‌شده")
    print("گزارش -> 15 فرصت برتر بر اساس رنکینگ 6 بلوکی TSETMC")
    print("نماد  -> 5 فرصت برتر همان نماد پایه بر اساس رنکینگ 6 بلوکی")
    print("فعالیت -> 15 قرارداد برتر از نظر فعالیت معاملاتی")
    print("====================================")

    send_report_menu(CHAT_ID)

    offset = load_offset()

    while True:
        try:
            updates = get_updates(offset)

            for update in updates:
                next_offset = int(update["update_id"]) + 1

                callback = update.get("callback_query") or {}
                if callback:
                    callback_message = callback.get("message") or {}
                    callback_chat = callback_message.get("chat") or {}
                    chat_id = callback_chat.get("id")

                    if not chat_id:
                        save_offset(next_offset)
                        offset = next_offset
                        continue

                    if CHAT_ID and str(chat_id) != str(CHAT_ID):
                        save_offset(next_offset)
                        offset = next_offset
                        continue

                    try:
                        answer_callback_query(callback.get("id"))
                        command = CALLBACK_COMMANDS.get(
                            str(callback.get("data") or "").strip()
                        )
                        if not command:
                            raise RuntimeError("UNKNOWN_CALLBACK")

                        if command == "وضعیت":
                            send_message(chat_id, system_status())
                        else:
                            send_message(chat_id, generate_report(command))

                        send_report_menu(chat_id)
                        print(
                            f"REPORT_OK callback={callback.get('data')}"
                        )
                        save_offset(next_offset)
                        offset = next_offset
                    except Exception as e:
                        print(
                            f"REPORT_ERROR type={type(e).__name__}"
                        )
                    continue

                message = (
                    update.get("message")
                    or update.get("edited_message")
                    or {}
                )

                chat = message.get("chat", {})
                chat_id = chat.get("id")

                text = normalize_command(
                    message.get("text", "")
                )

                if not chat_id or not text:
                    save_offset(next_offset)
                    offset = next_offset
                    continue

                if CHAT_ID and str(chat_id) != str(CHAT_ID):
                    save_offset(next_offset)
                    offset = next_offset
                    continue

                text = REPLY_MENU_COMMANDS.get(text, text)

                print(
                    f"COMMAND = {text} | CHAT_ID = {chat_id}"
                )

                try:
                    if text in ("منو", "menu", "/start", "/menu", "🏠 منوی اصلی"):
                        send_report_menu(chat_id)
                    elif text == "نمادها":
                        send_symbol_menu(chat_id, 0)
                    elif text.startswith(SYMBOL_PAGE_PREFIX):
                        page_number = int(text[len(SYMBOL_PAGE_PREFIX):].strip()) - 1
                        send_symbol_menu(chat_id, page_number)
                    elif text.startswith(SYMBOL_SELECT_PREFIX):
                        symbol = text[len(SYMBOL_SELECT_PREFIX):].strip()
                        if not symbol:
                            raise ValueError("نماد پایه خالی است")
                        report = generate_report(symbol)
                        send_message(chat_id, report)
                        send_report_menu(chat_id)
                    elif text in ("وضعیت", "استاتوس", "status"):
                        send_message(chat_id, system_status())
                        send_report_menu(chat_id)
                    else:
                        report = generate_report(text)
                        send_message(chat_id, report)
                        send_report_menu(chat_id)

                    print(
                        f"REPORT_OK command={text}"
                    )
                    save_offset(next_offset)
                    offset = next_offset

                except Exception as e:
                    print(
                        f"REPORT_ERROR type={type(e).__name__}"
                    )

                    try:
                        send_message(
                            chat_id,
                            "⚠️ خطا در تولید گزارش V4.1\n\n"
                            + "داده یا ارتباط قابل تأیید نیست؛ تولید یا ارسال گزارش کامل نشد.",
                        )
                    except Exception as send_error:
                        print(
                            "ERROR_MESSAGE_SEND_FAILED:",
                            type(send_error).__name__,
                        )
                    else:
                        save_offset(next_offset)
                        offset = next_offset

        except KeyboardInterrupt:
            print("\nLISTENER_STOPPED")
            break

        except Exception as e:
            print("LISTENER_ERROR:", type(e).__name__)
            time.sleep(5)


if __name__ == "__main__":
    main()
