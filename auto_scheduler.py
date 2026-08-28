#!/usr/bin/env python3
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
RUN_SCRIPT = ROOT / "run_and_send.sh"
INTERVAL_SECONDS = 1800  # هر ۳۰ دقیقه

def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line, flush=True)

def run_job():
    log("🔄 شروع چرخه دریافت و پردازش داده‌ها...")
    if not RUN_SCRIPT.is_file():
        log(f"❌ فایل اجرایی پیدا نشد: {RUN_SCRIPT}")
        return
    try:
        res = subprocess.run(
            ["bash", str(RUN_SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300
        )
        if res.returncode == 0:
            log("✅ چرخه با موفقیت کامل شد.")
        else:
            log(f"⚠️ چرخه با خطا مواجه شد (کد {res.returncode}):\n{res.stdout}")
    except subprocess.TimeoutExpired:
        log("⏱ خطای تایم‌اوت: پردازش بیش از ۵ دقیقه طول کشید.")
    except Exception as e:
        log(f"❌ خطای غیرمنتظره: {e}")

def main():
    log("🚀 زمان‌بند خودکار Optionschool با موفقیت فعال شد.")
    # اجرای اول بلافاصله پس از استارت
    run_job()
    
    while True:
        try:
            log(f"⏳ خواب به مدت ۳۰ دقیقه تا چرخه بعدی...")
            time.sleep(INTERVAL_SECONDS)
            run_job()
        except KeyboardInterrupt:
            log("🛑 زمان‌بند توسط کاربر متوقف شد.")
            break
        except Exception as e:
            log(f"⚠️ خطای حلقه اصلی: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
