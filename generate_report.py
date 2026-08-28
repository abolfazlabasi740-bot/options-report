import sys, os, pandas as pd, requests

if len(sys.argv) < 2:
    print('No file provided')
    sys.exit(1)

file_path = sys.argv[1]
print(f'Reading: {file_path}')

df = pd.read_excel(file_path)

def get_col(patterns):
    for p in patterns:
        for c in df.columns:
            clean_c = str(c).strip()
            if p == clean_c:
                return c
    for p in patterns:
        for c in df.columns:
            clean_c = str(c).strip()
            if p in clean_c:
                return c
    return None

c_symbol = get_col(['نماد'])
c_strike = get_col(['قیمت اعمال'])
c_due = get_col(['تاریخ سررسید', 'سررسید'])
c_prem = get_col(['قیمت پایانی', 'آخرین قیمت'])
c_lev = get_col(['اهرم'])
c_val = get_col(['ارزش معاملات'])
c_itm = get_col(['وضعیت'])
c_delta = get_col(['دلتا'])

# فیلتر قراردادهای خرید (شروع با ض)
if c_symbol:
    df = df[df[c_symbol].astype(str).str.strip().str.startswith('ض')].copy()

# تمیزسازی و عددی کردن اهرم
if c_lev:
    df['clean_lev'] = pd.to_numeric(df[c_lev].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    # فیلتر: اهرم کوچکتر از ۳ نباشد (Leverage >= 3)
    df = df[df['clean_lev'] >= 3.0].copy()

# تمیزسازی ارزش معاملات
if c_val:
    df['clean_val'] = pd.to_numeric(df[c_val].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    df = df.sort_values(by='clean_val', ascending=False)

df_top = df.head(10).copy()

rows = []
rank = 1

for idx, row in df_top.iterrows():
    symbol = str(row[c_symbol]).strip() if c_symbol and pd.notna(row[c_symbol]) else '---'
    
    # قیمت اعمال
    try:
        strike_val = int(float(str(row[c_strike]).replace(',', '').strip()))
        strike = f"{strike_val:,}"
    except:
        strike = str(row[c_strike]) if c_strike else '-'

    due = str(row[c_due]).strip() if c_due and pd.notna(row[c_due]) else '-'
    
    # قیمت پایانی
    try:
        prem_val = int(float(str(row[c_prem]).replace(',', '').strip()))
        prem = f"{prem_val:,}"
    except:
        prem = str(row[c_prem]) if c_prem else '-'

    # اهرم
    lev_val = row.get('clean_lev', 0.0)
    lev = f"{lev_val:.1f}"

    # ارزش معاملات
    val_val = row.get('clean_val', 0.0)
    if val_val >= 1e9:
        val_str = f"{val_val/1e9:.2f}B"
    elif val_val >= 1e6:
        val_str = f"{val_val/1e6:.1f}M"
    elif val_val > 0:
        val_str = f"{val_val:,.0f}"
    else:
        val_str = "0"

    itm = str(row[c_itm]).strip() if c_itm and pd.notna(row[c_itm]) else '-'
    
    # دلتا
    try:
        delta_val = float(str(row[c_delta]).replace(',', '').strip())
        delta = f"{delta_val:.2f}"
    except:
        delta = str(row[c_delta]) if c_delta else '-'

    score = f"{100 - (rank-1)*5}"

    r_text = (
        f"{rank}. 🔹 نماد: {symbol}\n"
        f"   قیمت اعمال: {strike} | سررسید: {due}\n"
        f"   پایانی: {prem} | اهرم: {lev} | ارزش: {val_str}\n"
        f"   وضعیت: {itm} | دلتا: {delta} | امتیاز: {score}"
    )
    rows.append(r_text)
    rank += 1

header = "📊 گزارش رتبه‌بندی اختیار معامله (Optionschool)\n«« موتور رتبه‌بندی قراردادهای برتر خرید (اهرم ۳+) »»\n" + ("="*35)
final_msg = header + "\n\n" + "\n\n".join(rows)

print('--- پیش‌نمایش گزارش ---')
print(final_msg)

bot_token = os.environ.get('BALE_BOT_TOKEN')
chat_id = os.environ.get('BALE_CHAT_ID')

if bot_token and chat_id:
    url = f'https://tapi.bale.ai/bot{bot_token}/sendMessage'
    res = requests.post(url, json={'chat_id': chat_id, 'text': final_msg}, timeout=30)
    print(f'Bale API: {res.status_code} - {res.text}')
else:
    print('Warning: Missing Bale credentials')
