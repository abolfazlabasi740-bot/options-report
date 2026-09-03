#!/usr/bin/env python3
"""Always-on, low-latency Bale listener for Termux."""
from __future__ import annotations

import os
import subprocess
import time
import traceback
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
API = os.getenv("BALE_API_BASE", "https://tapi.bale.ai").rstrip("/")
TOKEN = os.environ["BALE_BOT_TOKEN"]
ENDPOINT = f"{API}/bot{TOKEN}"
DOWNLOAD_URL = "https://s3.optionschool24.com/export/excel?type=1"
ALIASES = {
    "وبملت": "ضملت", "وبصادر": "ضصاد", "وتجارت": "ضتجارت",
    "خودرو": "ضخود", "خساپا": "ضسپا", "شستا": "ضستا",
    "شپنا": "ضشنا", "فملی": "ضملی", "فولاد": "ضفلا",
    "ذوب": "ضذوب", "سامان": "ضبساما", "خبهمن": "ضهمن",
    "هرمز": "ضهرم", "فرابورس": "ضفرابورس", "فزر": "ضفزر",
    "توان": "ضتوان", "اطلس": "ضاطلس", "جواهر": "ضجواهر", "طعام": "ضطعام",
}


def log(message: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)


def request_kind(text: str) -> tuple[str, int] | None:
    for name, prefix in ALIASES.items():
        if name in text:
            return prefix, 5
    if "گزارش" in text:
        return "", 15
    return None


def download() -> Path:
    raw = ROOT / "data"
    raw.mkdir(exist_ok=True)
    target = raw / f"optionschool24_latest_{int(time.time())}.xlsx"
    log("مرحله ۱/۴: دریافت فایل تازه Optionschool24...")
    response = requests.get(DOWNLOAD_URL, timeout=90)
    response.raise_for_status()
    log(f"پاسخ دانلود: HTTP {response.status_code} | حجم: {len(response.content)} bytes")
    if len(response.content) < 5000 or response.content[:2] != b"PK":
        raise RuntimeError("پاسخ Optionschool فایل XLSX معتبر نیست.")
    target.write_bytes(response.content)
    log(f"فایل تازه ذخیره شد: {target.name}")
    return target


def send(chat_id: str, text: str) -> None:
    chunks = max(1, (len(text) + 3499) // 3500)
    for index, start in enumerate(range(0, len(text), 3500), start=1):
        log(f"مرحله ۴/۴: ارسال بخش {index}/{chunks} به بله...")
        response = requests.post(
            f"{ENDPOINT}/sendMessage",
            json={"chat_id": chat_id, "text": text[start:start + 3500]},
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"API بله ارسال پیام را تأیید نکرد: {payload}")
        log(f"ارسال بخش {index}/{chunks} موفق بود.")


def main() -> None:
    offset = 0
    log("Listener شروع شد.")
    log(f"Bale API: {API}")
    while True:
        try:
            log(f"مرحله ۰: getUpdates | offset={offset}")
            response = requests.get(
                f"{ENDPOINT}/getUpdates",
                params={"offset": offset, "timeout": 25},
                timeout=35,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok", True):
                raise RuntimeError(f"getUpdates خطا داد: {payload}")
            updates = payload.get("result", [])
            if updates:
                log(f"{len(updates)} update دریافت شد.")
            for update in updates:
                offset = max(offset, int(update.get("update_id", 0)) + 1)
                message = update.get("message") or {}
                text = " ".join(str(message.get("text", "")).strip().split())
                chat_id = str((message.get("chat") or {}).get("id", ""))
                log(f"پیام دریافتی: {text!r} | chat_id={chat_id}")
                kind = request_kind(text)
                if not chat_id or not kind:
                    log("پیام نادیده گرفته شد: دستور شناخته‌شده نیست یا chat_id موجود نیست.")
                    continue
                prefix, count = kind
                scope = prefix or "کل بازار"
                log(f"دستور معتبر: scope={scope} | خروجی مورد انتظار={count}")
                try:
                    workbook = download()
                    env = os.environ.copy()
                    env["REPORT_SYMBOL_PREFIX"] = prefix
                    env["REPORT_TOP_COUNT"] = str(count)
                    log("مرحله ۲/۴: اجرای generate_report.py...")
                    log(f"REPORT_SYMBOL_PREFIX={prefix!r} | REPORT_TOP_COUNT={count}")
                    result = subprocess.run(
                        [os.getenv("PYTHON_BIN", "python3"), str(ROOT / "generate_report.py"), str(workbook)],
                        cwd=ROOT, env=env, check=True, timeout=300,
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                    )
                    if result.stdout:
                        log("خروجی generate_report.py:")
                        print(result.stdout, end="", flush=True)
                    if result.stderr:
                        log("stderr generate_report.py:")
                        print(result.stderr, end="", flush=True)
                    report = (ROOT / "output_options_report.md").read_text(encoding="utf-8")
                    log(f"مرحله ۳/۴: گزارش تولید شد | طول متن={len(report)} کاراکتر")
                    prefix_text = "گزارش کل بازار | ۱۵ آپشن برتر\n\n" if count == 15 else f"گزارش سهم {text} | ۵ آپشن برتر\n\n"
                    send(chat_id, prefix_text + report)
                    log("چرخه درخواست با موفقیت کامل شد.")
                except Exception as error:
                    log(f"خطا در چرخه درخواست: {type(error).__name__}: {error}")
                    traceback.print_exc()
                    try:
                        send(chat_id, f"خطا در تهیه گزارش جدید: {type(error).__name__}: {error}")
                    except Exception as send_error:
                        log(f"ارسال پیام خطا نیز ناموفق بود: {type(send_error).__name__}: {send_error}")
                        traceback.print_exc()
        except Exception as error:
            log(f"خطای اصلی Listener: {type(error).__name__}: {error}")
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    main()
