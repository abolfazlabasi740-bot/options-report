#!/usr/bin/env python3
"""Poll Bale bot commands and generate five-contract underlying reports."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

import requests

COMMANDS = {
    "اخابر": "ضخابر",
    "خابر": "ضخابر",
    "ذوب": "ضذوب",
    "ذوب آهن": "ضذوب",
    "بساما": "ضبساما",
    "بانک ملت": "ضملت",
    "ملت": "ضملت",
    "بانک صادرات": "ضصاد",
    "صادرات": "ضصاد",
    "بانک تجارت": "ضتجارت",
    "تجارت": "ضتجارت",
    "بانک سامان": "ضبساما",
    "سامان": "ضبساما",
    "خودرو": "ضخود",
    "شستا": "ضستا",
    "فزر": "ضفزر",
    "وبصادر": "ضصاد",
    "اطلس": "ضاطلس",
    "تاصیکو": "ضتاصیکو",
    "خبهمن": "ضهمن",
    "فملی": "ضملی",
    "وبملت": "ضملت",
    "اهرم": "ضاهرم",
    "توان": "ضتوان",
    "خساپا": "ضسپا",
    "شپنا": "ضشنا",
    "فرابورس": "ضفرابورس",
    "موج": "ضموج",
    "تجارت": "ضتجارت",
}

SYMBOL_ALIASES = {
    "\u0648\u0628\u0645\u0644\u062a": "\u0636\u0645\u0644\u062a",
    "\u0648\u0628\u0635\u0627\u062f\u0631": "\u0636\u0635\u0627\u062f",
    "\u0648\u062a\u062c\u0627\u0631\u062a": "\u0636\u062a\u062c\u0627\u0631\u062a",
    "\u062e\u0648\u062f\u0631\u0648": "\u0636\u062e\u0648\u062f",
    "\u062e\u0633\u0627\u067e\u0627": "\u0636\u0633\u067e\u0627",
    "\u0634\u0633\u062a\u0627": "\u0636\u0633\u062a\u0627",
    "\u0634\u067e\u0646\u0627": "\u0636\u0634\u0646\u0627",
    "\u0641\u0645\u0644\u06cc": "\u0636\u0645\u0644\u06cc",
    "\u0641\u0648\u0644\u0627\u062f": "\u0636\u0641\u0644\u0627",
    "\u0630\u0648\u0628": "\u0636\u0630\u0648\u0628",
}

def resolve_request(text: str) -> tuple[str | None, int]:
    """Return (option prefix, result count); empty prefix means whole market."""
    if text in COMMANDS:
        return COMMANDS[text], 5
    for name, prefix in SYMBOL_ALIASES.items():
        if name in text:
            return prefix, 5
    if "\u06af\u0632\u0627\u0631\u0634" in text:
        return "", 15
    return None, 0


def download_latest_workbook(root: Path) -> Path:
    """Download fresh Optionschool data for every interactive request."""
    endpoint = "https://s3.optionschool24.com/export/excel?type=1"
    config_path = root / "configs" / "project.json"
    if config_path.exists():
        try:
            import json
            config = json.loads(config_path.read_text(encoding="utf-8-sig"))
            endpoint = config.get("data_source", {}).get("endpoint", endpoint)
        except Exception:
            pass
    raw_dir = root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / f"optionschool24_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = requests.get(endpoint, timeout=120)
    response.raise_for_status()
    if len(response.content) < 5000 or response.content[:2] != b"PK":
        raise RuntimeError("Downloaded response is not a valid XLSX workbook.")
    target.write_bytes(response.content)
    return target


def main() -> int:
    token = os.environ["BALE_BOT_TOKEN"]
    root = Path(os.environ.get("PROJECT_ROOT", ".")).resolve()
    api = os.environ.get("BALE_API_BASE", "https://tapi.bale.ai").rstrip("/")
    endpoint = f"{api}/bot{token}"
    offset = 0
    deadline = time.time() + int(os.environ.get("LISTENER_SECONDS", "240"))
    while time.time() < deadline:
        try:
            response = requests.get(
                f"{endpoint}/getUpdates",
                params={"offset": offset, "timeout": 25},
                timeout=35,
            )
            response.raise_for_status()
            updates = response.json().get("result", [])
        except requests.RequestException:
            time.sleep(10)
            continue
        for update in updates:
            offset = max(offset, int(update.get("update_id", 0)) + 1)
            message = update.get("message") or update.get("edited_message") or {}
            text = " ".join(str(message.get("text", "")).strip().lower().split())
            chat_id = str((message.get("chat") or {}).get("id", ""))
            prefix, top_count = resolve_request(text)
            if prefix is None or not chat_id:
                continue
            try:
                latest_workbook = download_latest_workbook(root)
            except Exception as error:
                requests.post(
                    f"{endpoint}/sendMessage",
                    data={"chat_id": chat_id, "text": f"دریافت اکسل جدید Optionschool ناموفق بود: {error}"},
                    timeout=30,
                )
                continue
            with tempfile.TemporaryDirectory() as temp:
                result = subprocess.run(
                    [
                        "pwsh",
                        "-NoProfile",
                        "-File",
                        str(root / "scripts" / "run_pipeline.ps1"),
                        "-ProjectRoot",
                        str(root),
                        "-InputWorkbook",
                        str(latest_workbook),
                        "-V4Candidate",
                        "-MinLeverage",
                        "3",
                        "-SymbolPrefix",
                        prefix,
                        "-TopCount",
                        str(top_count),
                        "-Quiet",
                    ],
                    text=True,
                    capture_output=True,
                    timeout=600,
                )
                if result.returncode != 0:
                    requests.post(
                        f"{endpoint}/sendMessage",
                        data={"chat_id": chat_id, "text": "خطا در تهیه گزارش؛ اجرای زمان‌بندی‌شده دست‌نخورده باقی ماند."},
                        timeout=30,
                    )
                    continue
                reports = list(root.joinpath("reports").glob("*_options_report_v4.md"))
                report = max(reports, key=lambda p: p.stat().st_mtime) if reports else None
                if report is None:
                    continue
                pdf = Path(temp) / f"{prefix}_top5.pdf"
                render = subprocess.run(
                    [
                        "python",
                        str(root / "scripts" / "render_report_pdf.py"),
                        "--markdown",
                        str(report),
                        "--output",
                        str(pdf),
                        "--font-path",
                        str(root / "assets" / "fonts" / "BNazanin.ttf"),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if render.returncode != 0:
                    continue
                with pdf.open("rb") as handle:
                    requests.post(
                        f"{endpoint}/sendDocument",
                        data={"chat_id": chat_id, "caption": f"گزارش ۵ آپشن برتر {text} | V4"},
                        files={"document": (pdf.name, handle, "application/pdf")},
                        timeout=90,
                    ).raise_for_status()
        time.sleep(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
