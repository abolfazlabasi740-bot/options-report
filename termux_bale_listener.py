#!/usr/bin/env python3
"""Always-on, low-latency Bale listener for Termux."""
from __future__ import annotations

import os
import subprocess
import time
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
    response = requests.get(DOWNLOAD_URL, timeout=90)
    response.raise_for_status()
    if len(response.content) < 5000 or response.content[:2] != b"PK":
        raise RuntimeError("پاسخ Optionschool فایل XLSX معتبر نیست.")
    target.write_bytes(response.content)
    return target

def send(chat_id: str, text: str) -> None:
    for start in range(0, len(text), 3500):
        requests.post(
            f"{ENDPOINT}/sendMessage",
            json={"chat_id": chat_id, "text": text[start:start + 3500]},
            timeout=45,
        ).raise_for_status()

def main() -> None:
    offset = 0
    while True:
        try:
            updates = requests.get(
                f"{ENDPOINT}/getUpdates",
                params={"offset": offset, "timeout": 25},
                timeout=35,
            ).json().get("result", [])
            for update in updates:
                offset = max(offset, int(update.get("update_id", 0)) + 1)
                message = update.get("message") or {}
                text = " ".join(str(message.get("text", "")).strip().split())
                chat_id = str((message.get("chat") or {}).get("id", ""))
                kind = request_kind(text)
                if not chat_id or not kind:
                    continue
                prefix, count = kind
                try:
                    workbook = download()
                    env = os.environ.copy()
                    env["REPORT_SYMBOL_PREFIX"] = prefix
                    env["REPORT_TOP_COUNT"] = str(count)
                    subprocess.run(
                        [os.getenv("PYTHON_BIN", "python3"), str(ROOT / "generate_report.py"), str(workbook)],
                        cwd=ROOT, env=env, check=True, timeout=300,
                    )
                    report = (ROOT / "output_options_report.md").read_text(encoding="utf-8")
                    send(chat_id, ("گزارش کل بازار | ۱۵ آپشن برتر\n\n" if count == 15 else f"گزارش سهم {text} | ۵ آپشن برتر\n\n") + report)
                except Exception as error:
                    send(chat_id, f"خطا در تهیه گزارش جدید: {error}")
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    main()
