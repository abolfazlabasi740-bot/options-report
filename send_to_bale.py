"""Explicit one-shot sender with no side effects on import."""
from pathlib import Path
import os
from bale_transport import send_message


def main():
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("BALE_BOT_TOKEN و BALE_CHAT_ID باید از قبل تنظیم شوند")
    report = Path(__file__).resolve().parent / "output" / "latest_report.txt"
    count = send_message(token, chat_id, report.read_text(encoding="utf-8"))
    print(f"BALE_SEND_OK CHUNKS={count}")


if __name__ == "__main__":
    main()
