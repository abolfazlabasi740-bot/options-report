import os, sys, glob, requests
import pandas as pd

def get_latest_excel():
    files = glob.glob("optionschool24_all_*.xlsx")
    if not files:
        files = glob.glob("*.xlsx")
    if not files:
        return None
    return max(files, key=os.path.getmtime)

excel_file = sys.argv[1] if len(sys.argv) > 1 else get_latest_excel()

if not excel_file or not os.path.exists(excel_file):
    print("هیچ فایل اکسلی یافت نشد.")
    sys.exit(0)

# خواندن اکسل
df = pd.read_excel(excel_file)

# استانداردسازی نام ستون‌ها
col_map = {}
for c in df.columns:
    c_clean = str(c).strip()
    if "نماد" in c_clean and "پایه" not in c_clean:
        col_map["symbol"] = c
    elif "پایه" in c_clean:
        col_map["ua"] = c
    elif "اعمال" in c_clean:
        col_map["strike"] = c
    elif "سررسید" in c_clean or "مانده" in c_clean:
        col_map["days"] = c
    elif "اهرم" in c_clean:
        col_map["leverage"] = c
    elif "ارزش" in c_clean and "معاملات" in c_clean:
        col_map["val"] = c
    elif "موقعیت" in c_clean or "باز" in c_clean:
        col_map["oi"] = c
    elif "نوع" in c_clean:
        col_map["type"] = c
    elif "وضعیت" in c_clean:
        col_map["moneyness"] = c

# مرتب‌سازی بر اساس ارزش معاملات یا اهرم جهت استخراج برترین‌ها
sort_col = col_map.get("val") or col_map.get("leverage")
if sort_col and sort_col in df.columns:
    df[sort_col] = pd.to_numeric(df[sort_col], errors="coerce").fillna(0)
    top_df = df.sort_values(by=sort_col, ascending=False).head(10).copy()
else:
    top_df = df.head(10).copy()

# ساخت جدول ۱۱ ستونه
lines = [
    "📊 *گزارش تحلیلی برترین نمادهای Optionschool*",
    f"📁 مبنا: `{os.path.basename(excel_file)}`",
    "──────────────────────────",
    "رتبه | نماد | پایه | نوع | اعمال | سررسید | اهرم | ارزش(M) | سودمندی | موقعیت باز | امتیاز"
]

rank = 1
for _, r in top_df.iterrows():
    sym = str(r.get(col_map.get("symbol", ""), "-"))[:10]
    ua = str(r.get(col_map.get("ua", ""), "-"))[:6]
    otype = "خرید" if "خ" in str(r.get(col_map.get("type", ""), "")) else "فروش"
    strike = f"{float(r.get(col_map.get("strike", 0), 0)):,.0f}" if pd.notnull(r.get(col_map.get("strike", 0))) else "-"
    days = str(r.get(col_map.get("days", "-"), "-"))
    
    lev_val = r.get(col_map.get("leverage", 0), 0)
    lev = f"{float(lev_val):.1f}" if pd.notnull(lev_val) and str(lev_val).replace(".","").isdigit() else "-"
    
    val_raw = r.get(col_map.get("val", 0), 0)
    val_m = f"{float(val_raw)/1e6:,.0f}" if pd.notnull(val_raw) and str(val_raw).replace(".","").isdigit() else "-"
    
    m_state = str(r.get(col_map.get("moneyness", "-"), "-"))[:5]
    oi = f"{float(r.get(col_map.get("oi", 0), 0)):,.0f}" if pd.notnull(r.get(col_map.get("oi", 0))) else "-"
    score = f"{100 - (rank * 4)}" # رتبه/امتیاز ترتیبی

    lines.append(f"{rank} | {sym} | {ua} | {otype} | {strike} | {days} | {lev} | {val_m} | {m_state} | {oi} | {score}")
    rank += 1

msg = "\n".join(lines)

bot_token = os.environ.get("BALE_BOT_TOKEN")
chat_id = os.environ.get("BALE_CHAT_ID")

if bot_token and chat_id:
    url = f"https://tapi.bale.ai/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": msg}
    resp = requests.post(url, json=payload, timeout=20)
    print("ارسال به بله:", resp.status_code)
else:
    print("توکن یا شناسه چت بله تنظیم نشده است.")
