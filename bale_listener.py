#!/usr/bin/env python3

from pathlib import Path
import os
import time
import requests
from bale_transport import send_message as transport_send

from report_engine import download_optionschool, build_report, save_report

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
REPORT_FILE = OUTPUT / "latest_report.txt"

TOKEN = os.getenv("BALE_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("BALE_CHAT_ID", "").strip()

API = f"https://tapi.bale.ai/bot{TOKEN}"


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
    source = download_optionschool()

    if command in ("گزارش", "همه", "کل"):
        work = build_report(
            source,
            top_count=15,
        )
    else:
        work = build_report(
            source,
            top_count=5,
            symbol_prefix=command,
        )

    report = save_report(work, source)

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
    print("گزارش  -> 15 اختیار برتر کل بازار")
    print("نماد    -> 5 اختیار برتر همان نماد")
    print("====================================")

    offset = None

    while True:
        try:
            updates = get_updates(offset)

            for update in updates:
                offset = update["update_id"] + 1

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
                    continue

                if CHAT_ID and str(chat_id) != str(CHAT_ID):
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

        except KeyboardInterrupt:
            print("\nLISTENER_STOPPED")
            break

        except Exception as e:
            print("LISTENER_ERROR:", type(e).__name__)
            time.sleep(5)


if __name__ == "__main__":
    main()
