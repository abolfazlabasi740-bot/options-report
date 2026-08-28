#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست دریافت داده زنده از TSETMC
هدف: مطمئن شویم قبل از ساخت ربات کامل، داده سهام و اختیار قابل دریافت است.
"""

import sys
import json
import traceback
from datetime import datetime

try:
    import requests
    import pandas as pd
except ImportError:
    print("❌ اول نصب کن: pip install requests pandas lxml beautifulsoup4")
    sys.exit(1)

# هدر شبیه مرورگر (خیلی مهم برای TSETMC)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.tsetmc.com",
    "Referer": "https://www.tsetmc.com/",
    "Connection": "keep-alive",
}

session = requests.Session()
session.headers.update(HEADERS)
TIMEOUT = 20

def section(title):
    print("\n" + "=" * 60)
    print(f"▶ {title}")
    print("=" * 60)

def ok(msg):
    print(f"✅ {msg}")

def warn(msg):
    print(f"⚠️  {msg}")

def err(msg):
    print(f"❌ {msg}")

def try_json(url, desc):
    try:
        r = session.get(url, timeout=TIMEOUT)
        print(f"   URL: {url}")
        print(f"   Status: {r.status_code} | Len: {len(r.content)} bytes")
        if r.status_code != 200:
            err(f"{desc}: HTTP {r.status_code}")
            print(r.text[:300])
            return None
        data = r.json()
        ok(f"{desc}: JSON دریافت شد")
        return data
    except Exception as e:
        err(f"{desc}: {type(e).__name__}: {e}")
        return None

def test_search_symbol(keyword="شفا"):
    section(f"۱. جستجوی نماد: {keyword}")
    url = f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/{keyword}"
    data = try_json(url, "Instrument Search")
    if not data:
        return None

    # ساختارهای رایج پاسخ
    instruments = data.get("instrumentSearch") or data.get("InstrumentSearch") or data
    if isinstance(instruments, dict):
        instruments = instruments.get("data") or instruments.get("instruments") or []

    if not instruments:
        warn("لیست خالی یا ساختار ناشناخته")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:800])
        return None

    print(f"   تعداد نتیجه: {len(instruments) if isinstance(instruments, list) else '—'}")
    first = instruments[0] if isinstance(instruments, list) else instruments
    print("   نمونه اولین نتیجه (کلیدها):", list(first.keys()) if isinstance(first, dict) else type(first))
    print(json.dumps(first, ensure_ascii=False, indent=2)[:600])

    # استخراج insCode
    ins_code = None
    if isinstance(first, dict):
        ins_code = first.get("insCode") or first.get("InsCode") or first.get("instrumentID")
    if ins_code:
        ok(f"insCode پیدا شد: {ins_code}")
    else:
        warn("insCode پیدا نشد — ساختار را دستی چک کن")
    return ins_code, first

def test_closing_price(ins_code):
    section(f"۲. قیمت و اطلاعات پایانی (insCode={ins_code})")
    if not ins_code:
        warn("insCode نداریم — رد شد")
        return None
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    data = try_json(url, "ClosingPriceInfo")
    if data:
        # چاپ خلاصه مفید
        info = data.get("closingPriceInfo") or data.get("ClosingPriceInfo") or data
        if isinstance(info, dict):
            keys_show = ["pClosing", "pDrCotVal", "zTotTran", "qTotTran5J", "qTotCap", "priceYesterday", "pe"]
            summary = {k: info.get(k) for k in keys_show if k in info}
            print("   خلاصه فیلدهای مهم:", json.dumps(summary, ensure_ascii=False))
        else:
            print(str(data)[:500])
    return data

def test_client_type(ins_code):
    section(f"۳. حقیقی/حقوقی (insCode={ins_code})")
    if not ins_code:
        return
    url = f"https://cdn.tsetmc.com/api/ClientType/GetClientType/{ins_code}/1/0"
    try_json(url, "ClientType")

def test_market_watch():
    section("۴. مارکت‌واچ کلی (برای پیدا کردن اختیارها)")
    # چند endpoint رایج را امتحان می‌کنیم
    urls = [
        "https://cdn.tsetmc.com/api/MarketWatch/GetMarketWatch?h=0&r=0",
        "https://cdn.tsetmc.com/api/MarketWatch/GetMarketWatch",
    ]
    for url in urls:
        data = try_json(url, "MarketWatch")
        if not data:
            continue
        # تلاش برای فهم ساختار
        if isinstance(data, dict):
            print("   کلیدهای ریشه:", list(data.keys())[:20])
            # گاهی marketwatch یا raw data داخل است
            for k, v in data.items():
                if isinstance(v, list) and len(v) > 0:
                    print(f"   لیست «{k}» با {len(v)} آیتم — نمونه کلیدها:", 
                          list(v[0].keys()) if isinstance(v[0], dict) else type(v[0]))
                    # جستجوی قرارداد اختیار (معمولاً نماد با ض یا ط شروع می‌شود یا نام Option)
                    sample_names = []
                    for item in v[:50]:
                        if isinstance(item, dict):
                            lval = str(item.get("lVal18AFC") or item.get("lVal30") or item.get("n") or "")
                            if any(x in lval for x in ["ض", "ط", "اختيار", "اختیار", "OPTION"]):
                                sample_names.append(lval)
                    if sample_names:
                        ok(f"نمونه نمادهای شبیه اختیار: {sample_names[:8]}")
                    break
        print("-" * 40)

def test_option_specific():
    section("۵. endpointهای اختصاصی‌تر اختیار")
    candidates = [
        "https://cdn.tsetmc.com/api/Instrument/GetInstrumentOptionMarketWatch/1",
        "https://cdn.tsetmc.com/api/Instrument/GetInstrumentOptionMarketWatch/0",
        "https://cdn.tsetmc.com/api/Option/GetOptionMarketWatch",
        "https://cdn.tsetmc.com/api/MarketWatch/GetOptionMarketWatch",
    ]
    for url in candidates:
        data = try_json(url, "OptionWatch")
        if data:
            print("   کلیدها/نوع:", type(data), list(data.keys())[:15] if isinstance(data, dict) else "")
            print(str(data)[:400])
            print("-" * 40)

def test_finpy():
    section("۶. تست finpy-tse (اگر پچ‌شده نصب باشد)")
    try:
        import finpy_tse as fpy
        ok(f"finpy_tse import شد: {getattr(fpy, '__version__', 'version?')}")
        # چند تابع رایج را امتحان می‌کنیم (ممکن است نام‌ها فرق کند)
        for fn_name in ["market_watch", "MarketWatch", "get_market_watch", "stock_list"]:
            fn = getattr(fpy, fn_name, None)
            if callable(fn):
                print(f"   تابع پیدا شد: {fn_name} — در حال فراخوانی...")
                try:
                    df = fn()
                    if isinstance(df, pd.DataFrame):
                        ok(f"{fn_name}: DataFrame با shape={df.shape}")
                        print("   ستون‌ها:", list(df.columns)[:25])
                        print(df.head(3).to_string())
                        # فیلتر اختیار
                        name_cols = [c for c in df.columns if "نام" in str(c) or "نماد" in str(c) or "lVal" in str(c)]
                        print("   ستون‌های نام/نماد:", name_cols)
                        return df
                    else:
                        print(f"   خروجی نوع {type(df)}")
                except Exception as e:
                    warn(f"{fn_name} خطا: {e}")
        warn("تابع مارکت‌واچ آماده پیدا نشد — نسخه/پچ finpy را چک کن")
    except Exception as e:
        warn(f"finpy-tse در دسترس نیست یا پچ ناقص است: {e}")
        traceback.print_exc()

def test_homepage_and_static():
    section("۷. دسترسی پایه به خود tsetmc.com")
    try:
        r = session.get("https://www.tsetmc.com/", timeout=TIMEOUT)
        print(f"   tsetmc.com → {r.status_code} | {len(r.content)} bytes")
        if r.status_code == 200:
            ok("سایت در دسترس است")
        else:
            warn("سایت کد غیر200 داد")
    except Exception as e:
        err(f"دسترسی به سایت: {e}")

def main():
    print("⏱ شروع تست TSETMC")
    print(f"زمان: {datetime.now()}")
    print(f"Python: {sys.version}")

    test_homepage_and_static()

    result = test_search_symbol("شفا")
    ins_code = None
    if result:
        ins_code, _ = result

    # اگر شفا پیدا نشد، یک نماد معروف دیگر
    if not ins_code:
        warn("شفا insCode نداد — تست با وبملت")
        result = test_search_symbol("وبملت")
        if result:
            ins_code, _ = result

    test_closing_price(ins_code)
    test_client_type(ins_code)
    test_market_watch()
    test_option_specific()
    test_finpy()

    section("پایان تست")
    print("""
کارهای بعدی:
1. کل خروجی همین ترمینال را کپی کن و برای من بفرست.
2. مخصوصاً بگو کدام بخش‌ها ✅ و کدام ❌ شدند.
3. اگر MarketWatch یا Option endpoint داده داد، همان را پایه ربات می‌کنیم.
4. اگر فقط finpy کار کرد، روی همان مسیر می‌رویم.
""")

if __name__ == "__main__":
    main()
