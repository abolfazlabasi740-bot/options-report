# -*- coding: utf-8 -*-
import os
import sys
import json
import unicodedata
from datetime import datetime
from pathlib import Path
import pytz

TEHRAN_TZ = pytz.timezone("Asia/Tehran")

# نگاشت قطعی ستون‌های بخش دوم MarketWatch TSETMC (۲۶ ستونی)
IDX = {
    "ins_code": 0,
    "isin": 1,
    "symbol": 2,
    "name": 3,
    "time": 4,
    "first": 5,
    "pc": 6,     # قیمت پایانی
    "pl": 7,     # آخرین قیمت معامله
    "tno": 8,    # تعداد معاملات
    "tvol": 9,   # حجم معاملات
    "tval": 10,  # ارزش معاملات (ریال)
    "pmin": 11,  # کمترین قیمت
    "pmax": 12,  # بیشترین قیمت
    "py": 13,    # قیمت دیروز (مبنای قطعی محاسبه درصد رشد)
    "eps": 14,
    "yval": 22   # نوع دارایی
}

# سهام عادی و حق تقدم مجاز
ALLOWED_YVAL = {"300", "301", "303", "309"}

def norm_fa(text: str) -> str:
    """استانداردسازی کاراکترهای عربی و فاصله‌های مجازی به فارسی استاندارد"""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    return text.replace("ي", "ی").replace("ك", "ک").strip()

def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd

def get_snapshot_time(marketwatch_path: Path):
    meta_path = marketwatch_path.parent / "metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            raw_ts = meta.get("retrieved_at") or meta.get("timestamp")
            if raw_ts:
                dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                return dt.astimezone(TEHRAN_TZ)
        except Exception:
            pass
    mtime = os.path.getmtime(marketwatch_path)
    return datetime.fromtimestamp(mtime, tz=TEHRAN_TZ)

def format_persian_header(dt: datetime, title: str) -> str:
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return (
        f"📅 تاریخ: {jy:04d}/{jm:02d}/{jd:02d} | ⏰ ساعت: {dt.strftime('%H:%M:%S')}\n"
        f"📊 {title}\n"
        f"{'=' * 44}"
    )

def parse_marketwatch():
    raw_path = Path("output/raw/tsetmc/marketwatch_latest.txt")
    if not raw_path.exists():
        print(f"❌ فایل خام در مسیر {raw_path} یافت نشد.")
        sys.exit(1)

    as_of = get_snapshot_time(raw_path)
    content = raw_path.read_text(encoding="utf-8", errors="ignore")
    parts = content.split("@")
    if len(parts) < 3:
        print("❌ فرمت فایل دیده‌بان نامعتبر است (بخش ردیف‌های نماد وجود ندارد).")
        sys.exit(1)

    rows = [r for r in parts[2].split(";") if r.strip()]
    records = []
    bad_rows = 0

    for r in rows:
        cols = r.split(",")
        if len(cols) <= max(IDX.values()):
            bad_rows += 1
            continue

        yval = cols[IDX["yval"]].strip()
        if yval not in ALLOWED_YVAL:
            continue

        try:
            py = float(cols[IDX["py"]])
            if py <= 0:
                continue

            pl = float(cols[IDX["pl"]])
            pc = float(cols[IDX["pc"]])
            tvol = float(cols[IDX["tvol"]])
            tval = float(cols[IDX["tval"]])
            tno = int(cols[IDX["tno"]])

            pl_pct = ((pl - py) / py) * 100.0
            pc_pct = ((pc - py) / py) * 100.0

            symbol_raw = cols[IDX["symbol"]].strip()
            name_raw = cols[IDX["name"]].strip()

            records.append({
                "ins_code": cols[IDX["ins_code"]].strip(),
                "isin": cols[IDX["isin"]].strip(),
                "symbol_raw": symbol_raw,
                "symbol": norm_fa(symbol_raw),
                "name": norm_fa(name_raw),
                "py": py,
                "pl": pl,
                "pc": pc,
                "pl_pct": pl_pct,
                "pc_pct": pc_pct,
                "tval": tval,
                "tvol": tvol,
                "tno": tno,
                "tval_b_toman": tval / 10_000_000_000.0
            })
        except (ValueError, IndexError):
            bad_rows += 1
            continue

    print(f"✅ پردازش موفق: {len(records):,} نماد مجاز سهام و حق‌تقدم (ردیف‌های نامعتبر: {bad_rows})")

    # تولید گزارش‌ها
    # ۱. بیشترین رشد بر مبنای آخرین معامله (pl)
    top_pl_gainers = sorted(records, key=lambda x: x["pl_pct"], reverse=True)[:20]
    # ۲. بیشترین رشد بر مبنای قیمت پایانی (pc)
    top_pc_gainers = sorted(records, key=lambda x: x["pc_pct"], reverse=True)[:20]
    # ۳. بیشترین ارزش معاملات
    top_turnover = sorted(records, key=lambda x: x["tval"], reverse=True)[:20]
    # ۴. بیشترین افت بر مبنای آخرین معامله
    top_pl_losers = sorted(records, key=lambda x: x["pl_pct"])[:20]

    # نمایش گزارش Top 20 رشد آخرین معامله
    print("\n" + format_persian_header(as_of, "۲۰ نماد با بیشترین رشد (بر مبنای آخرین معامله)"))
    print(f"{'رتبه':<4} {'نماد':<12} {'آخرین (ریال)':<14} {'رشد آخرین':<12} {'رشد پایانی':<12}")
    print("-" * 56)
    for idx, item in enumerate(top_pl_gainers, 1):
        print(f"{idx:<4} {item['symbol']:<12} {int(item['pl']):<14,} {item['pl_pct']:>+6.2f}%      {item['pc_pct']:>+6.2f}%")

    # ذخیره بسته تحلیلی جهت بات بله و اپلیکیشن اندروید
    out_dir = Path("output/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = out_dir / "market_analytics_bundle.json"

    bundle_data = {
        "metadata": {
            "snapshot_time": as_of.isoformat(),
            "shamsi_date": f"{gregorian_to_jalali(as_of.year, as_of.month, as_of.day)[0]:04d}/{gregorian_to_jalali(as_of.year, as_of.month, as_of.day)[1]:02d}/{gregorian_to_jalali(as_of.year, as_of.month, as_of.day)[2]:02d}",
            "time_str": as_of.strftime("%H:%M:%S"),
            "total_symbols_parsed": len(records)
        },
        "top_pl_gainers": top_pl_gainers,
        "top_pc_gainers": top_pc_gainers,
        "top_turnover": top_turnover,
        "top_pl_losers": top_pl_losers
    }

    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(bundle_data, f, ensure_ascii=False, indent=2)

    print(f"\n📁 بسته تحلیلی کامل ذخیره گردید: {bundle_path}")

if __name__ == "__main__":
    parse_marketwatch()
