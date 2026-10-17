import json, glob
from datetime import datetime
from underlying_map import resolve_underlying

files = sorted(glob.glob('output/reports/lmp/latest.json'))
assert files, "latest.json پیدا نشد!"
with open(files[0], encoding='utf-8') as f:
    data = json.load(f)

today = datetime.now().date()

# کشف بازگشتی ساختار: اولین لیستی که آیتم‌هایش دیکشنری هستند
def find_rows(node):
    if isinstance(node, list) and node and isinstance(node[0], dict):
        return node
    if isinstance(node, dict):
        for v in node.values():
            r = find_rows(v)
            if r:
                return r
    return None

rows = find_rows(data)
assert rows, "هیچ لیست قراردادی در فایل پیدا نشد!"
print("کلیدهای آیتم:", list(rows[0].keys()))
print(f"تعداد کل قراردادها: {len(rows)}")

def days_left(r):
    dl = r.get('days_left')
    if dl is not None:
        return dl
    exp = r.get('expiry_date') or r.get('endDate') or r.get('end_date')
    if exp:
        for fmt in ('%Y/%m/%d', '%Y-%m-%d'):
            try:
                return (datetime.strptime(str(exp)[:10], fmt).date() - today).days
            except ValueError:
                pass
    return None

urgent = []
for r in rows:
    dl = days_left(r)
    if dl is not None and 0 <= dl <= 1:
        urgent.append((r, dl))

print("=" * 70)
print(f"⚠️  سررسید امروز/فردا: {len(urgent)} قرارداد")
print("=" * 70)
for r, dl in sorted(urgent, key=lambda x: x[1]):
    name = r.get('contract') or r.get('contractSymbol') or r.get('symbol') or '?'
    und = resolve_underlying(name, r) or r.get('underlying') or r.get('buyCompanyNamePersian') or '?'
    print(f"{name} | پایه: {und} | اعمال: {r.get('strike')} | "
          f"پرمیوم: {r.get('premium')} | قیمت تمام‌شده: "
          f"{r.get('break_even') or r.get('break_even_price')} | روز مانده: {dl}")

def score(r):
    for k in ('expected_premium_growth_pct', 'premium_growth_pct',
              'growth_pct', 'expected_growth_pct'):
        if r.get(k) is not None:
            return float(r[k])
    return 0.0

# فیلتر نقدشوندگی: حذف پرمیوم‌های عملاً بی‌ارزش (زیر ۵ ریال)
valid = [x for x in urgent if float(x[0].get('premium') or 0) >= 5]
if valid:
    best, bdl = max(valid, key=lambda x: score(x[0]))
    print()
    print("=" * 70)
    print("🎯 بهترین خرید (سررسید نزدیک + فیلتر پرمیوم >= ۵ ریال)")
    print("=" * 70)
    for k, v in best.items():
        print(f"  {k}: {v}")
    print(f"\n⏰ هشدار: {bdl} روز تا سررسید — ریسک زمانی (Theta) بحرانی است")
else:
    print("\n❌ قرارداد معتبری (پرمیوم >= ۵) برای بهترین خرید نبود")

print(f"\n✅ سایر قراردادها (سررسید امن): {len(rows) - len(urgent)} مورد")
