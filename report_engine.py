#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import argparse
import hashlib
import json
import pandas as pd
import requests
from scoring_engine import ENGINE_VERSION, MIN_LEVERAGE, normalize_text
from opportunity_engine import run_shadow

ROOT = Path(__file__).resolve().parent
TEHRAN = ZoneInfo("Asia/Tehran")

OPTIONSCHOOL_URL = "https://s3.optionschool24.com/export/excel?type=1"
TOP_COUNT = int(os.getenv("TOP_COUNT", "15"))


def download_optionschool():
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    stamp = datetime.now(TEHRAN).strftime("%Y%m%d_%H%M%S_%f")
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


def build_report(path, top_count=None, symbol_prefix=None):
    limit = TOP_COUNT if top_count is None else top_count
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("تعداد قراردادها باید عدد صحیح مثبت باشد")
    df = pd.read_excel(path)

    # V4.1 scoring engine: GitHub six-block production candidate
    from scoring_engine import score_dataframe

    scored = score_dataframe(df)

    # Shadow Opportunity Engine scans the full scored universe before symbol/Top-N
    # filtering. It never changes FinalScore, ranking, or report contents.
    snapshot_id = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    shadow = run_shadow(scored, snapshot_id)
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
        scored["BreakevenDistancePct"]
    )
    work["سررسید"] = (
        scored[expiry].astype("string").str.strip()
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
        "DataConfidence",
    ]

    for col in score_columns:
        if col in scored.columns:
            work[col] = pd.to_numeric(scored[col], errors="coerce")
    work["AnalyticsFlags"] = scored["AnalyticsFlags"]
    work.attrs.update(scored.attrs)
    work.attrs["unscorable_count"] = int(scored["FinalScore"].isna().sum())

    # فقط قراردادهای فعال و واجد شرایط V4.1
    work = work[
        (work["آخرین"] > 0) &
        (work["پایه"] > 0) &
        (work["اهرم"] >= MIN_LEVERAGE) &
        (work["RemainingDays"] > 0) &
        work["FinalScore"].notna()
    ].copy()

    if work.empty:
        raise RuntimeError(
            "هیچ قرارداد دارای داده کافی برای امتیازدهی شش‌بلوک پیدا نشد"
        )

    # فیلتر نماد باید قبل از رتبه‌بندی و انتخاب Top-N انجام شود.
    # بنابراین درخواست نماد، از بین کل قراردادهای همان نماد رتبه‌بندی می‌شود.
    if symbol_prefix:
        prefix = normalize_text(symbol_prefix)
        work = work[
            work["نماد"].str.startswith(prefix, na=False)
        ].copy()

        if work.empty:
            raise RuntimeError(
                f"هیچ قرارداد فعال و واجد شرایطی برای نماد «{prefix}» پیدا نشد"
            )

    # رتبه‌بندی نهایی فقط بر اساس FinalScore موتور V4.1
    work = work.sort_values(
        ["FinalScore", "ارزش", "حجم", "نماد"],
        ascending=[False, False, False, True],
        na_position="last"
    )

    work = work.head(limit)

    # Keep shadow evidence attached to the report object for audit persistence.
    work.attrs["opportunity_shadow"] = shadow
    work.attrs["opportunity_shadow_summary"] = shadow.get("summary", {})

    return work

def format_report(work, source):
    source = Path(source)
    now = datetime.now(TEHRAN)

    lines = [
        f"📊 گزارش رتبه‌بندی اختیار معامله — {ENGINE_VERSION}",
        "━━━━━━━━━━━━━━━━━━━━",
        "📥 منبع: OptionSchool24",
        f"📄 فایل: {source.name}",
        f"⏱ زمان تولید: {now.strftime('%Y/%m/%d %H:%M:%S')}",
        f"📌 تعداد قراردادها: {len(work)}",
        "⚠️ زمان واقعی داده بازار در این ورودی تأیید نشده؛ زمان بالا فقط زمان تولید گزارش است.",
        "ℹ️ امتیاز، رتبه نسبی قراردادهاست؛ احتمال سود یا توصیه خرید/فروش نیست.",
        "ℹ️ روز باقی‌مانده طبق قرارداد فعلی منبع: روزهای تقویمی منهای یک.",
        f"ورودی: {work.attrs.get('input_count', 'نامشخص')} | حذف نامعتبر: {work.attrs.get('excluded_count', 'نامشخص')} | فاقد بلوک کامل: {work.attrs.get('unscorable_count', 'نامشخص')}",
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
            f"🔎 شاخص کامل‌بودن داده: {fmt(row.get('DataConfidence', pd.NA))}/100 (احتمال سود نیست)",
            f"کاهش بابت اجرا: {fmt(row.get('ExecutionPenalty', 0) * 100)}٪ | کاهش بابت سررسید: {fmt(row.get('DecayPenalty', 0) * 100)}٪",
            "⚠️ " + format_flags(row.get("AnalyticsFlags", "")),
            "",
            "━━━━━━━━━━━━━━━━━━━━",
        ])

    return "\n".join(lines)


def format_flags(flags):
    labels = {
        "MISSING_IV": "نوسان ضمنی موجود نیست",
        "MISSING_IV_HV": "نوسان تاریخی موجود نیست",
        "MISSING_BREAKEVEN": "سر‌به‌سر موجود نیست",
        "MISSING_DELTA": "دلتا موجود نیست",
        "ExtremeDelta": "قدر مطلق دلتا نزدیک حد نهایی است",
        "NEAR_EXPIRY": "نزدیک سررسید",
        "STATUS_MAPPING_NOT_APPROVED": "وضعیت بازار در امتیاز لحاظ نشده",
        "CONTRACT_TYPE_NOT_EXPLICIT": "عامل Moneyness لحاظ نشده",
        "MISSING_INTRADAY_RANGE": "دامنه روزانه موجود نیست",
    }
    return "؛ ".join(labels.get(flag, flag) for flag in str(flags).split("|") if flag) or "هشداری ثبت نشده"


def save_report(work, source):
    report = format_report(work, source)
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    report_file = output / "latest_report.txt"
    temporary = output / "latest_report.txt.tmp"
    temporary.write_text(report, encoding="utf-8")
    temporary.replace(report_file)
    shadow = work.attrs.get("opportunity_shadow", {
        "status": "INSUFFICIENT_DATA",
        "engine_version": "OPP-SHADOW-1.0",
        "snapshot_id": None,
        "summary": {},
        "cases": [],
    })
    shadow_file = output / "latest_opportunity_shadow.json"
    shadow_temp = output / "latest_opportunity_shadow.json.tmp"
    shadow_temp.write_text(
        json.dumps(shadow, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    shadow_temp.replace(shadow_file)

    audit_attrs = dict(work.attrs)
    audit_attrs.pop("opportunity_shadow", None)
    audit = {
        **audit_attrs,
        "opportunity_shadow": {
            "status": shadow.get("status"),
            "engine_version": shadow.get("engine_version"),
            "snapshot_id": shadow.get("snapshot_id"),
            "summary": shadow.get("summary", {}),
            "case_file": shadow_file.name,
        },
        "generated_at": datetime.now(TEHRAN).isoformat(),
        "source_file": Path(source).name,
        "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "market_data_timestamp": None,
        "freshness_status": "UNVERIFIED_SOURCE_TIMESTAMP_MISSING",
        "selected_count": len(work),
        "selected": json.loads(work.to_json(orient="records", force_ascii=False)),
    }
    audit_temp = output / "latest_audit.json.tmp"
    audit_temp.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    audit_temp.replace(output / "latest_audit.json")
    return report


def main():
    parser = argparse.ArgumentParser(description="Generate V4.1.1 report without sending to Bale")
    parser.add_argument("--input", type=Path, help="Use an existing workbook; otherwise download")
    parser.add_argument("--symbol", help="Symbol prefix; filtered before Top-N")
    parser.add_argument("--top", type=int, default=None)
    args = parser.parse_args()
    source = args.input if args.input is not None else download_optionschool()
    work = build_report(source, top_count=args.top, symbol_prefix=args.symbol)
    report = save_report(work, source)

    print(report)
    print("\nREPORT_FILE =", ROOT / "output" / "latest_report.txt")


if __name__ == "__main__":
    main()
