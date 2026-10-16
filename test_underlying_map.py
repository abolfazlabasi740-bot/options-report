# -*- coding: utf-8 -*-
# test_underlying_map.py — تست‌های آفلاین نگاشت جهان اختیار معامله (بدون اینترنت)
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import underlying_map as M
try:
    from data import tsetmc as T
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import tsetmc as T

failures = []
def check(name, cond):
    print(('  OK  ' if cond else '  FAIL ') + name)
    if not cond:
        failures.append(name)

print('== نگاشت کامل ۲۶سهمی ==')
for und, pre in M.UNDERLYING_TO_PREFIX.items():
    check('پیشوند ' + und + ' = ' + pre, M.resolve_option_prefix(und) == pre)
    check('رفت‌وبرگشت ' + und, M.resolve_underlying(pre) == und)

print('== نمادهای پسونددار ==')
check('ضخود5000 → خودرو', M.resolve_underlying('ضخود5000') == 'خودرو')
check('ضملی120 → فملی', M.resolve_underlying('ضملی120') == 'فملی')
check('ضفرابورسxyz → فرابورس', M.resolve_underlying('ضفرابورسxyz') == 'فرابورس')

print('== خارج از جهان → None ==')
for sym in ('ضفول', 'ضگل', 'ضچاد', 'ضبندر', 'ضتران', 'ضفام', 'ضفول5000'):
    check(sym + ' → None', M.resolve_underlying(sym) is None)

print('== سایه‌اندازی پیشوندها ==')
check('ضدرو → دارونو', M.resolve_underlying('ضدرو') == 'دارونو')
check('ضدزاگرس → دزاگرس', M.resolve_underlying('ضدزاگرس') == 'دزاگرس')
check('ضملت → وبملت', M.resolve_underlying('ضملت') == 'وبملت')
check('ضملی → فملی', M.resolve_underlying('ضملی') == 'فملی')
check('ضطعام → طعام', M.resolve_underlying('ضطعام') == 'طعام')

print('== یکپارچگی با snapshot ==')
ROWS = [
    '28328922873641814,IRO1KHAZ0001,خودرو,إيران خودرو ديزل,NO,1,0',
    '46348259193204880,IRO1MSMI0001,فملی,ملی صنایع مس ايران,NO,1,0',
    '14846386625878570,IRXFOLA0S1491,ضخود,اختيارخ خودرو-091229,DE,1,0',
    '99999999999999999,IRXFAOL0S9991,ضفول,اختيارخ فولاد-091229,DE,1,0',
    '6115139416985570,IRO6FUND0001,عطروز,صندوق درآمد ثابت عطروز,FE,2,0',
    '15873539095825960,IRXGHER0001,غقهر,حق تقدم شركت گروه قهر,NO,1,0',
]
TEXT = '11450,3850000000000,17' + '@' + ';'.join(ROWS) + '@' + '1,2,3,4' + '@' + 'junk'
tmp = tempfile.mkdtemp()
try:
    s = T.snapshot(TEXT, 'test-source', repo_root=tmp)
    check('خروجی ok', s['ok'] is True)
    with open(os.path.join(tmp, 'output', 'lists', 'stocks', 'latest.json'), encoding='utf-8') as f:
        stocks_env = json.load(f)
    with open(os.path.join(tmp, 'output', 'lists', 'options', 'latest.json'), encoding='utf-8') as f:
        options_env = json.load(f)
    with open(os.path.join(tmp, 'output', 'lists', 'others', 'latest.json'), encoding='utf-8') as f:
        others_env = json.load(f)
    stock_syms = {r['symbol'] for r in stocks_env['records']}
    option_syms = {r['symbol'] for r in options_env['records']}
    others_syms = {r['symbol'] for r in others_env['records']}
    check('خودرو در سهام', 'خودرو' in stock_syms)
    check('فملی در سهام', 'فملی' in stock_syms)
    check('ضخود در آپشن', 'ضخود' in option_syms)
    r_khodro = next(r for r in options_env['records'] if r['symbol'] == 'ضخود')
    check('ضخود underlying = خودرو', r_khodro.get('underlying') == 'خودرو')
    check('ضفول در others', 'ضفول' in others_syms)
    check('ضفول در آپشن نیست', 'ضفول' not in option_syms)
    check('صندوق عطروز در others', 'عطروز' in others_syms)
    check('حق تقدم غقهر در others', 'غقهر' in others_syms)
    check('options_by_underlying = {خودرو:۱}', options_env['counts'].get('options_by_underlying') == {'خودرو': 1})
    check('validation_pass در هر سه پاکت', all(env['validation_pass'] is True for env in (stocks_env, options_env, others_env)))
    check('همه آپشن‌ها underlying دارند', all(r.get('underlying') for r in options_env['records']))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print('FAILURES:', failures if failures else 'NONE — all tests passed')
sys.exit(1 if failures else 0)
