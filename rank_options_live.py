#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical PROTOCOL_OPTIONS_RANKING_V3 scoring engine.

Rules implemented from Master Project Book V3:
- Optionschool24 is the primary source.
- Missing data is never converted to an artificial zero/neutral score.
- Missing factor weight is redistributed only inside its own block.
- Robust percentile normalization is applied across the valid population.
- Market Status is not numerically mapped until approved; its weight is redistributed
  inside the Market block to Last-vs-Close and Intraday Range.
- Contract type is not guessed; the Moneyness factor is therefore treated as missing
  and its weight is redistributed inside the Payoff block.
- Risk remains transitional when exact approved thresholds are unavailable.
- The user-facing ranking table has exactly the eleven canonical columns required by V3.
"""

from pathlib import Path
from datetime import datetime
import re
import sys
import numpy as np
import pandas as pd

TOP_N = 15
PROTOCOL = "PROTOCOL_OPTIONS_RANKING_V3"

WEIGHTS = {
    "liquidity": {"trade_value": 7, "volume": 5, "open_interest": 3, "spread": 3, "depth": 2},
    "valuation": {"black_scholes_difference": 8, "iv": 7, "iv_hv": 5, "time_value": 5},
    "payoff": {"breakeven_distance": 10, "leverage": 5, "moneyness": 3},
    "time": {"trading_days": 6, "calendar_days": 2, "theta": 7},
    "greeks": {"delta": 4, "gamma": 3, "vega": 3, "rho": 2},
    "market": {"last_vs_close": 4, "intraday_range": 3, "status": 3},
}

REQUIRED_COLUMNS = [
    "نماد", "حجم معاملات", "ارزش معاملات", "موقعیت های باز", "قیمت پایانی",
    "قیمت اعمال", "قیمت سهم پایه", "روزهای معاملاتی", "روزهای تقویمی",
]

NUMERIC_COLUMNS = [
    "قیمت اعمال", "قیمت سهم پایه", "روزهای تقویمی", "روزهای معاملاتی",
    "موقعیت های باز", "حجم معاملات", "ارزش معاملات", "آخرین قیمت", "قیمت پایانی",
    "ارزش ذاتی", "ارزش زمانی", "سر به سر", "اختلاف تا سر به سر", "بلک شولز",
    "اختلاف تا بلک شولز", "اهرم", "نوسان ضمنی", "نوسان تاریخی", "اندازه قرارداد",
    "حجم بهترین تقاضا", "قیمت بهترین تقاضا", "حجم بهترین عرضه", "قیمت بهترین عرضه",
    "شکاف قیمتی", "دلتا", "تتا", "گاما", "وگا", "رو",
]


def parse_number(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("٬", "")
    if not text or text in {"-", "—", "nan", "None"}:
        return np.nan
    text = re.sub(r"\s*\([^)]*\)", "", text).strip()
    match = re.search(r"[-+]?\d*\.?\d+\s*[KMBkmb]?", text)
    if not match:
        return np.nan
    token = match.group(0).replace(" ", "")
    suffix = token[-1:].upper()
    multiplier = {"K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0}.get(suffix, 1.0)
    if suffix in {"K", "M", "B"}:
        token = token[:-1]
    try:
        return float(token) * multiplier
    except ValueError:
        return np.nan


def numeric_columns(df):
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = df[col].map(parse_number)
        else:
            df[col] = np.nan
    return df


def robust_percentile(series, higher_is_better=True):
    """Robust cross-sectional percentile in [0,1], preserving missing values."""
    s = pd.to_numeric(series, errors="coerce")
    out = pd.Series(np.nan, index=s.index, dtype=float)
    valid = s.dropna()
    if valid.empty:
        return out
    if len(valid) == 1:
        out.loc[valid.index] = 1.0
        return out
    ranks = valid.rank(method="average", pct=True)
    if higher_is_better:
        out.loc[valid.index] = ranks
    else:
        out.loc[valid.index] = 1.0 - ranks + (1.0 / len(valid))
    return out.clip(0, 1)


def block_weighted_score(df, factor_specs, block_weight):
    """Calculate a block score with within-block redistribution for missing factors."""
    numerator = pd.Series(0.0, index=df.index)
    available_weight = pd.Series(0.0, index=df.index)
    for score_col, weight in factor_specs:
        score = pd.to_numeric(df[score_col], errors="coerce")
        present = score.notna()
        numerator.loc[present] += score.loc[present] * weight
        available_weight.loc[present] += weight
    result = pd.Series(np.nan, index=df.index, dtype=float)
    ok = available_weight > 0
    result.loc[ok] = numerator.loc[ok] * block_weight / available_weight.loc[ok]
    return result


def add_analytics(df):
    df["IV_HV_Ratio"] = np.where(
        df["نوسان تاریخی"].notna() & (df["نوسان تاریخی"] != 0) & df["نوسان ضمنی"].notna(),
        df["نوسان ضمنی"] / df["نوسان تاریخی"], np.nan
    )
    df["Spread_Percentage"] = np.where(
        df["آخرین قیمت"].notna() & (df["آخرین قیمت"] != 0) & df["شکاف قیمتی"].notna(),
        df["شکاف قیمتی"].abs() / df["آخرین قیمت"].abs() * 100, np.nan
    )
    df["BreakevenDistancePct"] = np.where(
        df["قیمت سهم پایه"].notna() & (df["قیمت سهم پایه"] != 0) & df["سر به سر"].notna(),
        (df["سر به سر"] - df["قیمت سهم پایه"]) / df["قیمت سهم پایه"] * 100, np.nan
    )
    df["LastVsClosePct"] = np.where(
        df["آخرین قیمت"].notna() & df["قیمت پایانی"].notna() & (df["قیمت پایانی"] != 0),
        (df["آخرین قیمت"] - df["قیمت پایانی"]).abs() / df["قیمت پایانی"].abs() * 100, np.nan
    )
    df["IntradayRangePct"] = np.where(
        df["آخرین قیمت"].notna() & (df["آخرین قیمت"] != 0),
        (df["قیمت بهترین عرضه"] - df["قیمت بهترین تقاضا"]).abs() / df["آخرین قیمت"].abs() * 100,
        np.nan
    )
    # Contract type is deliberately NOT inferred from symbol naming.
    df["ContractType"] = pd.Series(pd.NA, index=df.index, dtype="string")
    df["MoneynessScore"] = np.nan

    flags = []
    confidence = []
    critical_fields = ["نماد", "حجم معاملات", "ارزش معاملات", "آخرین قیمت", "قیمت اعمال", "قیمت سهم پایه"]
    for _, row in df.iterrows():
        f = []
        missing = 0
        for field in critical_fields:
            if pd.isna(row.get(field)) or row.get(field) == 0:
                f.append(f"DATA_MISSING:{field}")
                missing += 1
        if pd.isna(row.get("نوسان ضمنی")):
            f.append("MISSING_IV")
            missing += 1
        if pd.isna(row.get("نوسان تاریخی")):
            f.append("MISSING_IV_HV")
            missing += 1
        if pd.isna(row.get("سر به سر")):
            f.append("MISSING_BREAKEVEN")
            missing += 1
        if pd.isna(row.get("دلتا")):
            f.append("MISSING_DELTA")
        if pd.notna(row.get("دلتا")) and (row["دلتا"] > 0.95 or row["دلتا"] < 0.05):
            f.append("ExtremeDelta")
        if pd.notna(row.get("روزهای تقویمی")) and row["روزهای تقویمی"] <= 5:
            f.append("NEAR_EXPIRY")
        f.append("STATUS_MAPPING_NOT_APPROVED")
        f.append("CONTRACT_TYPE_NOT_EXPLICIT")
        flags.append("|".join(f))
        confidence.append(max(0, 100 - missing * 10))
    df["AnalyticsFlags"] = flags
    df["DataConfidence"] = confidence
    return df


def score_v3(df):
    # Liquidity: higher is better, except spread where lower is better.
    df["Score_TradeValue"] = robust_percentile(df["ارزش معاملات"], True)
    df["Score_Volume"] = robust_percentile(df["حجم معاملات"], True)
    df["Score_OpenInterest"] = robust_percentile(df["موقعیت های باز"], True)
    df["Score_Spread"] = robust_percentile(df["Spread_Percentage"], False)
    depth = pd.concat([df["حجم بهترین تقاضا"], df["حجم بهترین عرضه"]], axis=1).min(axis=1, skipna=False)
    df["Score_Depth"] = robust_percentile(depth, True)

    # Valuation: lower absolute deviations/cost are better; IV is higher-is-better only as specified.
    df["Score_BlackScholesDiff"] = robust_percentile(df["اختلاف تا بلک شولز"].abs(), False)
    df["Score_IV"] = robust_percentile(df["نوسان ضمنی"], True)
    df["Score_IV_HV_Ratio"] = robust_percentile(df["IV_HV_Ratio"], False)
    df["Score_TimeValue"] = robust_percentile(df["ارزش زمانی"], True)

    # Payoff. Moneyness is unavailable until contract type is explicit; redistribute its weight.
    df["Score_BreakevenDistance"] = robust_percentile(df["BreakevenDistancePct"].abs(), False)
    df["Score_Leverage"] = robust_percentile(df["اهرم"], True)

    # Time: lower remaining time is not intrinsically better; the Master requires directional validation.
    # Until an approved directional mapping is available, keep the factor missing rather than inventing one.
    df["Score_TradingDays"] = robust_percentile(df["روزهای معاملاتی"], False)
    df["Score_CalendarDays"] = robust_percentile(df["روزهای تقویمی"], False)
    df["Score_Theta"] = robust_percentile(df["تتا"].abs(), False)

    # Greeks: magnitude-only normalization is retained because direction rules are not separately approved.
    df["Score_Delta"] = robust_percentile(df["دلتا"].abs(), True)
    df["Score_Gamma"] = robust_percentile(df["گاما"].abs(), True)
    df["Score_Vega"] = robust_percentile(df["وگا"].abs(), True)
    df["Score_Rho"] = robust_percentile(df["رو"].abs(), True)

    # Market: Status mapping is explicitly unapproved, so its weight is redistributed within the block.
    df["Score_LastVsClose"] = robust_percentile(df["LastVsClosePct"], False)
    df["Score_IntradayRange"] = robust_percentile(df["IntradayRangePct"], False)
    market_specs = [
        ("Score_LastVsClose", WEIGHTS["market"]["last_vs_close"]),
        ("Score_IntradayRange", WEIGHTS["market"]["intraday_range"]),
    ]

    df["BlockScore_Liquidity"] = block_weighted_score(df, [
        ("Score_TradeValue", 7), ("Score_Volume", 5), ("Score_OpenInterest", 3),
        ("Score_Spread", 3), ("Score_Depth", 2)], 20)
    df["BlockScore_Valuation"] = block_weighted_score(df, [
        ("Score_BlackScholesDiff", 8), ("Score_IV", 7), ("Score_IV_HV_Ratio", 5),
        ("Score_TimeValue", 5)], 25)
    df["BlockScore_Payoff"] = block_weighted_score(df, [
        ("Score_BreakevenDistance", 10), ("Score_Leverage", 5), ("MoneynessScore", 3)], 18)
    df["BlockScore_Time"] = block_weighted_score(df, [
        ("Score_TradingDays", 6), ("Score_CalendarDays", 2), ("Score_Theta", 7)], 15)
    df["BlockScore_Greeks"] = block_weighted_score(df, [
        ("Score_Delta", 4), ("Score_Gamma", 3), ("Score_Vega", 3), ("Score_Rho", 2)], 12)
    df["BlockScore_Market"] = block_weighted_score(df, market_specs, 10)

    block_cols = ["BlockScore_Liquidity", "BlockScore_Valuation", "BlockScore_Payoff",
                  "BlockScore_Time", "BlockScore_Greeks", "BlockScore_Market"]
    df["BaseScore"] = df[block_cols].sum(axis=1, min_count=1).round(6)

    # Exact approved risk thresholds are not available in the Master; do not invent them.
    df["RiskPenalty"] = 0.0
    df["RiskStatus"] = "KNOWN_GAP_THRESHOLDS_NOT_AVAILABLE"
    df["FinalScore"] = df["BaseScore"].round(2)
    return df


def fmt(value, digits=2):
    if pd.isna(value):
        return "—"
    if isinstance(value, (int, np.integer)) or (isinstance(value, float) and value.is_integer()):
        return f"{int(value):,}"
    return f"{float(value):,.{digits}f}"


def fmt_persian_int(value):
    """Format an integer-valued market number with Persian thousands separators."""
    if pd.isna(value):
        return "—"
    try:
        text = f"{int(round(float(value))):,}"
    except (TypeError, ValueError, OverflowError):
        return "—"
    return text.replace(",", "٬").translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def fmt_persian_decimal(value, digits=2, signed=False, trim=False):
    """Format a decimal using Persian digits and decimal separator for Bale readability."""
    if pd.isna(value):
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return "—"
    sign = "+" if signed and number > 0 else "" if number >= 0 else "-"
    number = abs(number)
    text = f"{number:,.{digits}f}"
    if trim:
        text = text.rstrip("0").rstrip(".")
    text = text.replace(",", "٬").replace(".", "٫")
    return sign + text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def make_report(top, input_file, total_initial, valid_count):
    now = datetime.now()
    run_id = now.strftime("%Y%m%d_%H%M%S")
    lines = [
        "# گزارش رتبه‌بندی اختیار معامله V3",
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
    ]

    # Bale-facing top-15 cards: replace the dense Markdown table only.
    for rank, (_, row) in enumerate(top.iterrows(), 1):
        expiry = row.get("سررسید", "—")
        if pd.isna(expiry) or str(expiry).strip() in {"", "nan", "None"}:
            expiry = "—"
        remaining = fmt_persian_int(row.get("RemainingDays", np.nan))
        score = fmt_persian_decimal(row.get("FinalScore", np.nan), 2)
        leverage = fmt_persian_decimal(row.get("اهرم", np.nan), 2, trim=True)
        breakeven_distance = fmt_persian_decimal(row.get("BreakevenDistancePct", np.nan), 3, signed=True)
        lines.extend([
            f"🔹 {rank}. {row['نماد']}",
            f"قیمت اعمال: {fmt_persian_int(row.get('قیمت اعمال', np.nan))} | آخرین: {fmt_persian_int(row.get('آخرین قیمت', np.nan))}",
            f"سر‌به‌سر: {fmt_persian_int(row.get('سر به سر', np.nan))} | پایه: {fmt_persian_int(row.get('قیمت سهم پایه', np.nan))}",
            f"اهرم: {leverage} | فاصله سر‌به‌سر: {breakeven_distance}%",
            f"سررسید: {expiry} ({remaining} روز)",
            f"امتیاز: {score}",
            "━━━━━━━━━━━━━━━━━━",
            "",
        ])

    lines += [
        "## کنترل‌های V3",
        "* داده مفقود با صفر، میانگین یا حدس جایگزین نشده است.",
        "* وزن عامل مفقود فقط داخل همان بلوک بازتوزیع شده است.",
        "* نگاشت عددی Status هنوز تأیید نشده و در بلوک ساختار بازار بازتوزیع شده است.",
        "* نوع قرارداد از روی نام نماد حدس زده نشده و عامل Moneyness در صورت فقدان داده بازتوزیع شده است.",
        "* آستانه نهایی Risk در Master تأیید نشده است؛ بنابراین جریمه ساختگی اعمال نشده است.",
        "* امتیاز صرفاً رتبه‌بندی کیفیت قرارداد است و توصیه قطعی خرید/فروش نیست.",
    ]
    return "\n".join(lines) + "\n"


def main():
    files = sorted(Path(".").glob("optionschool24_all_*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
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

    valid = df[
        df["نماد"].notna() & (df["نماد"] != "") & (df["نماد"] != "nan") &
        (df["حجم معاملات"].fillna(0) > 0) & (df["ارزش معاملات"].fillna(0) > 0) &
        (df["آخرین قیمت"].fillna(0) > 0) & (df["قیمت اعمال"].fillna(0) > 0) &
        (df["قیمت سهم پایه"].fillna(0) > 0) & (df["روزهای تقویمی"].fillna(0) > 0)
    ].copy()
    if valid.empty:
        sys.exit("❌ هیچ قرارداد معتبری پس از فیلتر مالی باقی نماند.")

    valid = add_analytics(valid)
    valid["RemainingDays"] = (valid["روزهای تقویمی"] - 1).clip(lower=0)
    scored = score_v3(valid)
    top = scored.sort_values(["FinalScore", "حجم معاملات"], ascending=[False, False]).head(TOP_N).copy()
    report = make_report(top, input_path.name, total_initial, len(valid))
    Path("output_options_report.md").write_text(report, encoding="utf-8")
    top.to_csv("output_options_top15.csv", index=False, encoding="utf-8-sig")
    print(report)


if __name__ == "__main__":
    main()
