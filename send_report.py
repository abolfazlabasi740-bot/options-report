#!/usr/bin/env python3
import hashlib
import os
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
LAST_HASH_PATH = BASE_DIR / ".last_report_hash"
DEFAULT_REPORT_PATH = BASE_DIR / "output_options_report.md"
CHUNK_SIZE = 4000

# Bale Bot API (Telegram-like style)
BALE_API_URL = "https://tapi.bale.ai/bot{token}/sendMessage"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'" ))


def read_report_text(report_path: Path) -> str:
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")
    return report_path.read_text(encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_last_hash() -> str:
    if LAST_HASH_PATH.exists():
        return LAST_HASH_PATH.read_text(encoding="utf-8").strip()
    return ""


def write_last_hash(value: str) -> None:
    LAST_HASH_PATH.write_text(value + "\n", encoding="utf-8")


def split_chunks(text: str, size: int = CHUNK_SIZE):
    for start in range(0, len(text), size):
        yield text[start:start + size]


def send_chunk(token: str, chat_id: str, text: str) -> None:
    url = BALE_API_URL.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Send failed: {response.status_code} {response.text}")


def main() -> int:
    load_env_file(ENV_PATH)

    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("Missing BALE_BOT_TOKEN or BALE_CHAT_ID in .env", file=sys.stderr)
        return 2

    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPORT_PATH
    report_text = read_report_text(report_path)
    current_hash = sha256_text(report_text)
    last_hash = read_last_hash()

    if current_hash == last_hash:
        print("Report unchanged; skipping send.")
        return 0

    header = "گزارش جدید\n\n"
    chunks = list(split_chunks(report_text))
    if chunks:
        chunks[0] = header + chunks[0]
    else:
        chunks = [header]

    for chunk in chunks:
        send_chunk(token, chat_id, chunk)

    write_last_hash(current_hash)
    print("Report sent successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
