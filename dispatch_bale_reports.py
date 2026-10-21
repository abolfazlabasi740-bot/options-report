# -*- coding: utf-8 -*-
import os
import sys
import json
from pathlib import Path
import urllib.request
import urllib.parse

# خواندن تنظیمات بله از متغیرهای محیطی یا فایل کانفیگ
BALE_TOKEN = os.environ.get("BALE_BOT_TOKEN", "").strip()
BALE_CHAT_ID = os.environ.get("BALE_CHAT_ID", "").strip()

# تلاش برای خواندن کانفیگ در صورت وجود
config_path = Path("config/bale_config.json")
if config_path.exists() and (not BALE_TOKEN or not BALE_CHAT_ID):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            BALE_TOKEN = BALE_TOKEN or cfg.get("bot_token", "")
            BALE_CHAT_ID = BALE_CHAT_ID or cfg.get("chat_id", "")
    except Exception:
        pass

def send_bale_message(text: str) -> bool:
    if not BALE_TOKEN or not BALE_CHAT_ID:
        return False
    url = f"https://tapi.bale.ai/bot{BALE_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": BALE_CHAT_ID,
        "text": text
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"⚠️ خطا در ارسال پیام بله: {e}")
        return False

def build_reports():
    bundle_file = Path("output/reports/market_analytics_bundle.json")
    if not bundle_file.exists():
        print(f"❌ فایل تحلیلی {bundle_file} موجود نیست. ابتدا اسکریپت محاسبه را اجرا نمایید.")
        sys.exit(1)

    with open(bundle_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    shamsi_date = meta.get("shamsi_date", "")
    time_str = meta.get("time_str", "")

    reports = []

    # گزارش ۱: بیشترین رشد آخرین معامله
    lines = [
        f"📅 تاریخ: {shamsi_date} | ⏰ ساعت: {time_str}",
        "🚀 ۲۰ نماد با بیشترین رشد (بر مبنای آخرین معامله):",
        "────────────────────────"
    ]
    for idx, item in enumerate(data.get("top_pl_gainers", []), 1):
        lines.append(f"{idx:02d}. {item['symbol']} | آخرین: {int(item['pl']):,} ({item['pl_pct']:+.2f}%) | پایانی: {item['pc_pct']:+.2f}%")
    reports.append("\n".join(lines))

    # گزارش ۲: بیشترین رشد قیمت پایانی
    lines = [
        f"📅 تاریخ: {shamsi_date} | ⏰ ساعت: {time_str}",
        "📈 ۲۰ نماد با بیشترین رشد (بر مبنای قیمت پایانی):",
        "────────────────────────"
    ]
    for idx, item in enumerate(data.get("top_pc_gainers", []), 1):
        lines.append(f"{idx:02d}. {item['symbol']} | پایانی: {int(item['pc']):,} ({item['pc_pct']:+.2f}%) | آخرین: {item['pl_pct']:+.2f}%")
    reports.append("\n".join(lines))

    # گزارش ۳: بیشترین ارزش معاملات
    lines = [
        f"📅 تاریخ: {shamsi_date} | ⏰ ساعت: {time_str}",
        "💰 ۲۰ نماد با بیشترین ارزش معاملات (میلیارد تومان):",
        "────────────────────────"
    ]
    for idx, item in enumerate(data.get("top_turnover", []), 1):
        lines.append(f"{idx:02d}. {item['symbol']} | ارزش: {item['tval_b_toman']:,.2f} م.ت | پایانی: {item['pc_pct']:+.2f}%")
    reports.append("\n".join(lines))

    # گزارش ۴: بیشترین افت
    lines = [
        f"📅 تاریخ: {shamsi_date} | ⏰ ساعت: {time_str}",
        "🔻 ۲۰ نماد با بیشترین افت (بر مبنای آخرین معامله):",
        "────────────────────────"
    ]
    for idx, item in enumerate(data.get("top_pl_losers", []), 1):
        lines.append(f"{idx:02d}. {item['symbol']} | آخرین: {int(item['pl']):,} ({item['pl_pct']:+.2f}%) | پایانی: {item['pc_pct']:+.2f}%")
    reports.append("\n".join(lines))

    # استخراج اختصاصی وضعیت دشیری از بین کل نمادها جهت اطمینان خاطر
    dshiri_info = None
    all_symbols = data.get("top_pl_gainers", []) + data.get("top_pc_gainers", []) + data.get("top_turnover", []) + data.get("top_pl_losers", [])
    # بررسی مجدد فایل خام برای یافتن موقعیت دقیق دشیری در کل بازار
    from run_multi_reports_engine import parse_marketwatch
    # از باندل لود می‌کنیم
    print("=" * 50)
    print("📋 آماده‌سازی گزارش‌های ۴ گانه بله انجام شد.")
    
    can_send = bool(BALE_TOKEN and BALE_CHAT_ID)
    if can_send:
        print("📡 در حال ارسال گزارش‌ها به پیام‌رسان بله...")
        for i, rep in enumerate(reports, 1):
            success = send_bale_message(rep)
            status = "✅ ارسال شد" if success else "❌ خطا در ارسال"
            print(f"   - گزارش شماره {i}: {status}")
    else:
        print("ℹ️ شناسه بات بله (BALE_BOT_TOKEN / BALE_CHAT_ID) تنظیم نشده است.")
        print("📄 پیش‌نمایش گزارش اول (Top 20 رشد آخرین معامله):\n")
        print(reports[0])

if __name__ == "__main__":
    build_reports()
