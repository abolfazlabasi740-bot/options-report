# -*- coding: utf-8 -*-
# test_tsetmc.py — تست‌های آفلاین موتور داده TSETMC (بدون اینترنت)
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data.tsetmc as T

failures = []
def check(name, cond):
    print(('  OK  ' if cond else '  FAIL ') + name)
    if not cond:
        failures.append(name)

ROWS = [
    '35425587644337450,IRO1FOLA0001,فولاد,فولاد مباركه اصفهان,NO,1,0',
    '46348259193204880,IRO1MSMI0001,فملی,ملی صنایع مس ايران,NO,1,0',
    '92117701108178190,IRO1BPEN0001,شپنا,پتروشيمي نفت ايران,NO,1,0',
    '14846386625878570,IRXFOLA0S1491,ضخود,اختيارخ خودرو-091229,DE,1,0',
    '15266935617820460,IRXFOLA0P1491,ضملی,اختيارخ فملی-091229,DE,1,0',
    '18134376835186950,IRXTSE0000S1,ضفرابورس,اختيارخ فرابورس-138029,DE,1,0',
    '6115139416985570,IRO6FUND0001,عطروز,صندوق درآمد ثابت عطروز,FE,2,0',
    '7789136217325970,IRT1KHA00001,اخزا,اسناد خزانه اسلامي,NO,1,0',
    '15873539095825960,IRXGHER0001,غقهر,حق تقدم شركت گروه قهر,NO,1,0',
    '12345678901234,وبهمن,حق تقدم بانك بهمن,NO,1,0',
    '1,2,x',
]

def build_raw(rows, header='11450,3850000000000,17'):
    return header + '@' + ';'.join(rows) + '@' + '1,2,3,4' + '@' + 'junk'

print('== پارس ==')
RAW = build_raw(ROWS)
p = T.parse_marketwatch(RAW)
check('تعداد ابزارها = ۱۰', len(p['instruments']) == 10)
check('رد ردیف خراب = ۱', p['skipped_rows'] == 1)
r_fola = next(x for x in p['instruments'] if x['symbol'] == 'فولاد')
check('نماد و عنوان و isin', r_fola['title'] == 'فولاد مباركه اصفهان' and r_fola['isin'] == 'IRO1FOLA0001')
r_beh = next(x for x in p['instruments'] if x['symbol'] == 'وبهمن')
check('ردیف بدون ISIN → خالی', r_beh['isin'] == '')
syms = [x['symbol'] for x in p['instruments']]
check('مرتب‌شده بر اساس نماد', syms == sorted(syms))
check('rows_seen = ۱۰', p['rows_seen'] == 10)

print('== خطاها ==')
for name, bad in (('متن خالی', ''), ('بدون @', 'abc,def'), ('بدون ابزار', '1,2@3,4')):
    try:
        T.parse_marketwatch(bad)
        check(name + ' → ValueError', False)
    except ValueError:
        check(name + ' → ValueError', True)

print('== تفکیک ==')
check('ض → آپشن', T.classify('ضفام', 'اختيارخ فولاد-091229') == 'options')
check('ط → آپشن', T.classify('طفام', 'هرچی') == 'options')
check('اختيار در عنوان', T.classify('فولاد', 'اختيارخ فولاد') == 'options')
check('اختیار فارسی در عنوان', T.classify('سهم', 'اختیار خرید') == 'options')
check('صندوق', T.classify('عطروز', 'صندوق درآمد ثابت') == 'funds')
check('اسناد', T.classify('اخزا', 'اسناد خزانه') == 'debt')
check('حق تقدم', T.classify('غقهر', 'حق تقدم شركت') == 'rights')
check('سهام ساده', T.classify('فولاد', 'فولاد مباركه') == 'equities')

print('== مخزن ==')
tmp = tempfile.mkdtemp()
s = T.snapshot(RAW, 'test-source', repo_root=tmp)
check('خروجی ok', s['ok'] is True)
check('سه فایل latest.json', all(os.path.exists(os.path.join(tmp, 'output', 'lists', k, 'latest.json')) for k in ('stocks', 'options', 'others')))
check('نسخه خام ذخیره شد', os.path.exists(os.path.join(tmp, 'output', 'raw', 'tsetmc', 'marketwatch_latest.txt')))
with open(os.path.join(tmp, 'output', 'lists', 'options', 'latest.json'), encoding='utf-8') as f:
    env_o = json.load(f)
with open(os.path.join(tmp, 'output', 'lists', 'stocks', 'latest.json'), encoding='utf-8') as f:
    env_s = json.load(f)
check('آپشن‌ها = ۳', len(env_o['records']) == 3)
check('فقط ض/ط در آپشن', all(r['symbol'][:1] in ('ض', 'ط') for r in env_o['records']))
check('سهام = ۳', len(env_s['records']) == 3)
check('فیلدهای پاکت', all(k in env_s for k in ('run_id', 'generated_at', 'source', 'source_detail', 'counts', 'validation_pass', 'records')))
c = env_s['counts']
check('جمع شمارش‌ها = کل', c['stocks'] + c['options'] + c['others'] == c['total_instruments'] == 10)
check('validation_pass', env_s['validation_pass'] is True)
check('run_id قطعی', T.snapshot(RAW, 'x', repo_root=tempfile.mkdtemp())['run_id'] == s['run_id'])
check('run_id متفاوت با داده متفاوت', T.snapshot(build_raw(ROWS[:-1]), 'x', repo_root=tempfile.mkdtemp())['run_id'] != s['run_id'])
check('اجرای دوباره بی‌خطر', T.snapshot(RAW, 'x', repo_root=tmp)['ok'] is True)
check('پیش‌نمایش', isinstance(s['preview']['stocks'], list) and len(s['preview']['stocks']) == 3)

print('== اعتبارسنجی پاسخ ==')
VALID_RAW = 'h@' + ';'.join(
    ['35425587644337450' + str(i) + ',IRO1FOLA0001,فولاد,فولاد مباركه,1,2,3,4,5'
     for i in range(12)]
) + '@'
check('پاسخ ساختاری معتبر', T._mw_is_valid(VALID_RAW))
check('رد HTML', not T._mw_is_valid('<html>blocked</html>'))
check('رد متن خالی', not T._mw_is_valid(''))

print('== دریافت ==')
real_http_get = T._http_get
T._http_get = lambda url, timeout=30: (VALID_RAW, url)
text, url = T.fetch(urls=['http://x/'])
check('دریافت موفق', 'فولاد' in text and url == 'http://x/')

def _fail(url, timeout=30):
    raise OSError('network down: ' + url)

T._http_get = _fail
try:
    T.fetch(urls=['http://a/', 'http://b/'])
    check('شکست همه → ConnectionError', False)
except ConnectionError as e:
    check('شکست همه → ConnectionError', 'http://a/' in str(e) and 'http://b/' in str(e))

T._http_get = lambda url, timeout=30: ('<html>blocked</html>', url)
try:
    T.fetch(urls=['http://c/'])
    check('پاسخ نامعتبر → ConnectionError', False)
except ConnectionError as e:
    check('پاسخ نامعتبر → ConnectionError', 'http://c/' in str(e))
T._http_get = real_http_get

print('== CLI ==')
rawfile = os.path.join(tmp, 'mw_raw.txt')
with open(rawfile, 'w', encoding='utf-8') as f:
    f.write(RAW)
check('CLI --file موفق', T.main(['--file', rawfile], repo_root=tmp) == 0)
check('CLI فایل ناموجود', T.main(['--file', os.path.join(tmp, 'nope.txt')], repo_root=tmp) == 1)

print()
print('FAILURES:', failures if failures else 'NONE — all tests passed')
print('--- نمونه خروجی CLI ---')
T.main(['--file', rawfile], repo_root=tmp)
sys.exit(1 if failures else 0)
