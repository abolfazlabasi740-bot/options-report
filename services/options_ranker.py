#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
رتبه‌بندی زنده اختیار معامله (Call) از TSETMC
طبق PROTOCOL_OPTIONS_RANKING_V2
فقط تمرکز روی آپشن — بدون تحلیل سهم
"""

import re
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# ============== تنظیمات ==============
REF_DATE = "1405/05/16"          # تاریخ مرجع
TOP_N = 15
TIMEOUT = 25
SLEEP_BETWEEN_UA = 0.15          # احترام به سرور هنگام گرفتن قیمت پایه
OPTION_URL = "https://cdn.tsetmc.com/api/Instrument/GetInstrumentOptionMarketWatch/0"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.tsetmc.com",
    "Referer": "https://www.tsetmc.com/",
}

session = requests.Session()
session.headers.update(HEADERS)

def jalali_to_days(jstr):
    try:
        y, m, d = [int(x) for x in str(jstr).strip().split("/")]
        return y * 365 + m * 30 + d
    except Exception:
        return 0

def parse_strike_expiry(name: str):
    """استخراج قیمت اعمال و تاریخ سررسید از lVal30_C"""
    if not isinstance(name, str):
        return None, None
    m_date = re.search(r"(14\d{2}/\d{1,2}/\d{1,2})", name)
    expiry = m_date.group(1) if m_date else None
    m_strike = re.search(r"[-–—]\s*(\d{2,8})\s*[-–—]\s*14\d{2}/", name)
    if not m_strike:
        m_strike = re.search(r"(\d{2,8})\s*[-–—]?\s*14\d{2}/", name)
    strike = int(m_strike.group(1)) if m_strike else None
    return strike, expiry

def min_max(series, reverse=False):
    s = pd.to_numeric(series, errors="coerce")
    s_min, s_max = s.min(), s.max()
    if pd.isna(s_min) or pd.isna(s_max) or s_max == s_min:
        return pd.Series(0.5, index=series.index)
    res = (s - s_min) / (s_max - s_min)
    return (1 - res) if reverse else res

def fetch_options_raw():
    r = session.get(OPTION_URL, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    rows = data.get("instrumentOptMarketWatch") or []
    return rows

def fetch_ua_price(ua_code, cache):
    ua_code = str(ua_code)
    if ua_code in cache:
        return cache[ua_code]
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ua_code}"
    try:
        r = session.get(url, timeout=TIMEOUT)
        if r.status_code != 200:
            cache[ua_code] = None
            return None
        data = r.json()
        info = data.get("closingPriceInfo") or data.get("ClosingPriceInfo") or data
        px = None
        if isinstance(info, dict):
            px = info.get("pDrCotVal") or info.get("pClosing")
        cache[ua_code] = float(px) if px is not None else None
    except Exception:
        cache[ua_code] = None
    time.sleep(SLEEP_BETWEEN_UA)
    return cache[ua_code]

def build_calls_df(rows):
    records = []
    for r in rows:
        name = r.get("lVal30_C")
        symbol = r.get("lVal18AFC_C")
        strike, expiry = parse_strike_expiry(name or "")
        last = r.get("pDrCotVal_C") if r.get("pDrCotVal_C") not in (None, 0) else r.get("pClosing_C")
        rec = {
            "نماد": symbol,
            "نام_کامل": name,
            "insCode": r.get("insCode_C"),
            "uaInsCode": r.get("uaInsCode"),
            "قیمت_اعمال": strike,
            "تاریخ_سررسید": expiry,
            "آخرین_قیمت": last,
            "حجم": r.get("qTotTran5J_C"),
            "ارزش_معاملات": r.get("qTotCap_C"),
            "تعداد_معامله": r.get("zTotTran_C"),
            "OI": r.get("oP_C"),
            "contractSize": r.get("contractSize"),
        }
        records.append(rec)
    df = pd.DataFrame(records)
    # عددی کردن
    for col in ["قیمت_اعمال", "آخرین_قیمت", "حجم", "ارزش_معاملات", "OI", "تعداد_معامله"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def apply_protocol(df):
    """فیلتر + محاسبات + امتیاز ۱۰ عاملی (با امتیاز ثابت برای یونانی‌های ناموجود)"""
    # فیلتر حیاتی طبق پروتکل
    df = df[
        (df["آخرین_قیمت"].fillna(0) > 0) &
        (df["حجم"].fillna(0) > 0) &
        (df["ارزش_معاملات"].fillna(0) > 0) &
        (df["قیمت_اعمال"].notna()) &
        (df["نماد"].notna())
    ].copy()
    if df.empty:
        return df

    # قیمت سهم پایه
    cache = {}
    unique_ua = df["uaInsCode"].dropna().astype(str).unique().tolist()
    print(f"در حال دریافت قیمت پایه برای {len(unique_ua)} دارایی Underlying ...")
    ua_map = {}
    for i, ua in enumerate(unique_ua, 1):
        ua_map[ua] = fetch_ua_price(ua, cache)
        if i % 10 == 0:
            print(f"  ... {i}/{len(unique_ua)}")
    df["قیمت_پایه"] = df["uaInsCode"].astype(str).map(ua_map)
    df = df[df["قیمت_پایه"].fillna(0) > 0].copy()
    if df.empty:
        return df

    # محاسبات اولیه
    ref_days = jalali_to_days(REF_DATE)
    df["سربه‌سر"] = df["قیمت_اعمال"] + df["آخرین_قیمت"]
    df["اهرم"] = (df["قیمت_پایه"] / df["آخرین_قیمت"]).round(2)
    df["فاصله_سربه‌سر"] = (
        ((df["سربه‌سر"] - df["قیمت_پایه"]) / df["قیمت_پایه"]) * 100
    ).round(3)
    df["روز_باقی‌مانده"] = df["تاریخ_سررسید"].apply(
        lambda x: jalali_to_days(x) - ref_days if pd.notna(x) else np.nan
    )

    # ----- امتیازدهی (وزن‌ها دقیقاً مطابق پروتکل) -----
    # ۱. فاصله سربه‌سر ۲۰٪ (معکوس)
    s_gap = min_max(df["فاصله_سربه‌سر"], reverse=True) * 20
    # ۲. ارزش معاملات ۱۸٪
    s_val = min_max(df["ارزش_معاملات"]) * 18
    # ۳. حجم ۱۵٪
    s_vol = min_max(df["حجم"]) * 15
    # ۴. اهرم ۱۲٪ — بهینه حدود ۵ تا ۲۰ (قله ≈ ۱۲.۵)
    ahram_score = np.maximum(0, 1 - np.abs(df["اهرم"] - 12.5) / 7.5)
    s_lev = min_max(ahram_score) * 12
    # ۵. روز باقی‌مانده ۱۰٪ — بهینه ۳ تا ۳۰ (قله ≈ ۱۶.۵)
    days_score = np.maximum(0, 1 - np.abs(df["روز_باقی‌مانده"].fillna(0) - 16.5) / 13.5)
    s_days = min_max(days_score) * 10
    # ۶. IV ۱۰٪ — ناموجود → ثابت ۶ از ۱۰  → بعد از min_max تقریباً متوسط
    s_iv = pd.Series(6.0, index=df.index)   # چون داده IV نداریم
    # ۷. دلتا ۸٪ — ناموجود → ۴ از ۸
    s_delta = pd.Series(4.0, index=df.index)
    # ۸. ارزش زمانی ۵٪ — تقریبی ساده: آخرین قیمت (زمانی بیشتر ≈ گران‌تر بودن اختیار)
    #    (intrinsic تقریبی برای Call = max(S-K,0) ؛ time ≈ premium - intrinsic)
    intrinsic = np.maximum(df["قیمت_پایه"] - df["قیمت_اعمال"], 0)
    time_val = np.maximum(df["آخرین_قیمت"] - intrinsic, 0)
    s_time = min_max(time_val) * 5
    # ۹. شکاف قیمتی ۲٪ — داده مستقیم نداریم → امتیاز متوسط ۱
    s_spread = pd.Series(1.0, index=df.index)

    df["امتیاز"] = (
        s_gap + s_val + s_vol + s_lev + s_days + s_iv + s_delta + s_time + s_spread
    ).round(2)

    df = df.sort_values("امتیاز", ascending=False).head(TOP_N).reset_index(drop=True)
    df["رتبه"] = df.index + 1
    return df

def make_markdown(df):
    if df is None or df.empty:
        return "⚠️ هیچ قرارداد Call معتبری پس از فیلتر یافت نشد."

    md = "| رتبه | نماد | اعمال | آخرین قیمت | سربه‌سر | قیمت پایه | اهرم | فاصله سربه‌سر | تاریخ سررسید | روز باقی‌مانده | امتیاز |\n"
    md += "|:---:|------|:-----:|:----------:|:-------:|:---------:|:----:|:-------------:|:------------:|:--------------:|:------:|\n"

    for _, row in df.iterrows():
        md += (
            f"| {int(row['رتبه'])} | {row['نماد']} | "
            f"{int(row['قیمت_اعمال']):,} | {int(row['آخرین_قیمت']):,} | "
            f"{int(row['سربه‌سر']):,} | {int(row['قیمت_پایه']):,} | "
            f"{row['اهرم']:.2f} | {row['فاصله_سربه‌سر']:.3f}% | "
            f"{row['تاریخ_سررسید']} | {int(row['روز_باقی‌مانده']) if pd.notna(row['روز_باقی‌مانده']) else '—'} | "
            f"{row['امتیاز']} |\n"
        )
    return md

def make_analysis(df, source_note):
    if df is None or df.empty:
        return "داده‌ای برای تحلیل وجود ندارد."
    avg_lev = df["اهرم"].mean()
    neg_days = int((df["روز_باقی‌مانده"] < 0).sum())
    avg_gap = df["فاصله_سربه‌سر"].mean()
    top_sym = df.iloc[0]["نماد"]
    top_score = df.iloc[0]["امتیاز"]
    total_value = df["ارزش_معاملات"].sum()

    text = (
        f"**خلاصه تحلیلی (PROTOCOL_OPTIONS_RANKING_V2):**\n"
        f"رتبه‌بندی ۱۵ قرارداد برتر Call بر اساس داده زنده TSETMC ({source_note}). "
        f"مدل ۱۰‌عاملی با تمرکز اصلی روی فاصله سربه‌سر (۲۰٪)، نقدشوندگی ارزش/حجم (۳۳٪) و اهرم بهینه اجرا شد. "
        f"میانگین اهرم گروه برتر ≈ {avg_lev:.2f} و میانگین فاصله سربه‌سر ≈ {avg_gap:.2f}٪ است. "
        f"{neg_days} قرارداد دارای روز باقی‌مانده منفی/سررسید گذشته‌نما هستند و ریسک زمانی بالایی دارند. "
        f"نفر اول: {top_sym} با امتیاز {top_score}. "
        f"مجموع ارزش معاملات ۱۵تای برتر نشان‌دهنده تمرکز نقدشوندگی نسبی در این گروه است. "
        f"یونانی‌های IV و دلتا در فید فعلی موجود نبودند و طبق پروتکل امتیاز ثابت گرفتند؛ "
        f"بنابراین رتبه‌بندی بیشتر بر پایه قیمت، نقدشوندگی، اهرم و زمان تا سررسید است. "
        f"این خروجی صرفاً رتبه‌بندی کمّی است و توصیه خرید/فروش قطعی محسوب نمی‌شود. "
        f"همیشه حجم، فاصله سربه‌سر و روز باقی‌مانده را قبل از تصمیم نهایی بررسی کنید."
    )
    # کوتاه کردن اگر خیلی طولانی شد
    if len(text) > 1100:
        text = text[:1050] + "..."
    return text

def main():
    print("=" * 60)
    print("شروع رتبه‌بندی زنده اختیار (فقط Call)")
    print("زمان:", datetime.now())
    print("مرجع تاریخ:", REF_DATE)
    print("=" * 60)

    try:
        rows = fetch_options_raw()
        print(f"ردیف خام دریافت‌شده (جفت C/P): {len(rows)}")
        if not rows:
            print("داده خالی است.")
            return

        # نمایش کلیدها برای اطمینان
        print("\nکلیدهای موجود در ردیف اول:")
        print(sorted(rows[0].keys()))

        df_all = build_calls_df(rows)
        print(f"Call استخراج‌شده: {len(df_all)}")

        df_top = apply_protocol(df_all)
        print(f"پس از فیلتر و امتیازدهی — تعداد نهایی Top: {len(df_top)}")

        if df_top.empty:
            print("هیچ قراردادی از فیلترها عبور نکرد. فیلترها را بررسی کن.")
            # ذخیره خام برای دیباگ
            df_all.to_csv("output_calls_raw.csv", index=False, encoding="utf-8-sig")
            print("خام ذخیره شد: output_calls_raw.csv")
            return

        md = make_markdown(df_top)
        analysis = make_analysis(df_top, "GetInstrumentOptionMarketWatch/0")

        report = md + "\n\n" + analysis
        print("\n" + "=" * 60)
        print("گزارش نهایی (همین را بعداً ربات می‌فرستد):")
        print("=" * 60)
        print(report)

        # ذخیره
        with open("output_options_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        df_top.to_csv("output_options_top15.csv", index=False, encoding="utf-8-sig")
        print("\n✅ فایل‌ها ذخیره شدند:")
        print("  - output_options_report.md")
        print("  - output_options_top15.csv")

    except Exception as e:
        print("❌ خطا:", type(e).__name__, e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


def generate_options_message():
    """خروجی آماده برای ربات تلگرام"""
    from datetime import datetime

    rows = fetch_options_raw()
    df_all = build_calls_df(rows)
    df_top = apply_protocol(df_all)

    md = make_markdown(df_top)
    analysis = make_analysis(df_top, "GetInstrumentOptionMarketWatch/0")

    header = (
        f"📊 گزارش رتبه‌بندی اختیار (Call)\n"
        f"⏱ {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"پروتکل: OPTIONS_RANKING_V2\n\n"
    )
    msg = header + md + "\n\n" + analysis
    if len(msg) > 4000:
        msg = msg[:3900] + "\n…"
    return msg
