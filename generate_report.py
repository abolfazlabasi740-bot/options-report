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
            if p == clean_c or (len(p) > 3 and p in clean_c):
                return c
    return None

c_symbol = get_col(['نماد', 'نماد قرارداد', 'نماد اختیار'])
c_strike = get_col(['قیمت اعمال', 'اعمال'])
c_due = get_col(['سررسید', 'تاریخ سررسید', 'مانده تا سررسید', 'روز تا سررسید'])
c_lev = get_col(['اهرم موثر', 'اهرم', 'اهرم ساده'])
c_val = get_col(['ارزش معاملات (میلیارد)', 'ارزش معاملات', 'ارزش معامله', 'ارزش'])
c_itm = get_col(['وضعیت', 'وضعیت سود', 'وضعیت در سود بودن'])
c_delta = get_col(['دلتا', 'Delta'])
c_prem = get_col(['قیمت پایانی اختیار', 'قیمت پایانی', 'پایانی اختیار', 'آخرین معامله اختیار', 'آخرین معامله'])

# تبدیل مقادیر عددی برای ارزش معاملات
if c_val:
    df['clean_val'] = pd.to_numeric(df[c_val].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)
    # اگر نمادهای خرید با 'ض' شروع می‌شوند فیلتر کنیم
    if c_symbol:
        df_call = df[df[c_symbol].astype(str).str.strip().str.startswith('ض')].copy()
        if df_call.empty:
            df_call = df.copy()
    else:
        df_call = df.copy()
    
    df_top = df_call.sort_values(by='clean_val', ascending=False).head(10).copy()
else:
    df_top = df.head(10).copy()

rows = []
rank = 1

for idx, row in df_top.iterrows():
    symbol = str(row[c_symbol]).strip() if c_symbol and pd.notna(row[c_symbol]) else '---'
    
    # قیمت اعمال
    strike_raw = row[c_strike] if c_strike and pd.notna(row[c_strike]) else '-'
    try:
        strike = f"{int(float(str(strike_raw).replace(',', ''))):,}"
    except:
        strike = str(strike_raw)

    due = str(row[c_due]).strip() if c_due and pd.notna(row[c_due]) else '-'
    
    # اهرم
    lev_raw = row[c_lev] if c_lev and pd.notna(row[c_lev]) else '-'
    try:
        lev = f"{float(str(lev_raw).replace(',', '')):.1f}"
    except:
        lev = str(lev_raw)

    # ارزش معاملات
    val_raw = row.get('clean_val', 0)
    if val_raw >= 1e9:
        val_str = f"{val_raw/1e9:.2f}B"
    elif val_raw >= 1e6:
        val_str = f"{val_raw/1e6:.1f}M"
    elif val_raw > 0:
        val_str = f"{val_raw:,.0f}"
    else:
        val_str = "0"

    itm = str(row[c_itm]).strip() if c_itm and pd.notna(row[c_itm]) else '-'
    
    # دلتا
    delta_raw = row[c_delta] if c_delta and pd.notna(row[c_delta]) else '-'
    try:
        delta = f"{float(str(delta_raw).replace(',', '')):.2f}"
    except:
        delta = str(delta_raw)

    # قیمت پایانی (پریمیوم)
    prem_raw = row[c_prem] if c_prem and pd.notna(row[c_prem]) else '-'
    try:
        prem = f"{int(float(str(prem_raw).replace(',', ''))):,}"
    except:
        prem = str(prem_raw)

    score = f"{100 - (rank-1)*5}"

    r_text = (
        f"{rank}. 🔹 نماد: {symbol}\n"
        f"   قیمت اعمال: {strike} | سررسید: {due}\n"
        f"   پایانی: {prem} | اهرم: {lev} | ارزش: {val_str}\n"
        f"   وضعیت: {itm} | دلتا: {delta} | امتیاز: {score}"
    )
    rows.append(r_text)
    rank += 1

header = "📊 گزارش رتبه‌بندی اختیار معامله (Optionschool)\n«« موتور رتبه‌بندی قراردادهای برتر خرید »»\n" + ("="*35)
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
