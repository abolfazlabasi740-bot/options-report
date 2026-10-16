import json, os, sys, tempfile
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reporting.repository as R

failures = []
def check(name, cond):
    print(('  OK  ' if cond else '  FAIL ') + name)
    if not cond:
        failures.append(name)

TZ = R._TZ
def at(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=TZ)

print('== weekday anchors ==')
assert at(2026, 10, 17, 10).weekday() == 5
assert at(2026, 10, 16, 10).weekday() == 4
assert at(2026, 10, 15, 10).weekday() == 3
assert at(2026, 10, 14, 10).weekday() == 2

print('== ساعات بازار ==')
check('شنبه ۱۰:۰۰ در بازار', R.is_market_hours(at(2026, 10, 17, 10)))
check('شنبه ۱۲:۳۰ مرز داخل', R.is_market_hours(at(2026, 10, 17, 12, 30)))
check('شنبه ۱۲:۳۱ خارج', not R.is_market_hours(at(2026, 10, 17, 12, 31)))
check('شنبه ۰۸:۵۹ خارج', not R.is_market_hours(at(2026, 10, 17, 8, 59)))
check('جمعه خارج', not R.is_market_hours(at(2026, 10, 16, 10)))
check('پنجشنبه خارج', not R.is_market_hours(at(2026, 10, 15, 10)))

print('== آخرین جلسه ==')
check('جمعه ۱۵:۰۰ → چهارشنبه', R._last_session_start(at(2026, 10, 16, 15)).date().isoformat() == '2026-10-14')
check('شنبه ۰۷:۰۰ → چهارشنبه', R._last_session_start(at(2026, 10, 17, 7)).date().isoformat() == '2026-10-14')
check('شنبه ۱۳:۰۰ → امروز', R._last_session_start(at(2026, 10, 17, 13)).date().isoformat() == '2026-10-17')

print('== پارسر زمان ==')
check('ISO +03:30', R._parse_ts('2026-10-17T10:00:00+03:30') == at(2026, 10, 17, 10))
check('ISO Z → تهران', R._parse_ts('2026-10-17T06:30:00Z') == at(2026, 10, 17, 10))
check('naive → تهران', R._parse_ts('2026-10-17 10:00:00') == at(2026, 10, 17, 10))
check('epoch ثانیه آگاه', R._parse_ts(1760000000).tzinfo is not None)
check('epoch رشته میلی', isinstance(R._parse_ts('1760000000000'), datetime))
try:
    R._parse_ts('۱۴۰۵/۰۷/۲۴ ۱۰:۳۰')
    check('جلالی نامعتبر → ValueError', False)
except ValueError:
    check('جلالی نامعتبر → ValueError', True)

print('== تازگی و بارگذاری ==')
real_now = R.now_tehran
tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, 'lmp'))
mock = {
    'report_type': 'lmp', 'title': 'گزارش LMP — فرصت‌های اختیار معامله',
    'run_id': 'a' * 64, 'generated_at': '2026-10-17T09:55:00+03:30',
    'market_open': True, 'price_basis': 'realtime', 'validation_pass': True,
    'score_summary': 'امتیاز کل: ۸۵/۱۰۰',
    'results': [dict() for _ in range(12)],
    'no_ceiling': [dict() for _ in range(2)],
    'unmatched': [dict() for _ in range(3)],
    'ranking_top': [{'symbol': 'ضوبير', 'score': 91}, {'symbol': 'وهنر', 'score': 87}, {'symbol': 'فولاد', 'score': 85}],
}

def write_mock(gen):
    m = dict(mock)
    m['generated_at'] = gen
    with open(os.path.join(tmp, 'lmp', 'latest.json'), 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False)

def load_at(now):
    R.now_tehran = lambda: now
    try:
        return R.load('lmp', repo_dir=tmp)
    finally:
        R.now_tehran = real_now

write_mock('2026-10-17T09:55:00+03:30')
r = load_at(at(2026, 10, 17, 10))
check('داخل بازار، ۵ دقیقه → fresh', r['ok'] and r['fresh'] is True and r['age_minutes'] == 5.0)

write_mock('2026-10-17T09:25:00+03:30')
r = load_at(at(2026, 10, 17, 10))
check('داخل بازار، ۳۵ دقیقه → stale', r['ok'] and r['fresh'] is False and r.get('reason') == 'stale')

write_mock('2026-10-14T12:35:00+03:30')
r = load_at(at(2026, 10, 16, 15))
check('جمعه بعدازظهر، داده چهارشنبه → fresh', r['ok'] and r['fresh'] is True)

r = load_at(at(2026, 10, 17, 7))
check('شنبه قبل از باز، داده چهارشنبه → fresh', r['ok'] and r['fresh'] is True)

write_mock('2026-10-14T08:00:00+03:30')
r = load_at(at(2026, 10, 17, 7))
check('شنبه قبل از باز، داده قبل از جلسه → stale', r['ok'] and r['fresh'] is False)

r = R.load('nonexistent', repo_dir=tmp)
check('نبود فایل → not_found', r['ok'] is False and r['error'] == 'not_found')

with open(os.path.join(tmp, 'lmp', 'latest.json'), 'w') as f:
    f.write('{broken json')
r = load_at(at(2026, 10, 17, 10))
check('JSON خراب → read_error', r['ok'] is False and r['error'].startswith('read_error'))

with open(os.path.join(tmp, 'lmp', 'latest.json'), 'w', encoding='utf-8') as f:
    json.dump({'foo': 1}, f)
r = load_at(at(2026, 10, 17, 10))
check('بدون run_id → invalid_envelope', r['ok'] is False and r['error'] == 'invalid_envelope')

print('== رندر ==')
text = R.render(mock, fresh=True)
check('رندر شامل عنوان', '📊' in text and 'LMP' in text)
check('رندر شامل run_id و اعتبارسنجی', 'run_id' in text and '✅' in text)
check('رندر شامل شمارنده‌ها', 'نتایج: 12' in text and 'بدون سقف: 2' in text and 'نامنگاشت: 3' in text)
check('رندر شامل برترین‌ها', 'ضوبير' in text and 'امتیاز: 91' in text)
text_stale = R.render(mock, fresh=False)
check('رندر کهنه شامل هشدار', '⚠️' in text_stale)

write_mock('2026-10-17T09:55:00+03:30')
xl = os.path.join(tmp, 'lmp', 'lmp_20261017_1000.xlsx')
open(xl, 'w').close()
check('آخرین Excel', R.latest_excel('lmp', repo_dir=tmp) == xl)

print()
print('FAILURES:', failures if failures else 'NONE — all tests passed')
print('--- sample render ---')
print(text)
sys.exit(1 if failures else 0)
