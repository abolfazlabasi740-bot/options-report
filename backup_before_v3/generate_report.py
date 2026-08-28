import os
import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

EXCEL_PATH = "/data/data/com.termux/files/home/options_report/optionschool24_all_1783670594967.xlsx"

BALA_BOT_TOKEN = os.getenv("BALA_BOT_TOKEN")
BALA_CHAT_ID = os.getenv("BALA_CHAT_ID")

def send_to_bale(text: str) -> bool:
    if not BALA_BOT_TOKEN or not BALA_CHAT_ID:
        print("❌ BALA_BOT_TOKEN یا BALA_CHAT_ID خالی است.")
        return False

    url = f"https://tapi.bale.ai/bot{BALA_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": BALA_CHAT_ID, "text": text})
        print(f"SendMessage status: {r.status_code}")
        print(f"SendMessage response: {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"Connection Error: {e}")
        return False

def to_number(series):
    """تبدیل امن مقادیر به عدد؛ هر مقدار غیرعددی تبدیل به NaN می‌شود."""
    return pd.to_numeric(series, errors="coerce")

def calculate_rankings():
    try:
        df = pd.read_excel(EXCEL_PATH)

        # تبدیل امن ستون‌های عددی
        if "حجم معاملات" in df.columns:
            df["حجم معاملات"] = to_number(df["حجم معاملات"])
        if "موقعیت های باز" in df.columns:
            df["موقعیت های باز"] = to_number(df["موقعیت های باز"])
        if "اختلاف تا بلک شولز" in df.columns:
            df["اختلاف تا بلک شولز"] = to_number(df["اختلاف تا بلک شولز"])
        if "اهرم" in df.columns:
            df["اهرم"] = to_number(df["اهرم"])

        # فقط نمادهای قابل معامله (حجم > 0 و نامعتبر نباشد)
        df = df[df["حجم معاملats"].notna()] if False else df
        df = df[df["حجم معاملات"].notna() & (df["حجم معاملات"] > 0)].copy()

        score_columns = []

        if "حجم معاملات" in df.columns:
            df["حجم_امتیاز"] = df["حجم معاملات"].rank(pct=True) * 100
            score_columns.append("حجم_امتیاز")

        if "موقعیت های باز" in df.columns:
            df["موقعیت_امتیاز"] = df["موقعیت های باز"].rank(pct=True) * 100
            score_columns.append("موقعیت_امتیاز")

        if "اختلاف تا بلک شولز" in df.columns:
            df["بلکشولز_امتیاز"] = (1 - df["اختلاف تا بلک شولز"].rank(pct=True)) * 100
            score_columns.append("بلکشولز_امتیاز")

        if "اهرم" in df.columns:
            df["اهرم_امتیاز"] = df["اهرم"].rank(pct=True) * 100
            score_columns.append("اهرم_امتیاز")

        if not score_columns:
            print("❌ هیچ ستون قابل امتیازدهی پیدا نشد.")
            return

        df["امتیاز نهایی"] = df[score_columns].mean(axis=1)

        top_10 = df.sort_values(by="امتیاز نهایی", ascending=False).head(10)

        report_lines = []
        report_lines.append("📊 رتبه‌بندی برترین قراردادهای اختیار معامله")
        report_lines.append("مطابق پروتکل V3 - داروسازی دکتر عبیدی")
        report_lines.append("")
        report_lines.append("نماد | امتیاز | حجم معاملات | موقعیت‌های باز | اهرم")
        report_lines.append("-----------------------------------------------------")

        for _, row in top_10.iterrows():
            symbol = row.get("نماد", "")
            score = row.get("امتیاز نهایی", 0)
            vol = row.get("حجم معاملات", 0)
            oi = row.get("موقعیت های باز", 0)
            lev = row.get("اهرم", 0)

            def fmt(x):
                if pd.isna(x):
                    return "0"
                return f"{int(x):,}"

            def fmt_lev(x):
                if pd.isna(x):
                    return "0"
                return f"{x:.2f}"

            line = f"{symbol} | {score:.1f} | حجم: {fmt(vol)} | موقعیت باز: {fmt(oi)} | اهرم: {fmt_lev(lev)}"
            report_lines.append(line)

        report_text = "\n".join(report_lines)

        print(report_text)
        if send_to_bale(report_text):
            print("✅ گزارش با موفقیت به بله ارسال شد.")
        else:
            print("❌ خطا در ارسال گزارش به بله.")

    except Exception as e:
        print(f"❌ خطای سیستمی: {e}")

if __name__ == "__main__":
    calculate_rankings()
