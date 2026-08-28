
from __future__ import annotations

import os
import sys
import pandas as pd
import requests

TOP_N = 10
MIN_LEVERAGE = 3.0


def find_column(df: pd.DataFrame, names: list[str]) -> str | None:
    columns = {str(col).strip(): col for col in df.columns}
    for name in names:
        if name in columns:
            return columns[name]
    for name in names:
        for norm, orig in columns.items():
            if name in norm:
                return orig
    return None


def numeric(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype="float64")
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("٬", "", regex=False)
        .str.replace("٫", ".", regex=False)
        .str.strip(),
        errors="coerce",
    ).fillna(0)


def format_num(val: float, dec: int = 0) -> str:
    if dec == 0:
        return f"{int(round(val)):,}".replace(",", "٬")
    return f"{val:.{dec}f}".replace(".", "٫")


def format_pct(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.3f}".replace(".", "٫") + "٪"


def build_report(file_path: str) -> str:
    df = pd.read_excel(file_path)

    c_symbol = find_column(df, ["نماد"])
    c_strike = find_column(df, ["قیمت اعمال"])
    c_last = find_column(df, ["آخرین قیمت", "قیمت پایانی", "آخرین"])
    c_base = find_column(df, ["قیمت سهم پایه", "قیمت پایه", "قیمت دارایی پایه", "پایه"])
    c_lev = find_column(df, ["اهرم"])
    c_exp = find_column(df, ["تاریخ سررسید", "سررسید"])
    c_days = find_column(df, ["روزهای باقی‌مانده", "روزهای معاملاتی", "روزهای تقویمی", "مانده تا سررسید"])
    c_score = find_column(df, ["امتیاز نهایی", "Final Score", "امتیاز V3", "امتیاز"])
    c_dist = find_column(df, ["فاصله سر به سری", "فاصله سر به سر", "Distance to Breakeven"])

    req = {"نماد": c_symbol, "اعمال": c_strike, "آخرین": c_last, "پایه": c_base, "اهرم": c_lev, "سررسید": c_exp, "روزها": c_days}
    missing = [k for k, v in req.items() if v is None]
    if missing:
        raise ValueError(f"ستون‌های ضروری یافت نشدند: {', '.join(missing)}")

    # فقط قراردادهای خرید
    df = df[df[c_symbol].astype(str).str.strip().str.startswith("ض")].copy()

    df["_strike"] = numeric(df[c_strike])
    df["_last"] = numeric(df[c_last])
    df["_base"] = numeric(df[c_base])
    df["_lev"] = numeric(df[c_lev])
    df["_days"] = numeric(df[c_days])
    df["_be"] = df["_strike"] + df["_last"]

    if c_dist is not None:
        df["_dist"] = numeric(df[c_dist])
    else:
        df["_dist"] = ((df["_be"] - df["_base"]) / df["_base"].replace(0, pd.NA) * 100).fillna(0)

    # اگر ستون امتیاز نبود، رتبه‌بندی استاندارد
    if c_score is not None:
        df["_score"] = numeric(df[c_score])
    else:
        df["_score"] = (100 - df["_dist"].abs() - (df["_lev"] * 0.5)).clip(lower=0)

    # فیلتر اهرم حداقل ۳
    df = df[df["_lev"] >= MIN_LEVERAGE].copy()

    df = df.sort_values(by=["_score", "_lev"], ascending=[False, True], kind="stable").head(TOP_N)

    lines = [
        "📊 رتبه‌بندی برترین قراردادهای اختیار معامله",
        "پروتکل V3 (منبع: Optionschool24)",
        "فیلتر: اهرم حداقل ۳",
        "━━━━━━━━━━━━━━━━━━",
    ]

    for rank, (_, row) in enumerate(df.iterrows(), start=1):
        sym = str(row[c_symbol]).strip()
        exp = str(row[c_exp]).strip()
        days = int(round(row["_days"]))
        score_val = row["_score"]

        line = (
            f"🔹 {rank}. {sym}\n"
            f"قیمت اعمال: {format_num(row['_strike'])} | آخرین: {format_num(row['_last'])}\n"
            f"سر‌به‌سر: {format_num(row['_be'])} | پایه: {format_num(row['_base'])}\n"
            f"اهرم: {format_num(row['_lev'], 2)} | فاصله سر‌به‌سر: {format_pct(row['_dist'])}\n"
            f"سررسید: {exp} ({days} روز)\n"
            f"امتیاز: {format_num(score_val, 2)}"
        )
        lines.append(line)

    return "\n\n".join(lines)


def send_to_bale(text: str) -> None:
    token = os.environ.get("BALE_BOT_TOKEN")
    chat_id = os.environ.get("BALE_CHAT_ID")
    if not token or not chat_id:
        raise ValueError("متغیرهای BALE_BOT_TOKEN یا BALE_CHAT_ID یافت نشدند.")

    url = f"https://tapi.bale.ai/bot{token}/sendMessage"
    res = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=30)
    res.raise_for_status()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Excel file path required.")
        sys.exit(1)

    file_p = sys.argv[1]
    report_text = build_report(file_p)
    print(report_text)

    if os.getenv("SEND_TO_BALE", "false").lower() == "true":
        send_to_bale(report_text)
        print("✅ پیام با موفقیت به بله ارسال شد.")
