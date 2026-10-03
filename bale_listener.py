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
        [{"text": "🔥 سود لحظه آخری", "callback_data": "report_last_minute"}],
        [{"text": "📈 گزارش ۱۵ قرارداد فعال", "callback_data": "report_activity_15"}],
        [{"text": "🔎 انتخاب نماد", "callback_data": "symbols_page:0"}],
        [{"text": "📋 وضعیت سیستم", "callback_data": "system_status"}],
    ]
}

REPLY_MENU_MARKUP = {
    "keyboard": [
        [{"text": "📊 گزارش ۱۵ فرصت برتر"}],
        [{"text": "🔥 سود لحظه آخری"}],
        [{"text": "📈 گزارش ۱۵ قرارداد فعال"}],
        [{"text": "🔎 انتخاب نماد"}],
        [{"text": "📋 وضعیت سیستم"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

REPLY_MENU_COMMANDS = {
    "📊 گزارش ۱۵ فرصت برتر": "گزارش",
    "🔥 سود لحظه آخری": "سودلحظهآخری",
    "📈 گزارش ۱۵ قرارداد فعال": "فعالیت",
    "🔎 انتخاب نماد": "نمادها",
    "📋 وضعیت سیستم": "وضعیت",
}

SYMBOLS_PER_PAGE = 12
SYMBOL_PAGE_PREFIX = "نمادها صفحه "
SYMBOL_SELECT_PREFIX = "نماد: "

# ثابت‌های پرتکرار/موردنظر کاربر در ابتدای فهرست نمادهای پایه.
# فقط نمادهایی که واقعاً در Universe فعلی TSETMC وجود داشته باشند نمایش داده می‌شوند.
PREFERRED_UNDERLYINGS = (
    "اهرم",
    "وبملت",
    "وتجارت",
    "وبصادر",
    "فزر",
    "تاصیکو",
    "فملی",
    "شستا",
    "خودرو",
    "خساپا",
    "ذوب",
    "شپنا",
    "خبهمن",
    "دارونو",
    "دزاگرس",
)

CALLBACK_COMMANDS = {
    "report_ranked_15": "گزارش",
    "report_activity_15": "فعالیت",
    "report_last_minute": "سودلحظهآخری",
    "system_status": "وضعیت",
}

from report_engine import build_tsetmc_report, save_tsetmc_report
from github_runtime_evidence import publish_latest_evidence
from tsetmc_first_source import build_tsetmc_snapshot
from behavior_engine import build_behavior_report, format_behavior_report
from last_minute_profit_engine import build_last_minute_ranking

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
    if command in ("رفتار", "تغییرات", "behavior"):
        return format_behavior_report(build_behavior_report(ROOT))
    if command in ("سودلحظهآخری", "سود لحظه آخری", "last_minute_profit"):
        snapshot = build_tsetmc_snapshot(flow=None, max_instruments=None, symbol_prefix=None)
        result = build_last_minute_ranking(snapshot.get("rows", []), top_count=15)
        lines = [
            "🔥 سود لحظه آخری",
            "TSETMC-ONLY | سناریوی رشد ۳ درصدی پایه",
            "━━━━━━━━━━━━━━━━━━━━",
            "شرایط: دقیقاً یک روز تا سررسید + ITM + بازده سناریویی مثبت",
            f"تعداد کاندیداهای معتبر: {result.get('candidate_count', 0)}",
            f"تعداد نمایش: {result.get('display_count', 0)}",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
        if not result.get("ranking_rows"):
            lines.append("داده موجود نیست")
        else:
            for item in result["ranking_rows"]:
                lines.extend([
                    f"🔹 {item['rank']}. {item.get('symbol') or 'داده موجود نیست'}",
                    f"پایه: {item.get('underlying_symbol') or 'داده موجود نیست'} | نوع: {item.get('contract_type') or 'داده موجود نیست'}",
                    f"قیمت پایه فعلی: {item.get('underlying_price')}",
                    f"قیمت پایه در سناریو: {item.get('scenario_underlying_price')}",
                    f"اعمال: {item.get('strike')}",
                    f"قیمت فعلی آپشن: {item.get('current_option_price')}",
                    f"ارزش سناریویی آپشن در سررسید: {item.get('scenario_option_value_at_expiry')}",
                    f"بازده سناریویی: {item.get('scenario_return_pct'):.2f}%",
                    f"اهرم: {item.get('leverage'):.2f}x",
                    "━━━━━━━━━━━━━━━━━━━━",
                ])
        return "\n".join(lines)
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

    # Fail closed for every RANKED route, including symbol-specific Top-5.
    # A symbol report must use the same TSETMC economic ranking as the global
    # Top-15 report; only the universe is narrowed to the selected underlying.
    if snapshot.get("report_mode") == "RANKED":
        ranking = snapshot.get("ranking") or {}
        if ranking.get("mode") != "TSETMC_ECONOMIC_SCORING":
            raise RuntimeError(
                "REPORT_RANKING_MODE_MISMATCH: expected=TSETMC_ECONOMIC_SCORING; "
                f"actual={ranking.get('mode')}"
            )
        if ranking.get("status") != "PASS":
            raise RuntimeError(
                "REPORT_RANKING_STATUS_BLOCKED: "
                f"status={ranking.get('status')}"
            )
        if command not in ("گزارش", "همه", "کل") and snapshot.get("underlying_symbol") != command:
            raise RuntimeError(
                "REPORT_SYMBOL_ROUTE_MISMATCH: "
                f"expected={command}; actual={snapshot.get('underlying_symbol')}"
            )

    # Evidence publication is deliberately kept out of the Bale response path.
    # The user must receive the report first; audit publication is non-critical.
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
    available = {symbol for symbol in symbols if symbol}
    preferred = [symbol for symbol in PREFERRED_UNDERLYINGS if symbol in available]
    remaining = sorted(
        available.difference(preferred),
        key=lambda value: value,
    )
    return preferred + remaining


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
    # Use Bale inline (glass) buttons for symbol selection so the user can
    # tap a symbol directly. Reply-keyboard support remains available through
    # the existing "🔎 انتخاب نماد" command.
    inline_keyboard = []
    for index in range(0, len(page_symbols), 2):
        inline_keyboard.append([
            {"text": symbol, "callback_data": f"symbol:{symbol}"}
            for symbol in page_symbols[index:index + 2]
        ])
    navigation = []
    if page > 0:
        navigation.append({"text": "◀️ صفحه قبل", "callback_data": f"symbols_page:{page - 1}"})
    if page < total_pages - 1:
        navigation.append({"text": "صفحه بعد ▶️", "callback_data": f"symbols_page:{page + 1}"})
    if navigation:
        inline_keyboard.append(navigation)
    inline_keyboard.append([{"text": "🏠 منوی اصلی", "callback_data": "main_menu"}])
    markup = {"inline_keyboard": inline_keyboard}
    send_message(
        chat_id,
        f"🔎 انتخاب نماد پایه\n\nتعداد نمادهای دارای اختیار معامله در TSETMC: {len(symbols)}\nصفحه {page + 1} از {total_pages}\n\nبا انتخاب هر نماد، ۵ قرارداد برتر همان نماد بر اساس Ranking اقتصادی TSETMC نمایش داده می‌شود:",
        reply_markup=markup,
    )


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
                        callback_data = str(callback.get("data") or "").strip()
                        command = CALLBACK_COMMANDS.get(callback_data)

                        if callback_data.startswith("symbols_page:"):
                            page = int(callback_data.split(":", 1)[1])
                            send_symbol_menu(chat_id, page)
                        elif callback_data.startswith("symbol:"):
                            symbol = normalize_command(callback_data.split(":", 1)[1])
                            if not symbol:
                                raise RuntimeError("EMPTY_SYMBOL_CALLBACK")
                            report = generate_report(symbol)
                            send_message(chat_id, report)
                            try:
                                publish_latest_evidence()
                            except Exception as exc:
                                print("GITHUB_EVIDENCE_ERROR:", type(exc).__name__)
                            send_report_menu(chat_id)
                        elif callback_data == "main_menu":
                            send_report_menu(chat_id)
                        elif command == "وضعیت":
                            send_message(chat_id, system_status())
                            send_report_menu(chat_id)
                        elif command:
                            report = generate_report(command)
                            send_message(chat_id, report)
                            try:
                                publish_latest_evidence()
                            except Exception as exc:
                                print("GITHUB_EVIDENCE_ERROR:", type(exc).__name__)
                            send_report_menu(chat_id)
                        else:
                            raise RuntimeError("UNKNOWN_CALLBACK")
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
                    elif text in ("رفتار", "تغییرات", "behavior"):
                        send_message(chat_id, generate_report("رفتار"))
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
                        try:
                            publish_latest_evidence()
                        except Exception as exc:
                            print("GITHUB_EVIDENCE_ERROR:", type(exc).__name__)
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
