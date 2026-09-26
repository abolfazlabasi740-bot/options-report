#!/usr/bin/env python3

from pathlib import Path
import os
import time
import requests
import json
from bale_transport import send_message as transport_send

from report_engine import build_tsetmc_report, save_tsetmc_report

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


def send_message(chat_id, text):
    count = transport_send(TOKEN, chat_id, text)
    print(f"SENT {count}/{count}")


def generate_report(command):
    if command in ("گزارش", "همه", "کل"):
        report, snapshot = build_tsetmc_report(
            top_count=15,
            flow=1,
            report_mode="TRADING_ACTIVITY",
        )
    else:
        report, snapshot = build_tsetmc_report(
            top_count=5,
            underlying_symbol=command,
            flow=1,
            report_mode="TRADING_ACTIVITY",
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


def main():
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("BALE_BOT_TOKEN و BALE_CHAT_ID باید از قبل تنظیم شوند")

    print("====================================")
    print("OptimusAI V4.1 Bale Listener")
    print("====================================")
    print("گزارش  -> 15 قرارداد برتر معاملاتی کل بازار TSETMC")
    print("نماد    -> 5 قرارداد برتر معاملاتی بر اساس نماد پایه TSETMC")
    print("====================================")

    offset = load_offset()

    while True:
        try:
            updates = get_updates(offset)

            for update in updates:
                next_offset = int(update["update_id"]) + 1

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

                print(
                    f"COMMAND = {text} | CHAT_ID = {chat_id}"
                )

                try:
                    report = generate_report(text)

                    send_message(
                        chat_id,
                        report,
                    )

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
