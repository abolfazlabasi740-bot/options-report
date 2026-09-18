#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
TEHRAN = ZoneInfo("Asia/Tehran")

OPTIONSCHOOL_URL = "https://s3.optionschool24.com/export/excel?type=1"
TOP_COUNT = int(os.getenv("TOP_COUNT", "15"))


def download_optionschool():
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    stamp = datetime.now(TEHRAN).strftime("%Y%m%d_%H%M%S")
    path = data_dir / f"optionschool_{stamp}.xlsx"

    r = requests.get(OPTIONSCHOOL_URL, timeout=90)
    r.raise_for_status()

    if len(r.content) < 5000 or not r.content.startswith(b"PK"):
        raise RuntimeError("فایل دریافتی Optionschool معتبر نیست")

    path.write_bytes(r.content)
    return path


def find_column(df, names):
    normalized = {
        str(c).strip().replace(" ", "").replace("_", "").replace("‌", "").lower(): c
        for c in df.columns
    }

    for name in names:
        key = str(name).strip().replace(" ", "").replace("_", "").replace("‌", "").lower()
        if key in normalized:
            return normalized[key]

    return None


def build_report(path):
    df = pd.read_excel(path)

    # V4.1 scoring engine: GitHub six-block production candidate
    from scoring_engine import score_dataframe

    scored = score_dataframe(df)

    symbol = find_column(scored, ["نماد", "Symbol"])
    premium = find_column(scored, ["آخرین قیمت", "آخرین", "Last"])
    base = find_column(scored, ["قیمت سهم پایه", "Underlying"])
    leverage = find_column(scored, ["اهرم", "Leverage"])

    required = {
        "نماد": symbol,
        "آخرین قیمت": premium,
        "قیمت سهم پایه": base,
        "اهرم": leverage,
        "FinalScore": "FinalScore",
        "RemainingDays": "RemainingDays",
    }

    missing = [name for name, col in required.items() if col not in scored.columns]

    if missing:
        raise RuntimeError(
            "ستون‌های ضروری V4.1 موجود نیستند: " + ", ".join(missing)
        )

    work = pd.DataFrame(index=scored.index)
    work["نماد"] = scored[symbol].astype(str).str.strip()
    work["آخرین"] = pd.to_numeric(scored[premium], errors="coerce")
    work["پایه"] = pd.to_numeric(scored[base], errors="coerce")
    work["اهرم"] = pd.to_numeric(scored[leverage], errors="coerce")
    work["FinalScore"] = pd.to_numeric(scored["FinalScore"], errors="coerce")
    work["RemainingDays"] = pd.to_numeric(
        scored["RemainingDays"], errors="coerce"
    )

    # فیلدهای پایه گزارش ۱۱ ستونه
    strike = find_column(scored, ["قیمت اعمال"])
    breakeven = find_column(scored, ["سر به سر"])
    breakeven_distance = find_column(scored, ["اختلاف تا سر به سر"])
    expiry = find_column(scored, ["تاریخ سررسید"])

    work["اعمال"] = (
        pd.to_numeric(scored[strike], errors="coerce")
        if strike else pd.NA
    )
    work["سر به سری"] = (
        pd.to_numeric(scored[breakeven], errors="coerce")
        if breakeven else pd.NA
    )
    work["فاصله سر به سری"] = (
        pd.to_numeric(scored[breakeven_distance], errors="coerce") * 100
        if breakeven_distance else pd.NA
    )
    work["سررسید"] = (
        scored[expiry].astype(str).str.strip()
        if expiry else "داده موجود نیست"
    )

    volume = find_column(scored, ["حجم معاملات", "حجم کل", "Volume"])
    value = find_column(scored, ["ارزش معاملات", "ارزش کل", "TradeValue"])

    if volume:
        work["حجم"] = pd.to_numeric(scored[volume], errors="coerce")
    else:
        work["حجم"] = pd.NA

    if value:
        work["ارزش"] = pd.to_numeric(
            scored[value], errors="coerce"
        )
    else:
        work["ارزش"] = pd.NA

    # انتقال امتیازهای شش‌بلوک برای Audit / گزارش
    score_columns = [
        "BaseScore",
        "BlockScore_Liquidity",
        "BlockScore_Valuation",
        "BlockScore_Payoff",
        "BlockScore_Time",
        "BlockScore_Greeks",
        "BlockScore_Market",
        "ExecutionPenalty",
        "DecayPenalty",
    ]

    for col in score_columns:
        if col in scored.columns:
            work[col] = pd.to_numeric(scored[col], errors="coerce")

    # فقط قراردادهای فعال و واجد شرایط V4.1
    work = work[
        (work["آخرین"] > 0) &
        (work["پایه"] > 0) &
        (work["اهرم"] >= 3.5) &
        (work["RemainingDays"] > 0) &
        work["FinalScore"].notna()
    ].copy()

    if work.empty:
        raise RuntimeError(
            "هیچ قرارداد فعال و واجد شرایط V4.1 با اهرم حداقل ۳٫۵ پیدا نشد"
        )

    # رتبه‌بندی نهایی فقط بر اساس FinalScore موتور V4.1
    work = work.sort_values(
        ["FinalScore", "ارزش", "حجم"],
        ascending=[False, False, False],
        na_position="last"
    ).head(TOP_COUNT)

    return work

def format_report(work, source):
    source = Path(source)
    now = datetime.now(TEHRAN)

    lines = [
        "📊 گزارش رتبه‌بندی اختیار معامله — V4.1",
        "━━━━━━━━━━━━━━━━━━━━",
        "📥 منبع: OptionSchool24",
        f"📄 فایل: {source.name}",
        f"⏱ زمان تولید: {now.strftime('%Y/%m/%d %H:%M:%S')}",
        f"📌 تعداد قراردادها: {len(work)}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    def fmt(v):
        if pd.isna(v):
            return "داده موجود نیست"
        return f"{float(v):,.2f}".replace(".00", "")

    def text(v):
        if pd.isna(v):
            return "داده موجود نیست"
        return str(v).strip()

    for rank, (_, row) in enumerate(work.iterrows(), 1):
        distance = row.get("فاصله سر به سری", pd.NA)
        distance_text = (
            "داده موجود نیست"
            if pd.isna(distance)
            else f"{float(distance):+.2f}%"
        )

        lines.extend([
            f"🔹 {rank}. {row['نماد']}",
            "",
            f"💰 اعمال: {fmt(row.get('اعمال', pd.NA))}",
            f"📌 آخرین: {fmt(row['آخرین'])}",
            f"🎯 سر‌به‌سر: {fmt(row.get('سر به سری', pd.NA))}",
            f"📈 پایه: {fmt(row['پایه'])}",
            f"⚖️ اهرم: {fmt(row['اهرم'])}",
            f"📏 فاصله سر‌به‌سر: {distance_text}",
            f"📅 سررسید: {text(row.get('سررسید', pd.NA))}",
            f"⏳ باقی‌مانده: {fmt(row['RemainingDays'])} روز",
            f"🏆 امتیاز: {fmt(row['FinalScore'])}",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
        ])

    return "\n".join(lines)


def main():
    source = download_optionschool()
    work = build_report(source)

    report = format_report(work, source)

    output = ROOT / "output"
    output.mkdir(exist_ok=True)

    report_file = output / "latest_report.txt"
    report_file.write_text(report, encoding="utf-8")

    print(report)
    print("\nREPORT_FILE =", report_file)


if __name__ == "__main__":
    main()
