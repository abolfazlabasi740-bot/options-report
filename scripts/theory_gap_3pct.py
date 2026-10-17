from underlying_map import resolve_underlying  # noqa: F401
# -*- coding: utf-8 -*-
"""اسکنر حفره تئوری ۳٪ — Theory Gap Scanner v2
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_source_policy import needs_quarantine, POLICY_VERSION, PRIMARY_SOURCE

ساخت خودکار پوشه خروجی | قرنطینه پرمیوم کف (بی‌معامله) و مبنا کهنه (بدون حذف) |
برچسب data_mode (LIVE/EOD) طبق رژیم دوگانه مصوب."""
import json, glob, os, sys
from datetime import datetime
sys.path.insert(0, 'scripts')
from freshness_gate import get_data_mode

GROWTH = 0.03
MIN_PREMIUM = 10          # پرمیوم زیر ۱۰ ریال = قیمت کف/بی‌معامله → قرنطینه
KNOWN_STALE_BASES = {7960} # مبنای کهنه شناخته‌شده (ملت پیش از افزایش سرمایه)

os.makedirs('output/reports/lmp_leverage', exist_ok=True)
os.makedirs('output/reports/quarantine', exist_ok=True)

def find_rows(node):
    if isinstance(node, list) and node and isinstance(node[0], dict):
        return node
    if isinstance(node, dict):
        for v in node.values():
            r = find_rows(v)
            if r: return r
    return None

_latest = sorted(glob.glob('output/reports/lmp/latest.json'))
with open(_latest[-1], encoding='utf-8') as f:
    rows = find_rows(json.load(f))

mode = get_data_mode()
report = {'report_name': 'Theory_Gap_3pct', 'version': 2,
          'generated_at': datetime.now().isoformat(),
          'data_mode': mode,
          'basis_note': 'مبنای EOD: قیمت پایانی رسمی | مبنای LIVE: pull زنده TSETMC',
          'hypothesis': 'رشد ۳٪ سهم پایه همان روز معاملاتی',
          'model': 'Point Effect (ITM)', 'contracts': []}
quarantined = []

print(f"[رژیم داده: {mode}]")
print(f"{'قرارداد':<14}{'سهم‌پایه':>10}{'تئوری':>8}{'الان':>8}{'ظرفیت٪':>9}{'وضعیت':>12}")
print('-' * 70)

if rows is None:
    print("[هشدار] منبع داده None برگرداند — احتمالاً پول زنده TSETMC در دسترس نیست.")
    print("[اقدام] اجرا در حالت EOD-fallback: خواندن آخرین فایل کش معتبر.")
    import glob, json, os
    cands = sorted(glob.glob("output/reports/lmp/lmp_*.json"))
    for cand in reversed(cands):
        with open(cand, encoding="utf-8") as f:
            rows = find_rows(json.load(f))
        if rows:
            print(f"[fallback] بارگذاری شد: {os.path.basename(cand)} ({len(rows)} ردیف)")
            break
    else:
        rows = None
    if not rows:
        print("[نتیجه] داده قابل استفاده نیست — سیگنالی صادر نشد (قاعده: تحلیل بدون داده ممنوع).")
        rows = []
for r in rows:
    B = float(r.get('base_price') or 0)
    P = float(r.get('premium') or 0)
    strike = float(r.get('strike') or 0)
    q = None
    if B <= 0 or P <= 0:
        q = 'مبنا یا پرمیوم نامعتبر'
    elif P < MIN_PREMIUM:
        q = f'پرمیوم کف/بی‌معامله ({P:.0f} ریال) — نقدشوندگی صفر'
    elif round(B) in KNOWN_STALE_BASES:
        q = 'مبنای کهنه (پیش از افزایش سرمایه) — نیازمند pull زنده TSETMC'
    if q:
        quarantined.append({'option_symbol': r.get('option_symbol'),
                            'underlying': r.get('underlying_symbol'),
                            'base_price': B, 'premium': P, 'reason': q,
                            'repair_path': 'python3 scripts/fetch_tsetmc_live.py'})
        continue
    delta_rial = B * GROWTH
    theory = P + delta_rial
    gap_pct = (theory - P) / P * 100
    moneyness = 'ITM' if B > strike else ('ATM' if abs(B-strike)/B < 0.02 else 'OTM⚠')
    report['contracts'].append({
        'option_symbol': r.get('option_symbol'), 'underlying': r.get('underlying_symbol'),
        'base_now': B, 'premium_now': P, 'strike': strike, 'moneyness': moneyness,
        'base_if_3pct': round(B*1.03, 2), 'delta_rial': round(delta_rial, 2),
        'theory_price': round(theory, 2), 'upside_to_theory_pct': round(gap_pct, 2)})
    print(f"{r.get('option_symbol'):<14}{B:>10.0f}{theory:>8.0f}{P:>8.0f}{gap_pct:>8.1f}%{moneyness:>12}")

ranked = sorted(report['contracts'], key=lambda x: -x['upside_to_theory_pct'])[:10]
report['ranking'] = [{'rank': i+1, 'symbol': c['option_symbol'],
                      'upside_to_theory_pct': c['upside_to_theory_pct']} for i, c in enumerate(ranked)]
report['quarantine_count'] = len(quarantined)

ts = datetime.now().strftime('%Y%m%d_%H%M')
out = f'output/reports/lmp_leverage/Theory_Gap_3pct_{ts}.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
qpath = f'output/reports/quarantine/Quarantined_{ts}.json'
with open(qpath, 'w', encoding='utf-8') as f:
    json.dump({'generated_at': report['generated_at'], 'data_mode': mode,
               'count': len(quarantined), 'policy': 'قرنطینه به‌جای حذف',
               'rows': quarantined}, f, ensure_ascii=False, indent=2)
with open('Theory_Gap_3pct_LATEST', 'w', encoding='utf-8') as f:
    f.write(out)
print(f"\n✅ گزارش [{mode}]: {out}")
print(f"🔒 قرنطینه: {len(quarantined)} سطر → {qpath}")
print("\n🏆 رتبه‌بندی (قابل‌معامله):")
for i, c in enumerate(ranked, 1):
    print(f"  {i}. {c['option_symbol']:<12}{c['upside_to_theory_pct']:>8.1f}%")
