#!/usr/bin/env python3
"""Poll Bale bot commands and generate five-contract underlying reports."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

import requests

COMMANDS = {
    "ذوب": "ضذوب",
    "ذوب آهن": "ضذوب",
    "بانک ملت": "ضملت",
    "ملت": "ضملت",
    "بانک صادرات": "ضصاد",
    "صادرات": "ضصاد",
    "بانک تجارت": "ضتجارت",
    "تجارت": "ضتجارت",
    "بانک سامان": "ضبساما",
    "سامان": "ضبساما",
}


def main() -> int:
    token = os.environ["BALE_BOT_TOKEN"]
    root = Path(os.environ.get("PROJECT_ROOT", ".")).resolve()
    api = os.environ.get("BALE_API_BASE", "https://tapi.bale.ai").rstrip("/")
    endpoint = f"{api}/bot{token}"
    offset = 0
    deadline = time.time() + int(os.environ.get("LISTENER_SECONDS", "11700"))
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
            prefix = COMMANDS.get(text)
            if not prefix or not chat_id:
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
                        "-Download",
                        "-V4Candidate",
                        "-MinLeverage",
                        "3",
                        "-SymbolPrefix",
                        prefix,
                        "-TopCount",
                        "5",
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
                report = next(
                    root.joinpath("reports").glob("*_options_report_v4.md"),
                    None,
                )
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
