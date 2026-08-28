import sys, os, pandas as pd, requests

if len(sys.argv) < 2:
    print('No file provided')
    sys.exit(1)

file_path = sys.argv[1]
print(f'Reading: {file_path}')

df = pd.read_excel(file_path)

def find_col(possible_names):
    for c in df.columns:
        clean_c = str(c).strip()
        for p in possible_names:
            if p in clean_c:
                return c
    return None

c_symbol = find_col(['نماد', 'نماد قرارداد', 'اختیار', 'Symbol'])
c_strike = find_col(['قیمت اعمال', 'اعمال', 'Strike'])
c_due = find_col(['سررسید', 'تاریخ سررسید', 'Due', 'مانده تا سررسید', 'روز تا سررسید'])
c_lev = find_col(['اهرم', 'اهرم موثر', 'Leverage'])
c_val = find_col(['ارزش معاملات', 'ارزش معامله', 'ارزش', 'Value', 'TradeValue'])
c_itm = find_col(['وضعیت سود', 'وضعیت', 'Moneyness', 'در سود'])
c_delta = find_col(['دلتا', 'Delta'])
c_prem = find_col(['قیمت پایانی', 'پایانی', 'آخرین معامله', 'قیمت'])
c_open_pos = find_col(['موقعیت باز', 'موقعیت‌های باز', 'Open Interest', 'OpenInterest'])
c_vol = find_col(['حجم', 'حجم معاملات', 'Volume'])

if c_val:
    df[c_val] = pd.to_numeric(df[c_val].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df_top = df.sort_values(by=c_val, ascending=False).head(10).copy()
else:
    df_top = df.head(10).copy()

rows = []
rank = 1

for idx, row in df_top.iterrows():
    symbol = str(row[c_symbol]) if c_symbol and pd.notna(row[c_symbol]) else '---'
    strike = f"{int(row[c_strike]):,}" if c_strike and pd.notna(row[c_strike]) and str(row[c_strike]).replace('.','',1).isdigit() else str(row.get(c_strike, '-'))
    due = str(row[c_due]) if c_due and pd.notna(row[c_due]) else '-'
    lev = f"{float(row[c_lev]):.1f}" if c_lev and pd.notna(row[c_lev]) and str(row[c_lev]).replace('.','',1).isdigit() else '-'
    
    val_num = row[c_val] if c_val and pd.notna(row[c_val]) else 0
    val_str = f"{float(val_num)/1e9:.2f}B" if float(val_num) >= 1e9 else f"{float(val_num)/1e6:.0f}M"
    
    itm = str(row[c_itm]) if c_itm and pd.notna(row[c_itm]) else '-'
    delta = f"{float(row[c_delta]):.2f}" if c_delta and pd.notna(row[c_delta]) and str(row[c_delta]).replace('.','',1).isdigit() else '-'
    prem = f"{int(row[c_prem]):,}" if c_prem and pd.notna(row[c_prem]) and str(row[c_prem]).replace('.','',1).isdigit() else '-'
    pos = str(row[c_open_pos]) if c_open_pos and pd.notna(row[c_open_pos]) else '-'
    vol = str(row[c_vol]) if c_vol and pd.notna(row[c_vol]) else '-'
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
