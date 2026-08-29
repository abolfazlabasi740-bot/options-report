
# پیدا کردن پوشه پروژه و ورود به آن
cd ~/options-report 2>/dev/null || cd $(find ~ -maxdepth 2 -type d -name "options-report" | head -n 1)

# بازنویسی کامل فایل
cat << 'EOF' > generate_report.py
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
    print("✅ فایل با موفقیت دانلود شد.")

def send_to_bale(message_text):
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("⚠️ توکن یا Chat ID ست نشده است.")
        return

    url = f"https://tapi.bale.ai/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text
    }

    try:
        res = requests.post(url, json=payload, timeout=20)
        print(f"پاسخ بله: {res.text}")
    except Exception as e:
        print(f"❌ خطای ارسال: {e}")

def process_and_report():
    download_data()
    
    df = pd.read_excel(LOCAL_FILE)
    total_records = len(df)
    df.columns = [str(c).strip() for c in df.columns]
    
    top_df = df.head(10)
    now_str = datetime.now().strftime("%Y/%m/%d - %H:%M")

    header = f"📊 گزارش رتبه‌بندی اختیار معامله (پروتکل V3)\n🕒 زمان: {now_str}\n📋 کل رکوردها: {total_records}\n-----------------------------------------\n"
    
    lines = ["ردیف | نماد | اهرم | سررسید | وضعیت", "-----------------------------------------"]
    for idx, (_, row) in enumerate(top_df.iterrows()):
        symbol = str(row.get("نماد", row.get("symbol", "-")))
        leverage = str(row.get("اهرم", row.get("leverage", "-")))
        days = str(row.get("روز تا سررسید", row.get("days_to_maturity", "-")))
        status = str(row.get("وضعیت", "-"))
        lines.append(f"{idx+1} | {symbol} | {leverage} | {days} روز | {status}")

    full_report = header + "\n".join(lines) + "\n-----------------------------------------\nمنبع: Optionschool24"
    print(full_report)
    send_to_bale(full_report)

if __name__ == "__main__":
    process_and_report()
EOF

# بررسی سینتکس قبل از پوش
python3 -m py_compile generate_report.py && echo "✅ فایل پایتون بدون هیچ خطای سینتکسی تایید شد."

# کامیت و ارسال مستقیم به گیت‌هاب
git add generate_report.py
git commit -m "Update generate_report.py fixed strings"
git push origin main
