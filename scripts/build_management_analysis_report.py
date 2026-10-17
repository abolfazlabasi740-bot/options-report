#!/usr/bin/env python3
"""Management Analysis Report builder — derived from rolling7 report.
Glass-button "تحلیل" payload. Master Project Book: no invented numbers;
missing data labeled explicitly."""
import json, hashlib
from pathlib import Path
from datetime import datetime

try:
    from jdatetime import date as jdate, datetime as jdatetime
    HAS_J = True
except ImportError:
    HAS_J = False

def jalali_now():
    now = datetime.now()
    if HAS_J:
        j = jdatetime.now()
        return f"{j.year}/{j.month:02d}/{j.day:02d} — ساعت {j.hour:02d}:{j.minute:02d}"
    return now.strftime('%Y-%m-%d %H:%M') + ' (میلادی — jdatetime نصب نیست)'

def jalali_from(gdate):
    """gdate: 'YYYYMMDD' or ISO — returns 'YYYY/MM/DD' jalali"""
    if not gdate: return 'داده موجود نیست'
    try:
        y, m, d = int(gdate[:4]), int(gdate[4:6]), int(gdate[6:8])
        if HAS_J:
            j = jdate.fromgregorian(year=y, month=m, day=d)
            return f"{j.year}/{j.month:02d}/{j.day:02d}"
    except Exception:
        pass
    return str(gdate) + ' (میلادی)'

BASE = Path(__file__).resolve().parents[1] / 'output' / 'base_share'
SRC = BASE / 'latest_plain_symbol_trend_report_rolling7.json'
DST = BASE / 'latest_management_analysis_report.json'

r7 = json.loads(SRC.read_text(encoding='utf-8'))
rows7 = r7.get('rows') or r7.get('symbols') or []
src_sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
hist_date = r7.get('latest_history_date')
hist_jalali = r7.get('latest_history_date_jalali') or jalali_from(hist_date)

cand = sorted([r for r in rows7 if isinstance(r.get('final_score'), (int, float))],
              key=lambda x: x['final_score'], reverse=True)
top10 = cand[:10]
sig_keys = [k for k in (top10[0].keys() if top10 else []) if 'SIGNAL' in k.upper()]

def classify(r):
    rsi = r.get('rsi_14')
    if not isinstance(rsi, (int, float)): return 'داده موجود نیست'
    if rsi >= 70: return 'اشباع خرید — ریسک اصلاح کوتاه'
    if rsi >= 66: return 'نزدیک اشباع خرید — نیازمند پایش'
    return 'حرارت متعادل — فضای ادامه روند'

# ── سربرگ: دیتا مال چه تاریخی و چه ساعتی است ──
header = {
    'title': 'تحلیل',
    'data_time_label': (
        f'داده معاملاتی روز {hist_jalali} (بسته شدن بازار — حدود ساعت ۱۲:۳۰ تهران)؛ '
        f'بازسازی گزارش: {jalali_now()}'
    ),
    'latest_history_date': hist_date,
    'latest_history_date_jalali': hist_jalali,
    'data_type': 'EOD — پایان روز معاملاتی؛ ساعت داده = زمان بسته شدن بازار',
    'generated_at': datetime.now().isoformat(),
    'source_of_truth': str(SRC),
    'source_report_sha256': src_sha,
}

report = {
    'report_version': 'MANAGEMENT_ANALYSIS-1.1',
    **header,
    'universe_size': len(rows7),
    'window_sessions': r7.get('window_sessions'),
    'top10': [{
        'symbol': r.get('symbol'),
        'final_score': r['final_score'],
        'classification': r.get('classification'),
        'return_20_sessions_pct': r.get('return_20_sessions_pct'),
        'rsi_14': r.get('rsi_14'),
        'buy_sell_signal': (r.get(sig_keys[0]) if sig_keys else 'NOT_GENERATED'),
        'management_note': classify(r),
    } for r in top10],
    'fundamental_layer': 'داده موجود نیست — لایه Codal هنوز ادغام نشده',
    'trade_permission': 'NOT_PERMITTED — سیگنال قطعی مطابق منشور تولید نمیشود؛ تصمیم با Decision Engine',
}
DST.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('OK:', DST)
print('سربرگ:', report['data_time_label'])
print('top10:', len(report['top10']), '| signal_keys:', sig_keys)
