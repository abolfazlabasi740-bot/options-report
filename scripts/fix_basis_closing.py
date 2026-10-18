"""بازمحاسبه قراردادهای urgent بر مبنای قیمت پایانی (نه آخرین قیمت).
سقف مجاز فردا = قیمت پایانی امروز × ۱.۰۵"""
import json, glob
from datetime import datetime
from underlying_map import resolve_underlying

files = sorted(glob.glob('output/reports/lmp/latest.json'))
assert files, "latest.json پیدا نشد!"
with open(files[0], encoding='utf-8') as f:
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
urgent = [r for r in rows if isinstance(r.get('days_left'), (int, float))
          and 0 <= r['days_left'] <= 1]
valid = [r for r in urgent if float(r.get('premium') or 0) >= 5]

out = []
for r in valid:
    base = float(r['base_price'])                    # قیمت پایانی (مبنای صحیح)
    strike = float(r['strike'])
    prem = float(r['premium'])
    ceiling_exact = base * 1.05                     # بدون گرد کردن
    ceiling = int(ceiling_exact + 0.5)              # سقف فردا (مبنای پایانی)
    intrinsic_now = base - strike
    intrinsic_ceiling = ceiling - strike
    growth_prem = (intrinsic_ceiling - prem) / prem * 100 if prem > 0 else 0.0
    out.append({
        'option_symbol': r['option_symbol'],
        'underlying': r['underlying_symbol'],
        'base_closing': base,
        'strike': strike,
        'premium': prem,
        'intrinsic_now': intrinsic_now,
        'safety_margin': intrinsic_now - prem,
        'ceiling_tomorrow': ceiling,
        'share_growth_pct_closing': (ceiling - base) / base * 100,
        'premium_growth_pct_closing': growth_prem,
        'days_left': r['days_left'],
        'volume': r.get('volume'),
    })

out.sort(key=lambda x: x['premium_growth_pct_closing'], reverse=True)
report = {'generated_at': datetime.now().isoformat(),
          'basis': 'closing_price', 'contracts': out}
with open('output/reports/lmp/urgent_closing.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"مبنای قیمت: پایانی | قراردادهای معتبر: {len(out)}")
for c in out:
    print(f"{c['option_symbol']} | پایه {c['underlying']} | پایانی {c['base_closing']} | "
          f"اعمال {c['strike']} | پرمیوم {c['premium']} | ذاتی {c['intrinsic_now']} | "
          f"سقف فردا {c['ceiling_tomorrow']} | رشد پرمیوم {c['premium_growth_pct_closing']}%")
