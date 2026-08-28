import os, sys, requests
import pandas as pd

def send_to_bale(text):
    token = os.environ.get("BALE_BOT_TOKEN")
    chat_id = os.environ.get("BALE_CHAT_ID")
    if not token or not chat_id:
        print("[Warn] BALE credentials not found in env.")
        return
    try:
        url = f"https://tapi.bale.ai/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=20)
        if resp.status_code == 200:
            print("[SUCCESS] Report sent to Bale successfully.")
        else:
            print(f"[Error] Bale API returned {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[Error] Failed to connect to Bale: {e}")

def main():
    if len(sys.argv) < 2:
        files = glob.glob("*.xlsx")
        if not files:
            print("No Excel files found.")
            return
        excel_file = sorted(files, key=os.path.getmtime, reverse=True)[0]
    else:
        excel_file = sys.argv[1]

    print(f"Reading: {excel_file}")
    df = pd.read_excel(excel_file)
    
    # پردازش و استخراج گزارش
    # ستون‌های نمونه برای ایجاد گزارش
    summary = f"📊 **گزارش خودکار Optionschool**\nفایل مبنا: {os.path.basename(excel_file)}\nتعداد ردیف‌ها: {len(df)}\n\n"
    
    # ساخت جدول رتبه‌بندی بر اساس ساختار موجود
    cols = df.columns.tolist()
    rank_col = [c for c in cols if 'رتبه' in str(c) or 'score' in str(c).lower()]
    symbol_col = [c for c in cols if 'نماد' in str(c) or 'symbol' in str(c).lower()]
    
    if rank_col and symbol_col:
        top10 = df.sort_values(by=rank_col[0], ascending=False).head(10)
        summary += "🔝 **۱۰ موقعیت برتر:**\n"
        for idx, row in top10.iterrows():
            summary += f"- {row[symbol_col[0]]}: امتیاز/رتبه {row[rank_col[0]]}\n"
    else:
        summary += f"اطلاعات کلی: ستون‌های شناسایی شده شامل {len(cols)} مورد می‌باشد.\nتحلیل با موفقیت انجام شد."

    print(summary)
    send_to_bale(summary)

if __name__ == '__main__':
    import glob
    main()
