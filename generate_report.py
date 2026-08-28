#!/usr/bin/env python3
import sys
import re
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "output_options_report.md"

def clean_num(val):
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    table = str.maketrans(persian_digits, english_digits)
    val_str = val_str.translate(table)
    val_str = val_str.replace(",", "").strip()

    multiplier = 1.0
    if val_str.endswith("B") or val_str.endswith("b"):
        multiplier = 1e9
        val_str = val_str[:-1]
    elif val_str.endswith("M") or val_str.endswith("m"):
        multiplier = 1e6
        val_str = val_str[:-1]
    elif val_str.endswith("K") or val_str.endswith("k"):
        multiplier = 1e3
        val_str = val_str[:-1]

    val_str = re.sub(r"[^\d.-]", "", val_str)
    try:
        return float(val_str) * multiplier
    except:
        return 0.0

def fmt_int(value):
    num = clean_num(value)
    return f"{int(round(num)):,}"

def fmt_float(value, decimals=1):
    num = clean_num(value)
    return f"{num:.{decimals}f}"

def calculate_rankings(excel_path):
    excel_path = Path(excel_path)
    if not excel_path.is_file():
        raise FileNotFoundError(f"فایل اکسل پیدا نشد: {excel_path}")

    df = pd.read_excel(excel_path)
    df.columns = [c.strip() for c in df.columns]

    if "نماد" in df.columns:
        df["نماد_clean"] = df["نماد"].astype(str).str.strip()
        df = df[df["نماد_clean"].str.startswith("ض")].copy()

    df["vol_clean"] = df["حجم معاملات"].apply(clean_num) if "حجم معاملات" in df.columns else 0
    df["oi_clean"] = df["موقعیت های باز"].apply(clean_num) if "موقعیت های باز" in df.columns else 0
    df["lev_clean"] = df["اهرم"].apply(clean_num) if "اهرم" in df.columns else 1
    df["val_clean"] = df["ارزش معاملات"].apply(clean_num) if "ارزش معاملات" in df.columns else 0

    # فیلتر ۱: دارای حجم معامله
    active_df = df[df["vol_clean"] > 0].copy()
    if not active_df.empty:
        df = active_df

    # فیلتر ۲: اهرم حداقل ۳
    df = df[df["lev_clean"] >= 3.0].copy()

    if df.empty:
        print("هیچ نمادی با اهرم ۳ و بالاتر یافت نشد.")
        return

    # رتبه‌بندی بر اساس فرمول وزن‌دهی
    df["vol_rank"] = df["vol_clean"].rank(pct=True) * 100
    df["val_rank"] = df["val_clean"].rank(pct=True) * 100
    df["lev_score"] = np.where(
        df["lev_clean"].between(3, 10),
        100,
        np.maximum(0, 100 - np.abs(df["lev_clean"] - 6) * 10)
    )

    df["امتیاز_نهایی"] = (
        df["vol_rank"] * 0.45 +
        df["val_rank"] * 0.35 +
        df["lev_score"] * 0.20
    ).round(1)

    top_df = df.sort_values(by="امتیاز_نهایی", ascending=False).head(10).reset_index(drop=True)

    headers = [
        "رتبه", "نماد", "اعمال", "آخرین", "سر به سری",
        "پایه", "اهرم", "فاصله سر به سری", "سررسید", "باقی مانده روز", "امتیاز"
    ]

    lines = []
    lines.append("📊 **رتبه‌بندی برترین قراردادهای اختیار معامله (پروتکل V3)**\n")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for idx, row in top_df.iterrows():
        rank = str(idx + 1)
        symbol = str(row.get("نماد", "-")).strip()
        strike = fmt_int(row.get("قیمت اعمال", 0))
        last_px = fmt_int(row.get("آخرین قیمت", 0))
        breakeven_val = clean_num(row.get("سر به سر", 0))
        breakeven = fmt_int(breakeven_val)
        base_px_val = clean_num(row.get("قیمت سهم پایه", 0))
        base_px = fmt_int(base_px_val)
        leverage = fmt_float(row.get("اهرم", 0), 1)

        # محاسبه مستقیم درصد فاصله سر به سری: ((سر به سر - قیمت پایه) / قیمت پایه) * 100
        if base_px_val > 0:
            be_dist_pct = ((breakeven_val - base_px_val) / base_px_val) * 100.0
            be_dist = f"{be_dist_pct:+.1f}%"
        else:
            be_dist = "0.0%"

        due_date = str(row.get("تاریخ سررسید", "-")).strip()
        days_left = fmt_int(row.get("روزهای تقویمی", row.get("روزهای معاملاتی", 0)))
        score = fmt_float(row.get("امتیاز_نهایی", 0), 1)

        row_str = f"| {rank} | {symbol} | {strike} | {last_px} | {breakeven} | {base_px} | {leverage} | {be_dist} | {due_date} | {days_left} | {score} |"
        lines.append(row_str)

    report_text = "\n".join(lines).strip() + "\n"
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    print(f"گزارش نهایی اصلاح‌شده با موفقیت تولید شد:\n")
    print(report_text)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("استفاده: python3 generate_report.py FILE.xlsx", file=sys.stderr)
        sys.exit(2)
    calculate_rankings(sys.argv[1])



# --- بخش ارسال خودکار به بله اضافه شد ---
bale_token = os.environ.get("BALE_BOT_TOKEN")
bale_chat_id = os.environ.get("BALE_CHAT_ID")

if bale_token and bale_chat_id:
    try:
        import requests
        url = f"https://tapi.bale.ai/bot{bale_token}/sendMessage"
        payload = {
            "chat_id": bale_chat_id,
            "text": final_report_md
        }
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200 and resp.json().get("ok"):
            print("✅ گزارش با موفقیت به بله ارسال شد.")
        else:
            print(f"❌ خطا در تحویل به بله: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ خطای شبکه بله: {e}")

