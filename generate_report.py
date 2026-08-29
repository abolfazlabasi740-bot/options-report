import os
import sys
import requests
import pandas as pd
from datetime import datetime

EXCEL_URL = "https://s3.optionschool24.com/export/excel?type=1"
LOCAL_FILE = "options_data.xlsx"

def download_data():
    print("⏳ در حال دانلود داده‌های زنده از Optionschool...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    resp = requests.get(EXCEL_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    with open(LOCAL_FILE, "wb") as f:
        f.write(resp.content)
    print("✅ فایل با موفقیت دانلود و ذخیره شد.")

def send_to_bale(message_text):
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("⚠️ توکن یا Chat ID در متغیرهای محیطی یافت نشد. ارسال به بله انجام نشد.")
        return

    url = f"https://tapi.bale.ai/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text
    }

    try:
        res = requests.post(url, json=payload, timeout=20)
        res_json = res.json()
        if res_json.get("ok"):
            print("🚀 گزارش با موفقیت به بله ارسال شد.")
        else:
            print(f"❌ خطا از سمت سرور بله: {res_json}")
    except Exception as e:
        print(f"❌ خطای شبکه در ارسال به بله: {e}")

def process_and_report():
    download_data()
    
    # بارگذاری فایل اکسل
    df = pd.read_excel(LOCAL_FILE)
    total_records = len(df)
    
    # استانداردسازی نام ستون‌ها
    df.columns = [str(c).strip() for c in df.columns]
    
    # مرتب‌سازی و انتخاب ۱۰ نماد برتر
    top_df = df.head(10)
    valid_count = len(top_df)

    now_str = datetime.now().strftime("%Y/%m/%d - %H:%M")

    header = (
        f"📊 گزارش رتبه‌بندی اختیار معامله (پروتکل V3)\n"
        f"🕒 زمان پردازش: {now_str}\n"
        f"📋 داده‌ها: کل {total_records} ردیف | برتر {valid_count} موقعیت\n"
        f"-----------------------------------------\n"
    )

    lines = []
    lines.append("ردیف | نماد | اهرم | سررسید | وضعیت")
    lines.append("-----------------------------------------")

    for idx, (_, row) in enumerate(top_df.iterrows()):
        symbol = str(row.get("نماد", row.get("symbol", "-")))
        leverage = str(row.get("اهرم", row.get("leverage", "-")))
        days = str(row.get("روز تا سررسید", row.get("days_to_maturity", "-")))
        status = str(row.get("وضعیت", "-"))
        
        lines.append(f"{idx+1} | {symbol} | {leverage} | {days} روز | {status}")

    footer = "\n-----------------------------------------\nمنبع: Optionschool24"
    
    full_report = header + "\n".join(lines) + footer
    print("\n" + full_report + "\n")

    # ارسال به بله
    send_to_bale(full_report)

if __name__ == "__main__":
    process_and_report()
