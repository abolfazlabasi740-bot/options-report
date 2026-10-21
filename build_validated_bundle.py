# -*- coding: utf-8 -*-
import os, sys, json, hashlib, re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
RAW_FILE = ROOT / "output" / "raw" / "tsetmc" / "marketwatch_latest.txt"
OUT_FILE = ROOT / "output" / "reports" / "market_analytics_bundle.json"
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

TEHRAN = ZoneInfo("Asia/Tehran")

def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0,31,59,90,120,151,181,212,243,273,304,334]
    jy = 979 if gy > 1600 else 0
    gy -= 1600 if gy > 1600 else 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (365*gy) + ((gy2+3)//4) - ((gy2+99)//100) + ((gy2+399)//400) - 80 + gd + g_d_m[gm-1]
    jy += 33*(days//12053)
    days %= 12053
    jy += 4*(days//1461)
    days %= 1461
    if days > 365:
        jy += (days-1)//365
        days = (days-1)%365
    if days < 186:
        jm = 1 + (days//31)
        jd = 1 + (days%31)
    else:
        jm = 7 + ((days-186)//30)
        jd = 1 + ((days-186)%30)
    return jy, jm, jd

def parse_float(val):
    if val is None:
        return 0.0
    s = str(val).strip().replace(',', '')
    if not s or s.lower() in ('null', 'none', '-'):
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0

def main():
    if not RAW_FILE.exists():
        print(f"❌ [Fail-Closed] RAW file not found: {RAW_FILE}", file=sys.stderr)
        sys.exit(1)

    raw_bytes = RAW_FILE.read_bytes()
    raw_text = raw_bytes.decode('utf-8', errors='ignore')

    # Timestamp discovery (retrieved_at first, then header/mtime fallback)
    mtime_dt = datetime.fromtimestamp(RAW_FILE.stat().st_mtime, tz=TEHRAN)
    m_ts = re.search(r'retrieved_at\s*[:=]\s*["\']?([0-9]{4}-[0-9]{2}-[0-9]{2}[T\s][0-9:.]{5,}(?:Z|[+-][0-9:]{2,5})?)', raw_text[:500], re.I)
    
    if m_ts:
        retrieved_at = m_ts.group(1).replace('Z', '+00:00')
        dt = datetime.fromisoformat(retrieved_at).astimezone(TEHRAN)
    else:
        dt = mtime_dt
        retrieved_at = dt.isoformat(timespec='seconds')

    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    date_shamsi = f"{jy:04d}/{jm:02d}/{jd:02d}"
    time_tehran = dt.strftime("%H:%M:%S")

    # Data Parsing: Standard TSETMC format (delimited by @ or semicolon/comma)
    sections = raw_text.split('@')
    symbols_raw = sections[2] if len(sections) > 2 else sections[0]
    
    rows = []
    bad_rows = 0
    
    # Split by semicolon or newline
    entries = re.split(r'[;\n\r]+', symbols_raw)
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(',')
        if len(parts) >= 11:
            try:
                # TSETMC standard fields index:
                # 0: inscode, 1: iid, 2: symbol_l18, 3: symbol_fa, 4: name, 5: time,
                # 6: first, 7: close, 8: last, 9: count, 10: volume, 11: value, 12: min, 13: max, 14: yesterday_price
                symbol = parts[2].strip() if len(parts) > 2 else ""
                name = parts[3].strip() if len(parts) > 3 else symbol
                last_price = parse_float(parts[8]) if len(parts) > 8 else 0.0
                close_price = parse_float(parts[7]) if len(parts) > 7 else 0.0
                yesterday = parse_float(parts[14]) if len(parts) > 14 else (parse_float(parts[6]) or close_price)

                if yesterday > 0:
                    pct_last = ((last_price - yesterday) / yesterday) * 100.0
                    pct_close = ((close_price - yesterday) / yesterday) * 100.0
                else:
                    pct_last = 0.0
                    pct_close = 0.0

                rows.append({
                    "symbol": symbol,
                    "name": name,
                    "last_price": last_price,
                    "final_close": close_price,
                    "pct_last": round(pct_last, 2),
                    "pct_close": round(pct_close, 2),
                    "volume": parse_float(parts[10]) if len(parts) > 10 else 0.0
                })
            except Exception:
                bad_rows += 1
        else:
            bad_rows += 1

    if not rows:
        print("❌ [Fail-Closed] No valid records extracted.", file=sys.stderr)
        sys.exit(2)

    # Filter & Sort Top 20 Gainers based on final_close change
    rows_valid = [r for r in rows if r["symbol"] and r["final_close"] > 0]
    rows_valid.sort(key=lambda x: x["pct_close"], reverse=True)
    top_20_gainers = rows_valid[:20]

    bundle = {
        "header": {
            "retrieved_at": retrieved_at,
            "date_shamsi": date_shamsi,
            "time_tehran": time_tehran,
            "total_records": len(rows),
            "bad_rows": bad_rows,
            "sha256": hashlib.sha256(raw_bytes).hexdigest()
        },
        "top_gainers_n": 20,
        "top_gainers": top_20_gainers
    }

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)

    print(f"✅ Bundle generated successfully: {len(rows)} rows processed, {len(top_20_gainers)} top gainers selected.")

if __name__ == "__main__":
    main()
