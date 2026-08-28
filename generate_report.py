import os
import sys
import datetime
import requests
import pandas as pd
import glob

DOWNLOAD_URL = "https://s3.optionschool24.com/export/excel?type=1"

def download_live_excel():
    print("در حال دریافت فایل اکسل زنده از Optionschool24...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Referer": "https://optionschool24.com/"
    }
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = f"optionschool24_live_{ts}.xlsx"
    try:
        resp = requests.get(DOWNLOAD_URL, headers=headers, timeout=30)
        print(f"وضعیت دریافت از سرور: {resp.status_code}, حجم: {len(resp.content)} بایت")
        if resp.status_code == 200 and len(resp.content) > 2000:
            with open(file_path, "wb") as f:
                f.write(resp.content)
            return file_path
    except Exception as e:
        print(f"خطا در دانلود فایل زنده: {e}")

    existing_files = glob.glob("optionschool24_all*.xlsx") + glob.glob("*.xlsx")
    if existing_files:
        print(f"استفاده از فایل پشتیبان: {existing_files[0]}")
        return existing_files[0]
    
    raise ValueError("هیچ فایل اکسلی برای تحلیل یافت نشد!")

def audit_and_clean_data(file_path):
    print(f"در حال خواندن فایل: {file_path}")
    df = pd.read_excel(file_path)
    total_rows = len(df)
    
    col_map = {}
    for col in df.columns:
        c_str = str(col).strip()
        if "اهرم" in c_str:
            col_map[col] = "اهرم"
        elif "نماد" in c_str:
            col_map[col] = "نماد"
        elif "اعمال" in c_str:
            col_map[col] = "قیمت اعمال"
        elif "پایه" in c_str:
            col_map[col] = "قیمت دارایی پایه"
        elif "آخرین" in c_str:
            col_map[col] = "آخرین"
        elif "روز" in c_str and "سررسید" in c_str:
            col_map[col] = "روز تا سررسید"
            
    df = df.rename(columns=col_map)
    
    if "اهرم" in df.columns:
        df["اهرم"] = pd.to_numeric(df["اهرم"], errors="coerce").fillna(0)
        df = df[df["اهرم"] >= 3.0]
    
    audit_info = {
        "file_name": os.path.basename(file_path),
        "total_rows": total_rows,
        "valid_rows": len(df),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return df, audit_info

def calculate_v3_scores(df):
    results = []
    for idx, row in df.iterrows():
        symbol = str(row.get("نماد", "")).strip()
        strike = float(row.get("قیمت اعمال", 0) or 0)
        last_price = float(row.get("آخرین", 0) or 0)
        base_price = float(row.get("قیمت دارایی پایه", 0) or 0)
        leverage = float(row.get("اهرم", 0) or 0)
        expiry = str(row.get("سررسید", "")).strip()
        rem_days = float(row.get("روز تا سررسید", 0) or 0)
        
        breakeven = strike + last_price
        dist_be = ((breakeven - base_price) / base_price * 100) if base_price > 0 else 0
        
        risk_penalty = max(0.0, (2.0 * leverage) - 1.0)
        base_score = 100.0 - (dist_be * 1.5) - (rem_days * 0.1) - risk_penalty
        final_score = max(0.0, min(100.0, base_score))
        
        results.append({
            "symbol": symbol,
            "strike": int(strike),
            "last_price": int(last_price),
            "breakeven": int(breakeven),
            "base_price": int(base_price),
            "leverage": round(leverage, 2),
            "dist_be": round(dist_be, 2),
            "expiry": expiry,
            "rem_days": int(rem_days),
            "score": round(final_score, 2)
        })
    
    ranked = sorted(results, key=lambda x: x["score"], reverse=True)
    return ranked[:10]

def build_report_text(top_list, audit):
    text = "📊 گزارش رتبه‌بندی اختیار معامله (پروتکل V3)
"
    text += f"منبع: Optionschool24 | اهرم ≥ ۳
"
    text += f"حسابرسی داده: {audit['valid_rows']} معتبر از {audit['total_rows']} قرارداد
"
    text += f"زمان پردازش: {audit['timestamp']}

"
    text += "رتبه | نماد | سر‌به‌سر | پایه | اهرم | فاصله | سررسید(روز) | امتیاز
"
    text += "--------------------------------------------------
"
    
    for i, item in enumerate(top_list, 1):
        sign = '+' if item['dist_be'] >= 0 else ''
        text += f"{i}. {item['symbol']} | {item['breakeven']:,} | {item['base_price']:,} | {item['leverage']}x | {sign}{item['dist_be']}% | {item['rem_days']}ر | {item['score']}
"
    
    return text

def send_to_bale(text):
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()
    print(f"وضعیت کلیدها -> Token Present: {bool(token)}, ChatID Present: {bool(chat_id)}")
    
    if not token or not chat_id:
        print("خطا: توکن یا Chat ID در گیت‌هاب تعریف نشده است!")
        return
        
    url = f"https://tapi.bale.ai/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(url, json=payload, timeout=20)
        print(f"پاسخ بله -> کد وضعیت: {resp.status_code} | متن: {resp.text}")
    except Exception as e:
        print(f"خطا در ارسال به بله: {e}")

def main():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        file_path = sys.argv[1]
    else:
        file_path = download_live_excel()
        
    df, audit = audit_and_clean_data(file_path)
    top_list = calculate_v3_scores(df)
    report_text = build_report_text(top_list, audit)
    print("
--- پیش‌نمایش گزارش ---
")
    print(report_text)
    
    send_to_bale(report_text)

if __name__ == "__main__":
    main()
