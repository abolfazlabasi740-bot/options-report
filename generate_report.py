# -*- coding: utf-8 -*-
import os, sys, glob, requests
import pandas as pd
import numpy as np

def find_excel():
    f = glob.glob('optionschool24_all_*.xlsx') or glob.glob('*.xlsx')
    return max(f, key=os.path.getmtime) if f else None

excel_path = sys.argv[1] if len(sys.argv) > 1 else find_excel()
if not excel_path or not os.path.exists(excel_path):
    print('ERROR: No Excel file found.')
    sys.exit(0)

print(f'Processing file: {excel_path}')
df = pd.read_excel(excel_path)

def col(name_part):
    for c in df.columns:
        if name_part.replace(' ', '') in str(c).replace(' ', '').replace('‌', ''):
            return c
    return None

c_sym = col('نماد')
c_strike = col('قیمتاعمال')
c_ua = col('قیمتسهمپایه') or col('سهمپایه')
c_days = col('روزهایتقویمی') or col('سررسید')
c_price = col('آخرینقیمت') or col('قیمتپایانی')
c_val = col('ارزشمعاملات')
c_lev = col('اهرم')
c_state = col('وضعیت')
c_delta = col('دلتا')

# فیلتر و مرتب سازی بر اساس ارزش معاملات
if c_val and c_val in df.columns:
    df[c_val] = pd.to_numeric(df[c_val], errors='coerce').fillna(0)
    top = df.sort_values(by=c_val, ascending=False).head(10).copy()
else:
    top = df.head(10).copy()

# ساخت جدول گزارش ۱۱ ستونه
header = '📊 گزارش رتبه‌بندی اختیار معامله (Optionschool)
'
header += f'📁 منبع داده: {os.path.basename(excel_path)}
'
header += '═' * 32 + '
'
header += 'ردیف | نماد | اعمال | سهم پایه | سررسید | قیمت | ارزش(M) | اهرم | وضعیت | دلتا | امتیاز
'
header += '─' * 32

rows = []
rank = 1
for _, r in top.iterrows():
    sym = str(r.get(c_sym, '-'))[:10]
    strike = f"{float(r.get(c_strike, 0)):,.0f}" if pd.notnull(r.get(c_strike)) and str(r.get(c_strike)).replace('.','').isdigit() else '-'
    ua = f"{float(r.get(c_ua, 0)):,.0f}" if pd.notnull(r.get(c_ua)) and str(r.get(c_ua)).replace('.','').isdigit() else '-'
    days = str(int(r.get(c_days, 0))) if pd.notnull(r.get(c_days)) and str(r.get(c_days)).replace('.','').isdigit() else '-'
    price = f"{float(r.get(c_price, 0)):,.0f}" if pd.notnull(r.get(c_price)) and str(r.get(c_price)).replace('.','').isdigit() else '-'
    
    val_raw = r.get(c_val, 0)
    val_m = f"{float(val_raw)/1e6:,.0f}" if pd.notnull(val_raw) and str(val_raw).replace('.','').isdigit() else '-'
    
    lev_raw = r.get(c_lev, 0)
    lev = f"{float(lev_raw):.1f}" if pd.notnull(lev_raw) and str(lev_raw).replace('.','').isdigit() else '-'
    
    state = str(r.get(c_state, '-'))[:5]
    
    delta_raw = r.get(c_delta, 0)
    delta = f"{float(delta_raw):.2f}" if pd.notnull(delta_raw) and str(delta_raw).replace('.','').replace('-','').isdigit() else '-'
    
    score = str(100 - (rank * 5))
    
    line = f'{rank} | {sym} | {strike} | {ua} | {days} | {price} | {val_m} | {lev} | {state} | {delta} | {score}'
    rows.append(line)
    rank += 1

final_msg = header + '
' + '
'.join(rows)
print(final_msg)

bot_token = os.environ.get('BALE_BOT_TOKEN')
chat_id = os.environ.get('BALE_CHAT_ID')

if bot_token and chat_id:
    url = f'https://tapi.bale.ai/bot{bot_token}/sendMessage'
    res = requests.post(url, json={'chat_id': chat_id, 'text': final_msg}, timeout=30)
    print(f'Bale API Response: {res.status_code} - {res.text}')
else:
    print('Error: Missing BALE_BOT_TOKEN or BALE_CHAT_ID')
