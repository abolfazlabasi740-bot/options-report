# -*- coding: utf-8 -*-
# reporting/repository.py — دروازه فقط-خواندنی مخزن گزارش‌ها (Single Source of Truth)
# مصرف‌کننده‌ها (دکمه‌های شیشه‌ای بله) هرگز داده تولید نمی‌کنند؛ فقط از این ماژول می‌خوانند.
# منبع واحد: output/reports/<type>/latest.json
# سیاست تازگی (TTL): داخل بازار حداکثر ۲۰ دقیقه؛ خارج از بازار داده‌ی آخرین جلسه.
import glob
import json
import os
from datetime import datetime, time as dtime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo('Asia/Tehran')
except Exception:
    _TZ = timezone(timedelta(hours=3, minutes=30))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_DIR = os.path.join(_ROOT, 'output', 'reports')

# python weekday(): Mon=0 ... Sat=5, Sun=6 — روزهای بازار: شنبه تا چهارشنبه
MARKET_DAYS = {5, 6, 0, 1, 2}
MARKET_OPEN_T = dtime(9, 0)
MARKET_CLOSE_T = dtime(12, 30)
MAX_AGE_INTRADAY_MIN = 20

EXTRA_HOLIDAYS = set()
_HOLIDAY_FILE = os.path.join(_ROOT, 'scripts', 'holidays.txt')


def _holidays():
    hs = set(EXTRA_HOLIDAYS)
    try:
        with open(_HOLIDAY_FILE, encoding='utf-8') as f:
            hs |= {ln.strip() for ln in f if ln.strip() and not ln.startswith('#')}
    except OSError:
        pass
    return hs


def now_tehran():
    return datetime.now(_TZ)


def _is_holiday(d):
    return d.isoformat() in _holidays()


def is_market_hours(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_TZ)
    return (dt.weekday() in MARKET_DAYS and not _is_holiday(dt.date())
            and MARKET_OPEN_T <= dt.time() <= MARKET_CLOSE_T)


def _last_session_start(dt):
    # شروع آخرین جلسه معتبر نسبت به لحظه dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_TZ)
    d = dt.date()
    if dt.time() < MARKET_OPEN_T:
        d -= timedelta(days=1)
    while d.weekday() not in MARKET_DAYS or _is_holiday(d):
        d -= timedelta(days=1)
    return datetime.combine(d, MARKET_OPEN_T, tzinfo=_TZ)


def _parse_ts(v):
    # پارس تحمل‌پذیر برچسب زمانی — فقط فرمت‌های استاندارد، بدون حدس
    if isinstance(v, (int, float)):
        n = float(v)
        return datetime.fromtimestamp(n / 1000 if n > 1e11 else n, _TZ)
    if isinstance(v, str):
        s = v.strip()
        if s.isdigit():
            n = int(s)
            return datetime.fromtimestamp(n / 1000 if n > 1e11 else n, _TZ)
        try:
            dt_ = datetime.fromisoformat(s.replace('Z', '+00:00'))
            if dt_.tzinfo is None:
                dt_ = dt_.replace(tzinfo=_TZ)
            return dt_.astimezone(_TZ)
        except ValueError:
            pass
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M'):
            try:
                return datetime.strptime(s, fmt).replace(tzinfo=_TZ)
            except ValueError:
                continue
    raise ValueError('unparseable timestamp: ' + repr(v))


def load(report_type, repo_dir=None):
    # خواندن آخرین پاکت گزارش + ارزیابی تازگی — تنها دروازه مصرف‌کننده‌ها
    path = os.path.join(repo_dir or _REPO_DIR, report_type, 'latest.json')
    out = {'ok': False, 'repo_path': path,
           'retrieved_at': now_tehran().isoformat(), 'report_type': report_type}
    if not os.path.exists(path):
        out['error'] = 'not_found'
        out['hint'] = 'هنوز رانی ثبت نشده — تولیدکننده (اسکنر/زمان‌بند) را اجرا کن'
        return out
    try:
        with open(path, encoding='utf-8') as f:
            env = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        out['error'] = 'read_error: ' + str(e)
        return out
    if not isinstance(env, dict) or 'run_id' not in env:
        out['error'] = 'invalid_envelope'
        return out
    out.update(ok=True, envelope=env)

    gen, basis = env.get('generated_at'), 'field'
    try:
        gen_dt = _parse_ts(gen)
    except Exception:
        try:
            gen_dt = datetime.fromtimestamp(os.path.getmtime(path), _TZ)
            basis = 'mtime'
        except OSError:
            out['error'] = 'no_timestamp'
            return out

    now = now_tehran()
    age = (now - gen_dt).total_seconds() / 60
    if is_market_hours(now):
        fresh, policy = age <= MAX_AGE_INTRADAY_MIN, 'intraday: حداکثر ۲۰ دقیقه'
    else:
        fresh, policy = gen_dt >= _last_session_start(now), 'خارج از بازار: داده‌ی آخرین جلسه'
    out.update(generated_at_dt=gen_dt.isoformat(), timestamp_basis=basis,
               age_minutes=round(age, 1), fresh=fresh, freshness_policy=policy)
    if not fresh:
        out['reason'] = 'stale'
    return out


def latest_excel(report_type, repo_dir=None):
    # آخرین فایل Excel تاریخ‌دار برای ارسال سند
    files = sorted(glob.glob(os.path.join(repo_dir or _REPO_DIR, report_type, '*.xlsx')))
    return files[-1] if files else None


def render(env, fresh=True):
    # خلاصه متنی استاندارد برای بله — فقط از فیلدهای موجود؛ هیچ عدد فرضی
    L = []
    title = env.get('title') or env.get('report_type') or 'گزارش'
    L.append('📊 ' + title)
    ga = env.get('generated_at') or env.get('generated_at_jalali') or '—'
    mo = env.get('market_open')
    sess = 'جلسه باز (لحظه‌ای)' if mo else 'جلسه بسته (قیمت پایانی)'
    L.append('🗓 ' + ga + ' | ' + sess + ' | مبنا: ' + str(env.get('price_basis') or '—'))
    rid = str(env.get('run_id') or '—')
    L.append('🧾 run_id: ' + rid[:12] + '… | اعتبارسنجی: ' + ('✅' if env.get('validation_pass') else '❌'))
    if not fresh:
        L.append('⚠️ داده کهنه — به‌روزرسانی در جریان')
    if env.get('score_summary'):
        L.append('🎯 ' + env['score_summary'])
    for fa, key in (('نتایج', 'results'), ('بدون سقف', 'no_ceiling'), ('نامنگاشت', 'unmatched')):
        v = env.get(key)
        if isinstance(v, list):
            L.append('📋 ' + fa + ': ' + str(len(v)))
    top = env.get('ranking_top')
    if isinstance(top, list) and top:
        L.append('🏆 برترین‌ها:')
        for it in top[:3]:
            if isinstance(it, dict):
                sym = it.get('symbol') or it.get('option_symbol') or it.get('name') or '—'
                sc = it.get('score', it.get('total_score'))
                L.append('   • ' + sym + (f' — امتیاز: {sc}' if sc is not None else ''))
    return '\n'.join(L)


def load_and_render(report_type):
    # ترکیب آماده برای هندلر: (متن، وضعیت تازگی، جزئیات)
    r = load(report_type)
    if not r['ok']:
        return '⚠️ گزارشی در مخزن نیست — تولیدکننده هنوز رانی ثبت نکرده است.', False, r
    return render(r['envelope'], fresh=r.get('fresh', False)), r.get('fresh', False), r
