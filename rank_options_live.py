#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
موتور رتبه‌بندی اختیار معامله ـ PROTOCOL_OPTIONS_RANKING_V3
منبع داده مجاز و انحصاری: Optionschool24
این خروجی رتبه‌بندی کیفیت قرارداد است و توصیه قطعی خرید/فروش نیست.
"""

from pathlib import Path
from datetime import datetime
import re
import sys
import numpy as np
import pandas as pd

TOP_N = 15
PROTOCOL = "PROTOCOL_OPTIONS_RANKING_V3"

# مجموع وزن عوامل هر بلوک برابر وزن همان بلوک است؛ امتیاز نهایی در بازه تقریبی 0 تا 100 است.
WEIGHTS = {
    "liquidity": {
        "trade_value": 7, "volume": 5, "open_interest": 3, "spread": 3, "depth": 2
    },
    "valuation": {
        "black_scholes_difference": 8, "iv": 7, "iv_hv": 5, "time_value": 5
    },
    "payoff": {
        "breakeven_distance": 10, "leverage": 5, "moneyness": 3
    },
    "time": {
        "trading_days": 6, "calendar_days": 2, "theta": 7
    },
    "greeks": {
        "delta": 4, "gamma": 3, "vega": 3, "rho": 2
    },
    "market": {"market_factor": 10},
}

REQUIRED_COLUMNS = [
    "نماد", "حجم معاملات", "ارزش معاملات", "موقعیت های باز",
    "قیمت پایانی", "اهرم", "نوسان ضمنی", "دلتا",
    "قیمت اعمال", "قیمت سهم پایه", "روزهای معاملاتی", "روزهای تقویمی",
]


def parse_number(value):
    """تبدیل امن اعداد Optionschool24 شامل K/M/B و متن درصدی داخل پرانتز."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)

    text = str(value).strip().replace(",", "").replace("٬", "")
    if not text or text in {"-", "—", "nan", "None"}:
        return np.nan

    # نمونه: 799870 (-0.2%)  => فقط بخش عدد اصلی
    text = re.sub(r"\s*\([^)]*\)", "", text).strip()

    match = re.search(r"[-+]?\d*\.?\d+\s*[KMBkmb]?", text)
    if not match:
        return np.nan

    token = match.group(0).replace(" ", "")
    multiplier = 1.0
    suffix = token[-1:].upper()
    if suffix == "K":
        multiplier, token = 1_000.0, token[:-1]
    elif suffix == "M":
        multiplier, token = 1_000_000.0, token[:-1]
    elif suffix == "B":
        multiplier, token = 1_000_000_000.0, token[:-1]

    try:
        return float(token) * multiplier
    except ValueError:
        return np.nan


def numeric_columns(df):
    columns = [
        "قیمت اعمال", "قیمت سهم پایه", "روزهای تقویمی", "روزهای معاملاتی",
        "موقعیت های باز", "حجم معاملات", "ارزش معاملات", "آخرین قیمت",
        "قیمت پایانی", "ارزش ذاتی", "ارزش زمانی", "سر به سر",
        "اختلاف تا سر به سر", "بلک شولز", "اختلاف تا بلک شولز",
        "اهرم", "نوسان ضمنی", "نوسان تاریخی", "اندازه قرارداد",
        "حجم بهترین تقاضا", "قیمت بهترین تقاضا",
        "حجم بهترین عرضه", "قیمت بهترین عرضه",
        "شکاف قیمتی", "دلتا", "تتا", "گاما", "وگا", "رو",
    ]
    for col in columns:
        if col in df.columns:
            df[col] = df[col].map(parse_number)
        else:
            df[col] = np.nan
    return df


def positive_max_score(series):
    """نرمال‌سازی صفر تا یک؛ مقدار بیشتر بهتر است."""
    s = pd.to_numeric(series, errors="coerce").fillna(0).clip(lower=0)
    maximum = s.max()
    return s / maximum if maximum > 0 else pd.Series(0.0, index=s.index)


def inverse_abs_score(series):
    """نرمال‌سازی صفر تا یک؛ قدرمطلق کمتر بهتر است."""
    s = pd.to_numeric(series, errors="coerce").abs().fillna(0)
    maximum = s.max()
    return 1 - (s / maximum) if maximum > 0 else pd.Series(1.0, index=s.index)


def detect_contract_type(symbol):
    """
    Optionschool24 در نمونه فعلی نوع را به شکل صریح ندارد.
    این موتور نوع نامشخص را UNKNOWN نگه می‌دارد تا بدون حدس، امتیاز Moneyness خنثی شود.
    """
    return pd.Series("UNKNOWN", index=symbol.index)


def add_analytics(df):
    df["IV_HV_Ratio"] = np.where(
        df["نوسان تاریخی"].fillna(0) != 0,
        (df["نوسان ضمنی"] / df["نوسان تاریخی"]).round(2),
        0.0,
    )
    df["Spread_Percentage"] = np.where(
        df["قیمت پایانی"].fillna(0) != 0,
        (df["شکاف قیمتی"] / df["قیمت پایانی"] * 100).round(2),
        0.0,
    )

    df["نوع قرارداد"] = detect_contract_type(df["نماد"])
    df["Moneyness"] = "UNKNOWN"

    # چون نوع قرارداد در ستون‌های فعلی وجود ندارد، مانی‌نس را از قیمت اعمال/پایه
    # استخراج می‌کنیم اما در صورت ناشناخته‌بودن نوع، امتیاز خنثی خواهد بود.
    call_itm = df["قیمت سهم پایه"] > df["قیمت اعمال"]
    call_atm = df["قیمت سهم پایه"] == df["قیمت اعمال"]
    df.loc[call_itm, "Moneyness"] = "ITM"
    df.loc[call_atm, "Moneyness"] = "ATM"
    df.loc[~(call_itm | call_atm), "Moneyness"] = "OTM"

    flags_all, confidences = [], []
    check_fields = [
        "نماد", "حجم معاملات", "موقعیت های باز", "قیمت پایانی",
        "اهرم", "نوسان ضمنی", "دلتا",
    ]

    for _, row in df.iterrows():
        confidence, flags = 100, []

        for field in check_fields:
            value = row.get(field)
            invalid = pd.isna(value) or value == "" or value == 0
            if invalid:
                flags.append(f"MissingOrZero_{field}")
                confidence -= 10

        if row.get("اهرم", 0) == 0:
            flags.append("ZeroLeverage")
            confidence -= 5

        if pd.notna(row.get("ارزش زمانی")) and row["ارزش زمانی"] < 0:
            flags.append("NegativeTimeValue")
            confidence -= 10

        delta = row.get("دلتا")
        if pd.notna(delta) and (delta > 0.95 or delta < 0.05):
            flags.append("ExtremeDelta")
            confidence -= 5

        flags_all.append("|".join(flags) if flags else "None")
        confidences.append(max(0, confidence))

    df["AnalyticsFlags"] = flags_all
    df["DataConfidence"] = confidences
    return df


def score_v3(df):
    # Liquidity
    df["Score_TradeValue"] = positive_max_score(df["ارزش معاملات"])
    df["Score_Volume"] = positive_max_score(df["حجم معاملات"])
    df["Score_OpenInterest"] = positive_max_score(df["موقعیت های باز"])
    df["Score_Spread"] = inverse_abs_score(df["Spread_Percentage"])
    depth = df["حجم بهترین تقاضا"].fillna(0) + df["حجم بهترین عرضه"].fillna(0)
    df["Score_Depth"] = positive_max_score(depth)

    # Valuation
    df["Score_BlackScholesDiff"] = inverse_abs_score(df["اختلاف تا بلک شولز"])
    df["Score_IV"] = positive_max_score(df["نوسان ضمنی"])
    df["Score_IV_HV_Ratio"] = positive_max_score(df["IV_HV_Ratio"])
    df["Score_TimeValue"] = positive_max_score(df["ارزش زمانی"])

    # Payoff
    df["Score_BreakevenDistance"] = inverse_abs_score(df["اختلاف تا سر به سر"])
    df["Score_Leverage"] = positive_max_score(df["اهرم"])
    df["Score_Moneyness"] = df["Moneyness"].map({"ITM": 1.0, "ATM": 0.5, "OTM": 0.0}).fillna(0.0)

    # Time
    df["Score_TradingDays"] = positive_max_score(df["روزهای معاملاتی"])
    df["Score_CalendarDays"] = positive_max_score(df["روزهای تقویمی"])
    df["Score_Theta"] = positive_max_score(df["تتا"].abs())

    # Greeks
    df["Score_Delta"] = positive_max_score(df["دلتا"].abs())
    df["Score_Gamma"] = positive_max_score(df["گاما"].abs())
    df["Score_Vega"] = positive_max_score(df["وگا"].abs())
    df["Score_Rho"] = positive_max_score(df["رو"].abs())

    # مطابق موتور مرجع V3: فعلاً Market factor ثابت و بدون منبع خارجی است.
    df["Score_Market"] = 0.5

    w = WEIGHTS
    df["BlockScore_Liquidity"] = (
        df["Score_TradeValue"] * w["liquidity"]["trade_value"] +
        df["Score_Volume"] * w["liquidity"]["volume"] +
        df["Score_OpenInterest"] * w["liquidity"]["open_interest"] +
        df["Score_Spread"] * w["liquidity"]["spread"] +
        df["Score_Depth"] * w["liquidity"]["depth"]
    )
    df["BlockScore_Valuation"] = (
        df["Score_BlackScholesDiff"] * w["valuation"]["black_scholes_difference"] +
        df["Score_IV"] * w["valuation"]["iv"] +
        df["Score_IV_HV_Ratio"] * w["valuation"]["iv_hv"] +
        df["Score_TimeValue"] * w["valuation"]["time_value"]
    )
    df["BlockScore_Payoff"] = (
        df["Score_BreakevenDistance"] * w["payoff"]["breakeven_distance"] +
        df["Score_Leverage"] * w["payoff"]["leverage"] +
        df["Score_Moneyness"] * w["payoff"]["moneyness"]
    )
    df["BlockScore_Time"] = (
        df["Score_TradingDays"] * w["time"]["trading_days"] +
        df["Score_CalendarDays"] * w["time"]["calendar_days"] +
        df["Score_Theta"] * w["time"]["theta"]
    )
    df["BlockScore_Greeks"] = (
        df["Score_Delta"] * w["greeks"]["delta"] +
        df["Score_Gamma"] * w["greeks"]["gamma"] +
        df["Score_Vega"] * w["greeks"]["vega"] +
        df["Score_Rho"] * w["greeks"]["rho"]
    )
    df["BlockScore_Market"] = df["Score_Market"] * w["market"]["market_factor"]

    df["BaseScore"] = (
        df["BlockScore_Liquidity"] + df["BlockScore_Valuation"] +
        df["BlockScore_Payoff"] + df["BlockScore_Time"] +
        df["BlockScore_Greeks"] + df["BlockScore_Market"]
    )

    def risk_penalty(row):
        flags = str(row["AnalyticsFlags"]).split("|")
        penalty = 0.0
        if "ZeroLeverage" in flags:
            penalty += 10
        if "NegativeTimeValue" in flags:
            penalty += 15
        if "MissingOrZero_حجم معاملات" in flags:
            penalty += 20
        penalty += (100 - float(row["DataConfidence"])) * 0.2
        return penalty

    df["RiskPenalty"] = df.apply(risk_penalty, axis=1)
    df["FinalScore"] = (df["BaseScore"] - df["RiskPenalty"]).clip(lower=0).round(2)
    df["PercentileRank"] = (df["FinalScore"].rank(pct=True, method="average") * 100).round(2)
    return df


def fmt(value, digits=2):
    if pd.isna(value):
        return "—"
    if isinstance(value, (int, np.integer)) or (isinstance(value, float) and value.is_integer()):
        return f"{int(value):,}"
    return f"{float(value):,.{digits}f}"


def make_report(top, input_file, total_initial, valid_count):
    now = datetime.now()
    run_id = now.strftime("%Y%m%d_%H%M%S")

    lines = [
        "# گزارش تحلیل اختیار معامله V3",
        f"تاریخ اجرا: {now:%Y-%m-%d %H:%M:%S}",
        f"شناسه اجرا: {run_id}",
        f"نسخه: {PROTOCOL}",
        "",
        "---",
        "",
        "## خلاصه اجرا",
        f"* فایل ورودی: {input_file}",
        f"* تعداد کل قراردادهای اولیه: {total_initial:,}",
        f"* تعداد قراردادهای معتبر پس از فیلتر: {valid_count:,}",
        f"* تعداد قراردادهای گزارش‌شده: {len(top):,}",
        "",
        f"## قراردادهای برتر ({len(top)} مورد)",
        "",
        "| رتبه | نماد | وضعیت | امتیاز نهایی | اهرم | حجم معاملات | موقعیت های باز | شکاف قیمتی | دلتا | IV/HV | Confidence |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for rank, (_, row) in enumerate(top.iterrows(), 1):
        lines.append(
            f"| {rank} | {row['نماد']} | {row['وضعیت']} | "
            f"{fmt(row['FinalScore'])} | {fmt(row['اهرم'])} | "
            f"{fmt(row['حجم معاملات'], 0)} | {fmt(row['موقعیت های باز'], 0)} | "
            f"{fmt(row['شکاف قیمتی'])} | {fmt(row['دلتا'])} | "
            f"{fmt(row['IV_HV_Ratio'])} | {fmt(row['DataConfidence'], 0)} |"
        )

    common_flags = (
        top["AnalyticsFlags"].replace("None", np.nan).dropna()
        .str.split("|").explode().value_counts().head(3)
    )
    flag_text = "، ".join(f"{name}: {count}" for name, count in common_flags.items()) or "موردی ثبت نشد"

    lines += [
        "",
        "## بینش‌های تحلیلی و یادگیری",
        f"* میانگین امتیاز نهایی Top {len(top)}: {top['FinalScore'].mean():.2f}",
        f"* میانگین Confidence: {top['DataConfidence'].mean():.0f}",
        f"* Flagهای پرتکرار: {flag_text}",
        "* امتیاز صرفاً رتبه‌بندی کیفیت قرارداد است و مجوز یا توصیه قطعی خرید/فروش نیست.",
        "",
        "---",
        "",
        "این گزارش به‌صورت خودکار توسط سیستم تحلیل اختیار معامله تولید شده است.",
    ]
    return "\n".join(lines) + "\n"


def main():
    files = sorted(
        Path(".").glob("optionschool24_all_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        sys.exit("❌ فایل Optionschool24 با الگوی optionschool24_all_*.xlsx یافت نشد.")

    input_path = files[0]
    print(f"منبع داده: {input_path.name}")
    df = pd.read_excel(input_path)
    total_initial = len(df)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        sys.exit("❌ ستون‌های ضروری موجود نیستند: " + "، ".join(missing))

    df = numeric_columns(df)
    df["نماد"] = df["نماد"].astype(str).str.strip()

    # Financial Engine: قراردادهای فاقد نماد، حجم، ارزش معامله، قیمت یا سررسید معتبر حذف می‌شوند.
    valid = df[
        df["نماد"].notna() & (df["نماد"] != "") & (df["نماد"] != "nan") &
        (df["حجم معاملات"].fillna(0) > 0) &
        (df["ارزش معاملات"].fillna(0) > 0) &
        (df["قیمت پایانی"].fillna(0) > 0) &
        (df["روزهای تقویمی"].fillna(0) > 0)
    ].copy()

    if valid.empty:
        sys.exit("❌ هیچ قرارداد معتبری پس از فیلتر مالی باقی نماند.")

    valid = add_analytics(valid)
    scored = score_v3(valid)
    top = scored.sort_values(
        ["FinalScore", "DataConfidence", "حجم معاملات"],
        ascending=[False, False, False],
    ).head(TOP_N).copy()

    top.insert(0, "رتبه", range(1, len(top) + 1))
    report = make_report(top, input_path.name, total_initial, len(valid))

    Path("output_options_report.md").write_text(report, encoding="utf-8")
    top.to_csv("output_options_top15.csv", index=False, encoding="utf-8-sig")

    print(f"✅ قرارداد اولیه: {total_initial}")
    print(f"✅ معتبر پس از فیلتر: {len(valid)}")
    print(f"✅ گزارش Top {len(top)} ذخیره شد.")
    print("  - output_options_report.md")
    print("  - output_options_top15.csv")
    print()
    print(report)


if __name__ == "__main__":
    main()
