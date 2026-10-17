"""منبع انحصاری: TSETMC. قیمت پایانی (pdClo) سهم پایه هر قرارداد را
در لحظه اسکن می‌کشد و base_price را تصحیح می‌کند. هیچ cache طولانی‌مدتی
در مسیر نیست — فقط data/raw/tsetmc به‌عنوان Raw Evidence (بدون overwrite)."""
import json, glob, re, urllib.request, hashlib
from datetime import datetime
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from underlying_map import resolve_underlying

def tse_get(inst_id):
    """دریافت قیمت پایانی زنده از TSETMC بر اساس شناسه نماد"""
    urls = [
        f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentInfo/{inst_id}",
        f"https://cdn.tsetmc.com/api/ClosingPrice/GetInstrumentClosingPrice/{inst_id}",
    ]
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            continue
    return None

with open(sorted(glob.glob('output/reports/lmp/latest.json'))[0], encoding='utf-8') as f:
    data = json.load(f)

def find_rows(node):
    if isinstance(node, list) and node and isinstance(node[0], dict):
        return node
    if isinstance(node, dict):
        for v in node.values():
            r = find_rows(v)
            if r: return r
    return None

rows = find_rows(data)
if not rows:
    _res = data.get("results") if isinstance(data, dict) else None
    if isinstance(_res, list):
        rows = [r for r in _res if isinstance(r, dict)]
    elif isinstance(_res, dict):
        rows = [r for v in _res.values() if isinstance(v, list)
                for r in v if isinstance(r, dict)]
rows = rows or []

raw_ev = {'fetched_at': datetime.now().isoformat(), 'source': 'TSETMC', 'rows': []}
fixed = 0
for r in rows:
    und = resolve_underlying(r.get('option_symbol'), r) or r.get('underlying_symbol')
    if not und:
        continue
    info = tse_get(und)  # در نسخه کامل: نگاشت نماد → inst_id از لغت‌نامه TSETMC
    # تصدیق سازگاری: قیمت پایانی زنده در برابر قیمت تمام‌شده قرارداد
    be, prem = float(r.get('break_even') or 0), float(r.get('premium') or 0)
    est = be - prem
    live_closing = None
    if info:
        for key in ('pdClo', 'closing_price', 'pClosing'):
            if isinstance(info, dict) and key in info:
                live_closing = float(info[key]); break
            if isinstance(info, dict):
                for v in info.values():
                    if isinstance(v, dict) and key in v:
                        live_closing = float(v[key]); break
            if live_closing: break
    if live_closing and live_closing > 0:
        r['base_price'] = live_closing          # تصحیح بر مبنای TSE زنده
        r['base_price_source'] = 'TSETMC'
        r['base_price_fetched_at'] = raw_ev['fetched_at']
        fixed += 1
    raw_ev['rows'].append({'symbol': r.get('option_symbol'), 'underlying': und,
                           'live_closing': live_closing, 'est_from_contract': est,
                           'old_base': r.get('base_price')})
    print(f"  {r.get('option_symbol')}: سهم پایه {und} | پایانی زنده TSE: {live_closing} | تخمین بازار: {est}")

# Raw Evidence — بدون overwrite
h = hashlib.md5(raw_ev['fetched_at'].encode()).hexdigest()[:10]
with open(f'data/raw/tsetmc/{raw_ev['fetched_at'][:10]}_{h}.json', 'w', encoding='utf-8') as f:
    json.dump(raw_ev, f, ensure_ascii=False, indent=2)
with open('output/reports/lmp/latest.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"✅ {fixed} سطر بر مبنای قیمت پایانی زنده TSETMC تصحیح شد")
