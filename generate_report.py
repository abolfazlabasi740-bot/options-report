
import os
import requests
import pandas as pd
from datetime import datetime

EXCEL_URL = "https://s3.optionschool24.com/export/excel?type=1"
LOCAL_FILE = "options_data.xlsx"

HEADERS = {"User-Agent": "Mozilla/5.0"}

def download_data():
    print("⏳ در حال دانلود داده‌های زنده از Optionschool...")
    resp = requests.get(EXCEL_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    with open(LOCAL_FILE, "wb") as f:
        f.write(resp.content)
    print("✅ فایل با موفقیت دانلود شد.")

def pick(df, *names):
    """انتخاب اولین ستون موجود با نام‌های مختلف (پوشش تغییرات نام ستون‌ها)"""
    cols = {str(c).strip(): c for c in df.columns}
    for n in names:
        if n in cols:
            return cols[n]
    return None

def to_num(x):
    try:
        return float(str(x).replace(",", "").replace("٬", "").replace("٫", "."))
    except (ValueError, TypeError):
        return None

def fmt_th(x):
    """فرمت اعداد با جداکننده هزارگان و ممیز فارسی"""
    if x is None:
        return "-"
    s = f"{x:,.0f}" if x >= 100 else f"{x:.2f}"
    return s.replace(",", "٬").replace(".", "٫")

def days_to_maturity(date_str):
    """محاسبه ساده فاصله روز تا سررسید شمسی"""
    try:
        parts = str(date_str).split("/")
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        base = (y * 365) + (m * 30) + d
        now = datetime.now()
        now_j = (now.year + 621, now.month, now.day)
        now_base = (now_j[0] * 365) + (now_j[1] * 30) + now_j[2]
        return max(0, base - now_base)
    except (ValueError, IndexError, TypeError):
        return None

def send_to_bale(text):
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("⚠️ توکن یا Chat ID تنظیم نشده است.")
        return
    url = f"https://tapi.bale.ai/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        res = requests.post(url, json=payload, timeout=20)
        print(f"پاسخ بله: {res.text}")
    except Exception as e:
        print(f"❌ خطای ارسال: {e}")

def process_and_report():
    download_data()
    df = pd.read_excel(LOCAL_FILE)
    df.columns = [str(c).strip() for c in df.columns]

    # شناسایی ستون‌ها با نام‌های محتمل
    c_sym = pick(df, "نماد", "نماد قرارداد", "symbol")
    c_str = pick(df, "قیمت اعمال", "strike", "Strike Price")
    c_last = pick(df, "آخرین قیمت", "آخرین", "last price")
    c_be   = pick(df, "سر‌به‌سر", "سربه‌سر", "break even")
    c_und  = pick(df, "پایه", "دارایی پایه", "underlying")
    c_lev  = pick(df, "اهرم", "leverage")
    c_mat  = pick(df, "سررسید", "تاریخ سررسید", "maturity")
    c_score= pick(df, "امتیاز", "score")

    # فیلتر اهرم ≥ ۳
    df["_lev"] = df[c_lev].apply(to_num)
apply(to_num)
    df = df[df["_lev"] >= 3].copy()

    مشتق
    df["_be"] = df[c_be].apply(to_num) if c_be else None
    df["_und"] = df[c_und].apply(to_num) if c_und else None
    df["_dist"] = df.apply(
        lambda r: (r["_be"] - r["_und"]) / r["_und"] * 100
        if pd.notna(r["_be"]) and pd.notna(r["_und"]) and r["_und"] else None, axis=1)

   ["_und"] else None, axis=1)

    # امتیاز (اگر ست تقریبی V3 محاسبه شود)
    if c_score:
        df["_score"] = df[c_score].apply(to_num)
    else:
        df["_score"] = df.apply(
            lambda r: max(0, 100 - (2 * (r["_lev"] or 0) - 1) * 2
                          - abs(r["_dist"] or 0) * 1.5), axis=1)

    # مرتب‌سازی بر اساس امتیاز نهایی
    df = df.sort_values("_score", ascending=False).head(10)

    # ساخت پیام
    header = "📊 رتبه‌بندی برترین قراردادهای اختیار معامله\n\n"
    header += "پروتکل V3 (منبع: Optionschool24)\n\n"
    header += "فیلتر: اهرم حداقل ۳\n"
    header += "━━━━━━━━━━━━━━━━━━\n\n"

    cards = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        days = days_to_maturity(r[c_mat]) if c_mat else None
        dtxt = f" ({days} روز)" if days is not None else ""
        dist = r}{fmt_th(dist disttxt = f"{'+' if dist and dist > 0 else ''}{fmt_th(dist)}٪" if dist is not None else "-"
        card = (
            f"🔹 {i}. {r[c_sym]}\n"
            f"قیمت اعمال: {fmt_th(to_num(r[c_str]))} | آخرین: {fmt_th(to_num(r[c_last]))}\n"
            f"سر‌به‌سر: {fmt_th(r['_be'])} | پایه: {fmt_th(r['_und'])}\n"
            f"اهرم: {fmt_th(r['_lev'])} | فاصله سر‌به‌سر: {disttxt}\n"
            f"سررسید: {r[c_mat]}{dtxt}\n"
            f"امتیاز: {fmt_th(r['_score'])}\n"
        )
        cards.append(card)

    full_report = header + "━━━━━━━━━━━━━━ real━━━━━━━━━━\n\n".join(cards)
    print(full_report)
    send_to_bale(full_report)

if __name__ "__main__":
    process_and_report()

    
