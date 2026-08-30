#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical report runner for PROTOCOL_OPTIONS_RANKING_V3.
The scoring logic lives only in rank_options_live.py.
This file is orchestration/report-delivery only.
"""

import hashlib
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

import rank_options_live as v3

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_REPORT = BASE_DIR / "output_options_report.md"
OUTPUT_TOP = BASE_DIR / "output_options_top15.csv"


def send_bale(text: str) -> None:
    token = os.environ.get("BALE_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("BALE_CHAT_ID", "").strip()

    if not token or not chat_id:
        raise RuntimeError("BALE_BOT_TOKEN و BALE_CHAT_ID برای ارسال گزارش موجود نیستند.")

    chunks = [text[i:i + 3500] for i in range(0, len(text), 3500)]
    url = f"https://tapi.bale.ai/bot{token}/sendMessage"

    for index, chunk in enumerate(chunks, start=1):
        payload = urlencode({"chat_id": chat_id, "text": chunk}).encode("utf-8")
        request = Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "OptionsReport-V3/1.0",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=45) as response:
                response_text = response.read().decode("utf-8", errors="replace")
                status = response.status
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"خطای API بله در بخش {index}: HTTP {exc.code}: {details}") from exc
        except URLError as exc:
            raise RuntimeError(f"خطای اتصال به API بله در بخش {index}: {exc.reason}") from exc

        if status != 200 or '"ok":true' not in response_text.replace(" ", ""):
            raise RuntimeError(f"ارسال بخش {index} توسط بله تأیید نشد: {response_text}")

        print(f"ارسال بخش {index}/{len(chunks)} به بله موفق بود.")


def find_input(explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit)
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        if not candidate.is_file():
            raise RuntimeError(f"فایل ورودی یافت نشد: {candidate}")
        return candidate

    files = sorted(
        BASE_DIR.glob("optionschool24_all_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise RuntimeError("هیچ فایل optionschool24_all_*.xlsx در Repository/Workspace یافت نشد.")
    return files[0]


def build_v3_report(input_path: Path):
    df = pd.read_excel(input_path)
    total_initial = len(df)

    missing = [c for c in v3.REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise RuntimeError("ستون‌های ضروری V3 موجود نیستند: " + "، ".join(missing))

    df = v3.numeric_columns(df)
    df["نماد"] = df["نماد"].astype(str).str.strip()

    valid = df[
        df["نماد"].notna()
        & (df["نماد"] != "")
        & (df["نماد"] != "nan")
        & (df["حجم معاملات"].fillna(0) > 0)
        & (df["ارزش معاملات"].fillna(0) > 0)
        & (df["قیمت پایانی"].fillna(0) > 0)
        & (df["روزهای تقویمی"].fillna(0) > 0)
    ].copy()

    if valid.empty:
        raise RuntimeError("هیچ قرارداد معتبری پس از گیت‌های V3 باقی نماند.")

    valid = v3.add_analytics(valid)
    scored = v3.score_v3(valid)
    top = scored.sort_values(
        ["FinalScore", "DataConfidence", "حجم معاملات"],
        ascending=[False, False, False],
    ).head(v3.TOP_N).copy()
    top.insert(0, "رتبه", range(1, len(top) + 1))

    report = v3.make_report(top, input_path.name, total_initial, len(valid))
    OUTPUT_REPORT.write_text(report, encoding="utf-8")
    top.to_csv(OUTPUT_TOP, index=False, encoding="utf-8-sig")

    return report


def main() -> None:
    input_arg = sys.argv[1] if len(sys.argv) > 1 else None
    input_path = find_input(input_arg)
    print(f"منبع داده V3: {input_path.name}")

    report = build_v3_report(input_path)
    print(report)

    if os.environ.get("SEND_TO_BALE", "false").strip().lower() == "true":
        send_bale(report)
        print("گزارش V3 با موفقیت برای بله ارسال شد.")
    else:
        print("SEND_TO_BALE فعال نیست؛ گزارش فقط تولید شد.")

    digest = hashlib.sha256(report.encode("utf-8")).hexdigest()
    print(f"Report SHA-256: {digest}")


if __name__ == "__main__":
    main()
