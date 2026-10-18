#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Management Analysis Report builder — derived from rolling7 report.

Glass-button «تحلیل مدیریتی» payload. Multi-factor evidence per top symbol:
technical structure (SMA stack, MACD), volatility (ATR-14, vol-20),
volume/value expansion, price-action (breakout, range position, correction
state, limit headroom), pre-lock sequence, and RSI. Master Project Book:
no invented numbers; missing data labeled explicitly; no buy/sell signal.
"""
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

MISSING = 'داده موجود نیست'
NO_DATA = 'داده موجود نیست'

def _num(x):
    return x if isinstance(x, (int, float)) else None

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
    """چندعاملی — ساختار روند + مومنتوم + حرارت + پرایس‌اکشن.
    هر بُعد فقط از داده واقعی همان ردیف؛ داده مفقود = «داده موجود نیست» و
    بُعد از جمع‌بندی حذف می‌شود (جایگزین نمی‌شود)."""
    notes, strengths = [], []
    trend = r.get('trend_state')
    rsi = _num(r.get('rsi_14'))
    macd_pct = _num(r.get('macd_pct'))
    atr_pct = _num(r.get('atr_14_pct'))
    vol_pct = _num(r.get('volatility_20_pct'))
    volr = _num(r.get('volume_ratio_5_to_20'))
    valr = _num(r.get('value_ratio_5_to_20'))
    rp20 = _num(r.get('range_position_20'))
    corr = r.get('correction_state')
    em = r.get('early_move') or {}
    brk = em.get('breakout_above_prior_20_high')
    prelock = (em.get('pre_lock_sequence') or {}).get('state')
    headroom = _num(r.get('upper_limit_headroom_pct'))

    # ۱) ساختار روند (SMA stack)
    if trend == 'UP_TREND_STRUCTURE':
        notes.append('ساختار روند صعودی (ترتیب میانگین‌ها)'); strengths.append(1)
    elif trend == 'DOWN_TREND_STRUCTURE':
        notes.append('ساختار روند نزولی'); strengths.append(-1)
    elif trend == 'MIXED_STRUCTURE':
        notes.append('ساختار روند مخلوط/بی‌تصمیم'); strengths.append(0)
    elif trend:
        notes.append(f'ساختار روند: {trend}'); strengths.append(0)
    else:
        notes.append(NO_DATA + ' — ساختار روند')
    # ۲) مومنتوم (MACD)
    if macd_pct is not None:
        if macd_pct > 0: notes.append(f'MACD مثبت ({macd_pct:+.1f}٪)'); strengths.append(1)
        elif macd_pct < 0: notes.append(f'MACD منفی ({macd_pct:+.1f}٪)'); strengths.append(-1)
        else: notes.append('MACD خنثی'); strengths.append(0)
    else:
        notes.append(NO_DATA + ' — MACD')
    # ۳) حرارت (RSI)
    if rsi is not None:
        if rsi >= 70: notes.append(f'RSI {rsi:.0f} — اشباع خرید، ریسک اصلاح کوتاه'); strengths.append(-1)
        elif rsi >= 66: notes.append(f'RSI {rsi:.0f} — نزدیک اشباع'); strengths.append(0)
        else: notes.append(f'RSI {rsi:.0f} — حرارت متعادل'); strengths.append(1 if rsi >= 50 else 0)
    else:
        notes.append(NO_DATA + ' — RSI')
    # ۴) پرایس‌اکشن — شکست/موقعیت در بازه
    if brk is True:
        notes.append('شکست سقف ۲۰ جلسه اخیر'); strengths.append(1)
    elif brk is False:
        notes.append('زیر سقف ۲۰ جلسه — شکتی رخ نداده')
    else:
        notes.append(NO_DATA + ' — وضعیت شکست')
    if rp20 is not None:
        if rp20 >= 0.8: notes.append(f'موقعیت {rp20*100:.0f}٪ کانال ۲۰ جلسه — نزدیک سقف'); strengths.append(1)
        elif rp20 <= 0.2: notes.append(f'موقعیت {rp20*100:.0f}٪ کانال ۲۰ جلسه — نزدیک کف'); strengths.append(0)
        else: notes.append(f'موقعیت {rp20*100:.0f}٪ کانال ۲۰ جلسه')
    # ۵) اصلاح
    if corr:
        notes.append(f'وضعیت اصلاح: {corr}')
        if 'CORRECTION_IN_UPTREND' in str(corr): strengths.append(0)
        elif 'RECOVERY_BOUNCE' in str(corr): strengths.append(0)
        elif 'CORRECTION' in str(corr) and 'IN_UPTREND' not in str(corr): strengths.append(-1)
    # ۶) حجم/ارزش — انبساط
    if volr is not None and valr is not None:
        if volr >= 1.5 and valr >= 1.5:
            notes.append(f'انبساط هم‌زمان حجم ({volr:.2f}×) و ارزش ({valr:.2f}×)'); strengths.append(1)
        elif volr >= 1.2 or valr >= 1.2:
            notes.append(f'افزایش نسبی حجم ({volr:.2f}×) / ارزش ({valr:.2f}×)'); strengths.append(0)
        elif volr < 0.8 and valr < 0.8:
            notes.append(f'انقباض حجم ({volr:.2f}×) و ارزش ({valr:.2f}×)'); strengths.append(-1)
    elif volr is not None or valr is not None:
        v = volr if volr is not None else valr
        notes.append(f'نسبت حجم/ارزش ۵ به ۲۰: {v:.2f}×')
    else:
        notes.append(NO_DATA + ' — حجم/ارزش')
    # ۷) تابلو — فاصله تا سقف
    if headroom is not None:
        if headroom <= 2: notes.append(f'فاصله تا سقف روز فقط {headroom:.1f}٪ — نزدیک قفل خرید')
        else: notes.append(f'فسجه سقف: {headroom:.1f}٪') if False else notes.append(f'فاصله تا سقف: {headroom:.1f}٪')
    else:
        notes.append(NO_DATA + ' — تابلو/BestLimits')
    # ۸) توالی پیش‌قفل
    if prelock in ('EARLY', 'DEVELOPING'):
        notes.append(f'توالی پیش‌قفل: {prelock}')
    # ۹) نوسان
    if atr_pct is not None and vol_pct is not None:
        notes.append(f'ATR {atr_pct:.1f}٪ / نوسان ۲۰جلسه {vol_pct:.1f}٪')
    elif atr_pct is not None:
        notes.append(f'ATR {atr_pct:.1f}٪')

    if strengths:
        s = sum(strengths)
        if s >= 2: label = 'هم‌گرایی مثبت چندعاملی'
        elif s <= -2: label = 'هم‌گرایی منفی چندعاملی'
        elif s > 0: label = 'کیفیت متعادل — تمایل مثبت'
        elif s < 0: label = 'کیفیت متعادل — تمایل منفی'
        else: label = 'متوازن'
    else:
        label = NO_DATA
    return label, '؛ '.join(notes)

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

def _factor_block(r):
    """قطعه شواهد چندعاملی هر نماد — فقط فیلدهای واقعی، مفقود = None."""
    em = r.get('early_move') or {}
    prelock = em.get('pre_lock_sequence') or {}
    return {
        # تکنیکال
        'trend_state': r.get('trend_state'),
        'sma_5': _num(r.get('sma_5')), 'sma_10': _num(r.get('sma_10')),
        'sma_20': _num(r.get('sma_20')), 'sma_50': _num(r.get('sma_50')),
        'rsi_14': _num(r.get('rsi_14')),
        'macd_12_26': _num(r.get('macd_12_26')), 'macd_pct': _num(r.get('macd_pct')),
        'atr_14_pct': _num(r.get('atr_14_pct')), 'volatility_20_pct': _num(r.get('volatility_20_pct')),
        # پرایس‌اکشن
        'breakout_above_prior_20_high': em.get('breakout_above_prior_20_high'),
        'range_position_20': _num(r.get('range_position_20')),
        'correction_state': r.get('correction_state'),
        'correction_from_prior_peak_pct': _num(r.get('correction_from_prior_peak_pct')),
        'pre_lock_state': prelock.get('state'),
        'pre_lock_sequence_label': prelock.get('sequence'),
        'pre_lock_direction': prelock.get('sequence_direction'),
        # تابلوخوانی
        'upper_limit_headroom_pct': _num(r.get('upper_limit_headroom_pct')),
        'touched_upper_limit_today': r.get('touched_upper_limit_today'),
        'volume_ratio_5_to_20': _num(r.get('volume_ratio_5_to_20')),
        'value_ratio_5_to_20': _num(r.get('value_ratio_5_to_20')),
        'volume_ratio_5_to_50': _num(r.get('volume_ratio_5_to_50')),
        'board_bestlimits': MISSING + ' — لایه BestLimits در گذر اول قرنطینه است (گیت معنایی)',
    }

report = {
    'report_version': 'MANAGEMENT_ANALYSIS-2.0',
    **header,
    'universe_size': len(rows7),
    'window_sessions': r7.get('window_sessions'),
    'top10': [{
        'symbol': r.get('symbol'),
        'final_score': r['final_score'],
        'classification': r.get('classification'),
        'return_5_sessions_pct': _num(r.get('return_5_sessions_pct')),
        'return_20_sessions_pct': _num(r.get('return_20_sessions_pct')),
        'rsi_14': _num(r.get('rsi_14')),
        'factors': _factor_block(r),
        'buy_sell_signal': (r.get(sig_keys[0]) if sig_keys else 'NOT_GENERATED'),
        'management_note': classify(r),
        'note_label': classify(r)[0],
        'note_detail': classify(r)[1],
        'warnings': r.get('warnings') or [],
    } for r in top10],
    'fundamental_layer': 'داده موجود نیست — لایه Codal هنوز ادغام نشده',
    'board_layer': MISSING + ' — BestLimits/حقیقی-حقوقی در گذر اول کل بازار خاموش است؛ برای نمادهای برتر قابل فعال‌سازی مجزا است',
    'trade_permission': 'NOT_PERMITTED — سیگنال قطعی مطابق منشور تولید نمیشود؛ تصمیم با Decision Engine',
}
DST.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('OK:', DST)
print('سربرگ:', report['data_time_label'])
print('top10:', len(report['top10']), '| signal_keys:', sig_keys)
print('نسخه: MANAGEMENT_ANALYSIS-2.0 (چندعاملی: تکنیکال + پرایس‌اکشن + تابلو)')
