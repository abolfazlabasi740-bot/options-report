from pathlib import Path
import requests
import json

def load_env(path):
    env = {}
    env_file = Path(path)
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip().strip('"').strip("'")
    return env

env = load_env("/data/data/com.termux/files/home/options_report/.env")
TOKEN = env.get("BALE_BOT_TOKEN")
CHAT_ID = env.get("BALE_CHAT_ID")
report_path = Path("/data/data/com.termux/files/home/options_report/output_options_report.md")

if not TOKEN or not CHAT_ID:
    print("❌ خطا: مقادیر BALE_BOT_TOKEN یا BALE_CHAT_ID در فایل .env یافت نشد.")
    print(f"مقادیر خوانده شده: TOKEN={TOKEN}, CHAT_ID={CHAT_ID}")
    exit(1)

if not report_path.is_file():
    print("❌ خطا: فایل گزارش output_options_report.md وجود ندارد.")
    exit(1)

text = report_path.read_text(encoding="utf-8").strip()
if not text:
    print("⚠️ هشدار: فایل گزارش خالی است.")
    exit(0)

# تقسیم پیام به بخش‌های حداکثر ۴۰۰۰ کاراکتری جهت جلوگیری از خطای طول پیام در بله
MAX_LEN = 4000
parts = [text[i:i+MAX_LEN] for i in range(0, len(text), MAX_LEN)]

base_url = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"

for idx, part in enumerate(parts, 1):
    payload = {
        "chat_id": CHAT_ID,
        "text": part
    }
    try:
        response = requests.post(base_url, json=payload, timeout=20)
        res_data = response.json()
        if response.status_code == 200 and res_data.get("ok"):
            print(f"✅ تکه {idx} با موفقیت ارسال شد.")
        else:
            print(f"❌ خطا در ارسال تکه {idx}: کد وضعیت {response.status_code}")
            print(f"پاسخ سرور بله: {json.dumps(res_data, ensure_ascii=False)}")
    except Exception as e:
        print(f"❌ خطای شبکه یا ارتباطی در تکه {idx}: {e}")
