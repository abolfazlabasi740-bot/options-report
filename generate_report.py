#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical runner/report delivery for PROTOCOL_OPTIONS_RANKING_V3."""

import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import rank_options_live as v3

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_REPORT = BASE_DIR / "output_options_report.md"
OUTPUT_TOP = BASE_DIR / "output_options_top15.csv"
OPTIONSCHOOL_URL = "https://s3.optionschool24.com/export/excel?type=1"


def now_tehran() -> datetime:
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Tehran"))


def send_bale(text: str) -> None:
    token = os.environ.get("BALE_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("BALE_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("BALE_BOT_TOKEN و BALE_CHAT_ID برای ارسال گزارش موجود نیستند.")
    chunks = [text[i:i + 3500] for i in range(0, len(text), 3500)]
    url = f"https://tapi.bale.ai/bot{token}/sendMessage"
    for index, chunk in enumerate(chunks, start=1):
        payload = urlencode({"chat_id": chat_id, "text": chunk}).encode("utf-8")
        request = Request(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "OptionsReport-V3/1.0"}, method="POST")
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


def download_latest_optionschool() -> tuple[Path, dict]:
    """Download official OptionSchool XLSX and return auditable download metadata."""
    target = BASE_DIR / "optionschool24_latest.xlsx"
    started = now_tehran()
    request = Request(OPTIONSCHOOL_URL, headers={"User-Agent": "OptionsReport-V3/1.0"})
    try:
        with urlopen(request, timeout=60) as response:
            data = response.read()
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"دریافت فایل Optionschool24 ناموفق بود: {exc}") from exc
    finished = now_tehran()
    if len(data) < 1024:
        raise RuntimeError("فایل دریافت‌شده Optionschool24 غیرقابل قبول یا ناقص است.")
    if not data.startswith(b"PK"):
        raise RuntimeError("پاسخ endpoint فایل XLSX معتبر نیست.")
    target.write_bytes(data)
    metadata = {
        "source": "OptionSchool24",
        "url": OPTIONSCHOOL_URL,
        "filename": target.name,
        "download_started": started.isoformat(timespec="seconds"),
        "download_completed": finished.isoformat(timespec="seconds"),
        "download_completed_display": finished.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return target, metadata


def find_input(explicit: str | None):
    if explicit:
        candidate = Path(explicit)
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        if not candidate.is_file():
            raise RuntimeError(f"فایل ورودی یافت نشد: {candidate}")
        return candidate, {
            "source": "Explicit input",
            "filename": candidate.name,
            "download_started": None,
            "download_completed": None,
            "download_completed_display": "زمان دانلود ثبت نشده؛ فایل ورودی دستی است.",
            "bytes": candidate.stat().st_size,
            "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        }
    return download_latest_optionschool()


def build_v3_report(input_path: Path, metadata: dict):
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
        & (df["آخرین قیمت"].fillna(0) > 0)
        & (df["قیمت اعمال"].fillna(0) > 0)
        & (df["قیمت سهم پایه"].fillna(0) > 0)
        & (df["روزهای تقویمی"].fillna(0) > 0)
    ].copy()
    if valid.empty:
        raise RuntimeError("هیچ قرارداد معتبری پس از گیت‌های V3 باقی نماند.")
    valid = v3.add_analytics(valid)
    valid["RemainingDays"] = (valid["روزهای تقویمی"] - 1).clip(lower=0)
    scored = v3.score_v3(valid)
    top = scored.sort_values(["FinalScore", "حجم معاملات"], ascending=[False, False]).head(v3.TOP_N).copy()
    generated = now_tehran()
    report = v3.make_report(top, input_path.name, total_initial, len(valid))

    # make_report historically used naive UTC datetime. Replace only its
    # execution timestamp/run-id with the authoritative Tehran timestamp.
    lines = report.splitlines()
    if len(lines) >= 3 and lines[0].startswith("# گزارش رتبه‌بندی اختیار معامله V3"):
        lines[1] = f"تاریخ اجرا: {generated:%Y-%m-%d %H:%M:%S}"
        lines[2] = f"شناسه اجرا: {generated:%Y%m%d_%H%M%S}"
        report = "\n".join(lines) + "\n"

    audit_header = (
        "## شناسنامه داده و زمان‌بندی گزارش\n"
        f"- منبع داده: {metadata['source']}\n"
        f"- فایل مبنا: {metadata['filename']}\n"
        f"- زمان پایان دانلود: {metadata['download_completed_display']}\n"
        f"- حجم فایل: {metadata['bytes']} bytes\n"
        f"- SHA-256 فایل: `{metadata['sha256']}`\n"
        f"- زمان تولید گزارش: {generated.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
        "- مبنای تصمیم‌گیری: اطلاعات همین فایل دریافت‌شده در زمان فوق.\n\n"
    )
    report = audit_header + report
    OUTPUT_REPORT.write_text(report, encoding="utf-8")
    top.to_csv(OUTPUT_TOP, index=False, encoding="utf-8-sig")
    return report


def main() -> None:
    input_arg = sys.argv[1] if len(sys.argv) > 1 else None
    input_path, metadata = find_input(input_arg)
    print(f"منبع داده V3: {input_path.name}")
    print(f"زمان پایان دانلود: {metadata['download_completed_display']}")
    print(f"SHA-256 فایل: {metadata['sha256']}")
    report = build_v3_report(input_path, metadata)
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
