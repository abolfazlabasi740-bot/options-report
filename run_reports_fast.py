# -*- coding: utf-8 -*-
import os, sys, json
from datetime import datetime
import pytz

TEHRAN_TZ = pytz.timezone("Asia/Tehran")

IDX = {
    "ins_code": 0,
    "isin": 1,
    "symbol": 2,
    "name": 3,
    "pc": 6,   # closing
    "pl": 7,   # last
    "py": 11,  # yesterday
    "yval": 22
}
ALLOWED_YVAL = {"300", "301", "303", "309"}  # equities + rights variants

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

def _try_parse_iso_to_tehran(s):
    s = (s or "").strip()
    if not s: return None
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(TEHRAN_TZ)
    except Exception:
        return None

def _walk_find_retrieved_at(obj):
    if isinstance(obj, dict):
        ra = obj.get("retrieved_at")
        if ra:
            dt = _try_parse_iso_to_tehran(ra)
            if dt: return dt
        for v in obj.values():
            dt = _walk_find_retrieved_at(v)
            if dt: return dt
    elif isinstance(obj, list):
        for it in obj:
            dt = _walk_find_retrieved_at(it)
            if dt: return dt
    return None

def get_snapshot_timestamp():
    # no questions, just best-effort discovery
    candidates = [
        "output/raw/tsetmc/manifest.json",
        "output/lists/stocks/latest.json",
        "output/lists/options/latest.json",
        "output/lists/others/latest.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                dt = _walk_find_retrieved_at(data)
                if dt: return dt
            except Exception:
                pass

    raw_path = "output/raw/tsetmc/marketwatch_latest.txt"
    if os.path.exists(raw_path):
        return datetime.fromtimestamp(os.path.getmtime(raw_path), TEHRAN_TZ)

    return datetime.now(TEHRAN_TZ)

def shamsi_header(dt):
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d} | {dt.strftime('%H:%M:%S')}"

def load_marketwatch_rows():
    raw_path = "output/raw/tsetmc/marketwatch_latest.txt"
    if not os.path.exists(raw_path):
        print(f"❌ Missing: {raw_path}")
        sys.exit(1)

    content = open(raw_path, "r", encoding="utf-8", errors="ignore").read()
    parts = content.split("@")
    if len(parts) < 3:
        print("❌ Invalid raw format.")
        sys.exit(1)

    return [r for r in parts[2].split(";") if r]

def parse_once(rows):
    recs = []
    bad = 0
    for r in rows:
        cols = r.split(",")
        if len(cols) <= IDX["yval"]:
            bad += 1
            continue

        yval = cols[IDX["yval"]].strip()
        if yval not in ALLOWED_YVAL:
            continue

        try:
            py = float(cols[IDX["py"]])
            if py <= 0:
                continue

            pc = float(cols[IDX["pc"]]) if cols[IDX["pc"]] else 0.0
            pl = float(cols[IDX["pl"]]) if cols[IDX["pl"]] else 0.0
            if pc <= 0 and pl <= 0:
                continue

            recs.append({
                "ins_code": cols[IDX["ins_code"]].strip(),
                "isin": cols[IDX["isin"]].strip(),
                "symbol": cols[IDX["symbol"]].strip(),
                "name": cols[IDX["name"]].strip(),
                "last": pl,
                "close": pc,
                "yesterday": py,
                "last_pct": ((pl - py) / py) * 100.0 if pl > 0 else -1e18,
                "close_pct": ((pc - py) / py) * 100.0 if pc > 0 else -1e18,
                "yval": yval,
            })
        except Exception:
            bad += 1
            continue
    return recs, bad

def top_n(records, key, n=20):
    # faster than sorting whole list if huge? sorting is OK for ~500-2000
    return sorted(records, key=lambda x: x[key], reverse=True)[:n]

def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def main():
    ts = get_snapshot_timestamp()
    hdr = shamsi_header(ts)

    rows = load_marketwatch_rows()
    records, bad = parse_once(rows)

    # build multiple reports from same dataset
    reports = {}
    reports["top_gainers_by_last"]  = top_n(records, "last_pct", 20)
    reports["top_gainers_by_close"] = top_n(records, "close_pct", 20)
    reports["top_losers_by_last"]   = sorted(records, key=lambda x: x["last_pct"])[:20]
    reports["top_losers_by_close"]  = sorted(records, key=lambda x: x["close_pct"])[:20]

    payload = {
        "retrieved_at_tehran": ts.isoformat(),
        "shamsi_header": hdr,
        "universe_count": len(records),
        "bad_rows": bad,
        "topN": 20,
        "reports": reports,
    }

    out_path = "output/reports/reports_bundle.json"
    write_json(out_path, payload)

    print("=" * 110)
    print("📦 بسته گزارش‌ها ساخته شد (FAST, single-parse)")
    print(f"📅 تاریخ/ساعت (تهران): {hdr}")
    print(f"Universe: {len(records):,} | Bad rows skipped: {bad:,}")
    print(f"✅ JSON: {out_path}")
    print("=" * 110)

if __name__ == "__main__":
    main()
