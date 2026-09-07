#!/usr/bin/env python3
"""Render the governed eleven-column report as Bale-friendly cards and send it."""
from __future__ import annotations
import argparse, os
from datetime import datetime
from pathlib import Path
import requests

def num(v, decimals=0):
    try:
        x=float(str(v).replace(',','').replace('%','').strip())
        return f'{x:,.{decimals}f}'
    except Exception:
        return str(v).strip() or '—'

def cards(text):
    rows=[]
    for line in text.splitlines():
        if not line.startswith('|') or line.startswith('|---'): continue
        c=[x.strip() for x in line.strip('|').split('|')]
        if len(c)==11 and c[0].isdigit(): rows.append(c)
    if not rows: raise RuntimeError('11-column ranking table not found')
    out=['📊 گزارش امتیازدهی V4.1 | کارت‌های برتر','━━━━━━━━━━━━━━━━━━━━']
    for rank,symbol,strike,last,be,base,lev,distance,expiry,days,score in rows:
        try: cost=num(float(strike.replace(',',''))+float(last.replace(',','')))
        except Exception: cost='—'
        out += [f'🏷️ نماد: {symbol} (رتبه {rank})','📦 تسویه فیزیکی',f'📅 تاریخ اعمال/سررسید: {expiry}',f'⏳ {days} روز مانده','-------------',f'💰 پرمیوم (آخرین): {num(last)}',f'💲 قیمت اعمال: {num(strike)}',f'💲 قیمت سهم پایه: {num(base)}',f'💲 قیمت تمام‌شده: {cost}',f'🔃 فاصله تا سر‌به‌سر: {distance}', '-------------',f'📊 سر‌به‌سر: {num(be)}',f'⚖️ اهرم: {num(lev,2)}',f'🏆 امتیاز V4.1: {num(score,2)}','🧾 ۱۱ ستون رسمی: رتبه، نماد، اعمال، آخرین، سر‌به‌سر، پایه، اهرم، فاصله، سررسید، روز، امتیاز','━━━━━━━━━━━━━━━━━━━━','']
    out.append('⏱ زمان ارسال: '+datetime.now().astimezone().strftime('%Y/%m/%d, %H:%M:%S'))
    return '\n'.join(out)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--report',required=True); p.add_argument('--audit',action='store_true'); p.add_argument('--token',default=os.getenv('BALE_BOT_TOKEN','')); p.add_argument('--chat-id',default=os.getenv('BALE_CHAT_ID','')); p.add_argument('--api-base',default=os.getenv('BALE_API_BASE','https://tapi.bale.ai')); a=p.parse_args()
    card_text=cards(Path(a.report).read_text(encoding='utf-8'))
    if a.audit:
        print(f'Card audit passed: {card_text.count("🏷️ نماد:")} cards, 11 columns preserved')
        return
    payload={'chat_id':a.chat_id,'text':card_text,'disable_web_page_preview':True}
    r=requests.post(f"{a.api_base.rstrip('/')}/bot{a.token}/sendMessage",json=payload,timeout=60); r.raise_for_status(); data=r.json()
    if not data.get('ok'): raise RuntimeError(data)
    print('Bale card report sent successfully')
if __name__=='__main__': main()
