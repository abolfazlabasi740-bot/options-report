#!/usr/bin/env python3

from pathlib import Path
import os
import time
import requests

from report_engine import download_optionschool, build_report, format_report

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
REPORT_FILE = OUTPUT / "latest_report.txt"

TOKEN = os.getenv("BALE_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("BALE_CHAT_ID", "").strip()

if not TOKEN:
    raise RuntimeError("BALE_BOT_TOKEN تنظیم نشده است")

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
    url = f"{API}/sendMessage"

    chunks = [
        text[i:i + 3500]
        for i in range(0, len(text), 3500)
    ]

    for i, chunk in enumerate(chunks, 1):
        r = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": chunk,
            },
            timeout=30,
        )
        r.raise_for_status()

        result = r.json()

        if not result.get("ok"):
            raise RuntimeError(f"Bale error: {result}")

        print(f"SENT {i}/{len(chunks)}")


def generate_report(command):
    source = download_optionschool()

    if command in ("گزارش", "کل"):
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

    report = format_report(work, source)

    OUTPUT.mkdir(exist_ok=True)
    REPORT_FILE.write_text(report, encoding="utf-8")

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
    global CHAT_ID

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

                if not CHAT_ID:
                    CHAT_ID = str(chat_id)
                    print("CHAT_ID =", CHAT_ID)

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
                        f"REPORT_ERROR command={text}: {e}"
                    )

                    try:
                        send_message(
                            chat_id,
                            "⚠️ خطا در تولید گزارش V4.1\n\n"
                            + str(e),
                        )
                    except Exception as send_error:
                        print(
                            "ERROR_MESSAGE_SEND_FAILED:",
                            send_error,
                        )

        except KeyboardInterrupt:
            print("\nLISTENER_STOPPED")
            break

        except Exception as e:
            print("LISTENER_ERROR:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
