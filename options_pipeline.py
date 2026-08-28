#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
GENERATOR = BASE_DIR / "generate_report.py"
REPORT_FILE = BASE_DIR / "output_options_report.md"
HASH_FILE = BASE_DIR / ".last_report_hash"


def read_env():
    config = {}

    if not ENV_FILE.is_file():
        raise RuntimeError("فایل .env پیدا نشد.")

    for raw_line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        config[key.strip()] = value.strip().strip('"').strip("'")

    token = config.get("BALE_BOT_TOKEN", "")
    chat_id = config.get("BALE_CHAT_ID", "")

    if not token:
        raise RuntimeError("BALE_BOT_TOKEN در فایل .env ثبت نشده است.")

    if not chat_id:
        raise RuntimeError("BALE_CHAT_ID در فایل .env ثبت نشده است.")

    return token, chat_id


def send_message(token, chat_id, text, part_number, total_parts):
    url = f"https://tapi.bale.ai/bot{token}/sendMessage"

    payload = urlencode({
        "chat_id": chat_id,
        "text": text,
    }).encode("utf-8")

    request = Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "OptionsSchool24-Termux/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=45) as response:
            status = response.status
            response_text = response.read().decode("utf-8", errors="replace")

    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"خطای API بله (HTTP {error.code}): {details}") from error

    except URLError as error:
        raise RuntimeError(f"خطای اتصال به API بله: {error.reason}") from error

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"پاسخ نامعتبر API بله (HTTP {status}): {response_text}"
        ) from error

    if status != 200 or result.get("ok") is not True:
        raise RuntimeError(f"ارسال توسط بله تأیید نشد: {response_text}")

    message_id = result.get("result", {}).get("message_id", "نامشخص")
    print(f"ارسال بخش {part_number}/{total_parts} موفق بود | message_id={message_id}")


def main():
    if not GENERATOR.is_file():
        raise RuntimeError("فایل generate_report.py پیدا نشد.")

    token, chat_id = read_env()

    excel_files = sorted(
        BASE_DIR.glob("optionschool24_all_*.xlsx"),
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )

    if not excel_files:
        raise RuntimeError("فایل Excel با الگوی optionschool24_all_*.xlsx پیدا نشد.")

    latest_excel = excel_files[0]
    print(f"فایل ورودی: {latest_excel.name}")
    print("در حال تولید گزارش...")

    subprocess.run(
        [sys.executable, str(GENERATOR), str(latest_excel)],
        cwd=BASE_DIR,
        check=True,
    )

    if not REPORT_FILE.is_file():
        raise RuntimeError("فایل output_options_report.md تولید نشد.")

    report_text = REPORT_FILE.read_text(encoding="utf-8-sig").strip()

    if not report_text:
        raise RuntimeError("محتوای گزارش خالی است.")

    report_hash = hashlib.sha256(report_text.encode("utf-8")).hexdigest()

    if HASH_FILE.is_file():
        previous_hash = HASH_FILE.read_text(encoding="utf-8").strip()

        if previous_hash == report_hash:
            print("گزارش تغییری نکرده است؛ ارسال مجدد انجام نشد.")
            return

    # سقف امن پیام متنی بله
    chunks = [
        report_text[index:index + 3500]
        for index in range(0, len(report_text), 3500)
    ]

    print(f"در حال ارسال {len(chunks)} بخش به بله...")

    for number, chunk in enumerate(chunks, start=1):
        send_message(token, chat_id, chunk, number, len(chunks))

    HASH_FILE.write_text(report_hash + "\n", encoding="utf-8")
    HASH_FILE.chmod(0o600)

    print("گزارش با موفقیت در بله ارسال شد.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(f"خطا در اجرای generate_report.py: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"خطا: {error}", file=sys.stderr)
        sys.exit(1)
