import re
import unicodedata
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اسکنر سود لحظه آخری v2 — متدولوژی: قیمت تمام‌شده + رشد انتظاری پرمیوم
۱) مبنا: پیش از ۱۲:۳۰ قیمت لحظه‌ای | پس از بازار قیمت پایانی همان روز
۲) قیمت تمام‌شده = قیمت اعمال + پرمیوم
۳) رشد ریالی سهم = مبنای سهم × درصد رشد (سناریو صف خرید)
۴) درصد رشد انتظاری آپشن = (رشد ریالی ÷ پرمیوم) × ۱۰۰
۵) بدون گرد کردن محاسباتی — دقت کامل در JSON و Excel
"""
import requests, json, re, os, time, sys
from datetime import datetime, timezone, timedelta
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from scripts.premium_fallback import make_resolver as _mk_res, _FALLBACK_STATS, _load_snapshot_premiums
from underlying_map import resolve_underlying

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
           "Accept": "application/json, text/plain, */*"}
IRST = timezone(timedelta(hours=3, minutes=30))
IRAN_TRADING_DAYS = {5, 6, 0, 1, 2}
OPTION_URL = "https://webgw.tse.ir/InstrumentProvider/api/v1/MarketWatch/MarketWatchTradeOption/fa"
MW_URL = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch?market=0&paperTypes[0]=1&withBestLimits=false&hEven=0&RefID=0"
SEARCH_URL = "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch?searchTerm={}"
PRICE_URL = "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{}"

def val(obj):
    if obj is None: return None
    if isinstance(obj, dict): return obj.get("value")
    return obj

def now_ir(): return datetime.now(IRST)

def is_market_open():
    n = now_ir(); h = n.hour + n.minute / 60
    return (n.weekday() in IRAN_TRADING_DAYS) and (9 <= h <= 12.5)

def get_base_price(und, market_open):
    """متدولوژی بند ۱: انتخاب مبنای قیمت سهم بر اساس ساعت"""
    if market_open:
        base = und.get("last_price") or und.get("closing_price") or und.get("yesterday")
        return base, "قیمت لحظه‌ای", "realtime"
    base = und.get("closing_price") or und.get("last_price") or und.get("yesterday")
    return base, "قیمت پایانی", "closing"

def fetch_options():
    try:
        r = requests.get(OPTION_URL, headers=HEADERS, timeout=20); r.raise_for_status()
        items = r.json().get("Items", [])
        print(f"  ✅ قراردادها: {len(items)}")
        return items
    except Exception as e:
        print(f"  ❌ خطا در دریافت آپشن‌ها: {e}"); return []

def fetch_market_watch():
    try:
        r = requests.get(MW_URL, headers=HEADERS, timeout=25); r.raise_for_status()
        stocks = r.json().get("marketwatch", [])
        print(f"  ✅ سهم‌های بازار: {len(stocks)}")
        return stocks
    except Exception as e:
        print(f"  ⚠️ Market Watch ناموفق ({e}) — fallback جستجوی تفکیکی"); return []

def build_stock_lookup(market_watch):
    """ساختار واقعی MarketWatch: lva/pcl/pf/py/pmx/pmn"""
    lookup = {}
    for s in market_watch:
        symbol = (s.get("lva") or "").strip()
        if not symbol or symbol.startswith(("ض", "ط", "IR")):
            continue
        entry = {"symbol": symbol, "ins_code": s.get("insID"),
                 "last_price": s.get("pf") or s.get("pcl") or s.get("py") or 0,
                 "closing_price": s.get("pcl") or s.get("pf") or s.get("py") or 0,
                 "yesterday": s.get("py") or 0,
                 "ceiling": s.get("pmx") or 0, "floor": s.get("pmn") or 0}
        lookup[symbol] = entry
            for pre in ("ا", "وب", "و", "خ", "ف", "پ", "س", "ش", "گ", "ن", "ک", "د", "ب", "م", "ح", "ع", "ص", "ق", "ل", "ی", "ت", "ر"):
                if symbol.startswith(pre) and len(symbol) > len(pre):
                    lookup.setdefault(symbol[len(pre):], entry)
    return lookup

def search_underlying_fallback(term):
    try:
        r = requests.get(SEARCH_URL.format(term), headers=HEADERS, timeout=10); r.raise_for_status()
        for inst in r.json().get("instrumentSearch", []):
            sym = inst.get("lVal18AFC", "")
            if sym and not sym.startswith(("ض", "ط", "IR")):
                ins_code = inst.get("insCode")
                if ins_code: return ins_code, sym
    except: pass
    return None, None

def get_price_info(ins_code):
    try:
        r = requests.get(PRICE_URL.format(ins_code), headers=HEADERS, timeout=10); r.raise_for_status()
        cp = r.json().get("closingPriceInfo", {})
        return {"last_price": cp.get("pDrCotVal", 0), "closing_price": cp.get("pClosing", 0),
                "yesterday": cp.get("priceYesterday", 0) or cp.get("yesterday", 0),
                "ceiling": cp.get("psGelStaMax", 0), "floor": cp.get("psGelStaMin", 0)}
    except: return None



resolve_premium = _mk_res(requests, SEARCH_URL, HEADERS, get_price_info)
def find_underlying(option_symbol, lookup, fallback_cache, company_name=""):
    # روش ۰ (نقشه authoritative): ضملت→وبملت، طهرم→اهرم و ۲۲ مورد دیگر
    try:
        _sym = resolve_underlying(option_symbol, None)
        if not (_sym and _sym in lookup):
            _base = option_symbol[1:] if len(option_symbol) > 1 else ""
            if len(_base) >= 3:
                _hits = [k for k in lookup
                         if isinstance(k, str)
                         and not k.startswith(("ض", "ط"))
                         and 0 <= len(k) - len(_base) <= 2
                         and k.endswith(_base)]
                if len(_hits) == 1:
                    _sym = _hits[0]
        if not (_sym and _sym in lookup):
            _base = option_symbol[1:] if len(option_symbol) > 1 else ""
            if len(_base) >= 3:
                _hits = [k for k in lookup
                         if isinstance(k, str)
                         and not k.startswith(("ض", "ط"))
                         and 0 <= len(k) - len(_base) <= 2
                         and k.endswith(_base)]
                if len(_hits) == 1:
                    _sym = _hits[0]
        if _sym:
            _cand = lookup.get(_sym) if isinstance(lookup, dict) else None
            if _cand is not None:
                return _cand
    except Exception:
        pass
    # روش ۱ (قطعی): «اختيارخ وبملت-1454-...» یا «اختیارخ ...»
    m = re.search(r'اخ[تیي]ارخ\s+(.+?)\s*-', company_name or "")
    if m:
        cand = m.group(1).strip()
        if cand in lookup:
            return lookup[cand]
    # روش ۲: حذف ض/ط و ارقام + کاندیداهای پیشوند
    sym = re.sub(r'^[ضط]', '', option_symbol)
    sym = re.sub(r'\d+$', '', sym).strip()
    if not sym:
        return None
    for c in [sym, f"ا{sym}", f"وب{sym}", f"خ{sym}", f"ف{sym}", f"پ{sym}", f"س{sym}", f"ش{sym}", f"گ{sym}"]:
        if c in lookup:
            return lookup[c]
    if option_symbol not in fallback_cache:
        fallback_cache[option_symbol] = None
    return fallback_cache.get(option_symbol)

def calculate_option(op, und, market_open, fixed_growth=None):
    """متدولوژی v2: قیمت تمام‌شده + رشد انتظاری پرمیوم"""
    premium, _p_source = resolve_premium(op)
    op["_premium_source"] = _p_source
    if not premium or premium <= 0:
        return None  # قرنطینه، نه حذف
    strike = val(op.get("buyQeymateEmal"))
    days_left = val(op.get("buyBaqimandeTaSarresId"))
    volume = val(op.get("buyTradeVolume"))
    if not strike or not premium: return None
    base, basis_fa, basis_en = get_base_price(und, market_open)
    if not base or base <= 0: return None
    ceiling = und.get("ceiling", 0)
    break_even = strike + premium                      # بند ۲
    if fixed_growth is not None:                        # سناریوی درصد دلخواه (مثل 2.99)
        growth_pct = fixed_growth
        rial_growth = base * fixed_growth / 100         # بند ۳-الف
    else:
        if not ceiling or ceiling <= 0:
            return {"option_symbol": op.get("buyInstrumentName", ""), "underlying_symbol": und.get("symbol", ""),
                    "strike": strike, "premium": premium, "base_price": base,
                    "price_basis": basis_fa, "price_basis_en": basis_en,
                    "underlying_ceiling": 0, "break_even": break_even,
                    "share_growth_pct": None, "rial_growth": None,
                    "premium_growth_pct": None, "days_left": days_left,
                    "volume": volume, "status": "🚫 بدون سقف", "score": None, "_quarantine": "no_ceiling"}
        growth_pct = (ceiling - base) / base * 100
        rial_growth = ceiling - base
    premium_growth = (rial_growth / premium) * 100      # بند ۳-ب
    if ceiling and ceiling <= strike:
        status = "⚠️ OTM در سقف"
    elif premium_growth > 10: status = "🎯 عالی"
    elif premium_growth > 0: status = "✅ فرصت"
    elif premium_growth > -10: status = "⚠️ مرزی"
    else: status = "❌ گران"
    return {"option_symbol": op.get("buyInstrumentName", ""), "underlying_symbol": und.get("symbol", ""),
            "strike": strike, "premium": premium, "base_price": base,
            "price_basis": basis_fa, "price_basis_en": basis_en,
            "underlying_ceiling": ceiling, "break_even": break_even,
            "share_growth_pct": growth_pct, "rial_growth": rial_growth,
            "premium_growth_pct": premium_growth, "days_left": days_left,
            "volume": volume, "status": status, "score": premium_growth}


def main():
    fixed_growth = None
    if len(sys.argv) > 1:
        try: fixed_growth = float(sys.argv[1].replace("٪", "").replace("%", "").strip())
        except ValueError: fixed_growth = None
    n = now_ir(); market_open = is_market_open()
    basis_fa, basis_en = ("قیمت لحظه‌ای", "realtime") if market_open else ("قیمت پایانی", "closing")
    print("=" * 90)
    print("  🎯 اسکنر سود لحظه آخری v2 — متدولوژی: قیمت تمام‌شده + رشد انتظاری پرمیوم")
    print(f"  📅 {n.strftime('%Y-%m-%d %H:%M:%S')} IRST | بازار: {'🟢 باز' if market_open else '🔴 بسته'}")
    print(f"  📐 مبنا: {basis_fa}" + (f" | سناریو رشد فرضی: {fixed_growth}٪" if fixed_growth else " | سناریو: رشد تا سقف واقعی"))
    print("=" * 90)
    print("📡 دریافت داده‌ها...")
    options = fetch_options()
    if not options: print("\n❌ داده آپشن دریافت نشد. خروج."); return
    mw = fetch_market_watch()
    lookup = build_stock_lookup(mw) if mw else {}
    if lookup: print(f"  ✅ جدول جستجو: {len(lookup)} مورد")
    fb_cache = {}
    print("\n⚙️ محاسبه...")
    results, unmatched, no_ceiling = [], [], []
    for op in options:
        bn = op.get("buyInstrumentName", "")
        if not bn or not bn.startswith("ض"): continue
        und = find_underlying(re.sub(r"\d+$", "", bn) or bn, lookup, fb_cache, op.get("buyCompanyNamePersian", ""))
        if not und: unmatched.append({"symbol": bn, "reason": "نگاشت ناموفق"}); continue
        r = calculate_option(op, und, market_open, fixed_growth)
        if r:
            if r.get("_quarantine"):
                no_ceiling.append({"symbol": bn, "base": r.get("underlying_symbol", ""), "reason": r.get("_quarantine")})
            else:
                results.append(r)
        else:
            no_ceiling.append({"symbol": bn, "base": und.get("symbol", ""), "reason": "invalid_data"})
    results.sort(key=lambda x: x["premium_growth_pct"], reverse=True)
    opps = [r for r in results if r["premium_growth_pct"] > 0]
    print(f"  ✅ محاسبه‌شده: {len(results)} | فرصت مثبت: {len(opps)} | قرنطینه: {len(no_ceiling)} | تطبیق‌نیافته: {len(unmatched)}")
    print("\n" + "=" * 110)
    print("  📋 گزارش — سناریوی صف خرید | امتیاز = درصد رشد انتظاری پرمیوم")
    print("=" * 110)
    if opps:
        print(f"\n{'#':<3} {'آپشن':<14} {'سهم':<10} {'اعمال':>7} {'پرمیوم':>7} {'تمام‌شده':>9} {'رشد٪سهم':>9} {'رشد٪آپشن':>10} وضعیت")
        print("-" * 110)
        for i, r in enumerate(opps, 1):
            print(f"{i:<3} {r['option_symbol']:<14} {r['underlying_symbol']:<10} {r['strike']:>7,} "
                  f"{r['premium']:>7,} {r['break_even']:>9,} {r['share_growth_pct']:>+8.2f}% "
                  f"{r['premium_growth_pct']:>+9.2f}% {r['status']}")
        print(f"\n  💡 دقت کامل اعداد بدون گرد کردن در فایل‌های JSON و Excel ذخیره می‌شود.")
    from reporting.reports.lmp_report import LMPReport
    os.makedirs("output/reports/lmp", exist_ok=True)
    ts = n.strftime("%Y%m%d_%H%M")
    rpt = LMPReport()
    envelope = rpt.to_json(results, unmatched, no_ceiling, {"fixed_growth": fixed_growth})
    jf = f"output/reports/lmp/lmp_{ts}.json"
    with open(jf, "w", encoding="utf-8") as f: json.dump(envelope, f, ensure_ascii=False, indent=2)
    with open("output/reports/lmp/latest.json", "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)
    print(f"\n💾 JSON: {jf}")
    xf = f"output/reports/lmp/lmp_{ts}.xlsx"
    rpt.to_excel(envelope, xf)
    print(f"📊 Excel: {xf}")
    print(f"\n✅ تکمیل — {len(opps)} فرصت | مبنا: {basis_fa} | run_id: {envelope['run_id']}")

if __name__ == "__main__":
    main()
