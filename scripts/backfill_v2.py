#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Historical backfill v2 - resilient, standalone."""
from __future__ import annotations
import json, hashlib, sys, os, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PARENT_DIR)

from tsetmc_adapter import TSETMCAdapter

REQUEST_TIMEOUT = 25
MAX_ATTEMPTS = 3
BACKOFF_BASE = 2.0
RATE_LIMIT_DELAY = 0.12
PROGRESS_EVERY = 50
BASE_URL = "https://cdn.tsetmc.com/api"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

def fetch_json(url):
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw = resp.read()
                sha = hashlib.sha256(raw).hexdigest()
                return json.loads(raw.decode("utf-8")), sha
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_ATTEMPTS:
                wait = BACKOFF_BASE ** attempt
                print(f"    [attempt {attempt}/{MAX_ATTEMPTS}] {type(exc).__name__} - retry in {wait:.0f}s", flush=True)
                time.sleep(wait)
    raise last_exc

def at_or_before(values, target_time):
    valid = [x for x in values if isinstance(x, dict) and x.get("hEven") is not None and int(x["hEven"]) <= target_time]
    return max(valid, key=lambda x: int(x["hEven"])) if valid else None

def backfill_date(adapter, universe, date, target_time="123000"):
    records = universe.get("records", [])
    total = len(records)
    rows = []
    errors = 0
    t0 = time.time()
    tt = int(target_time)
    checkpoint_path = Path(f"output/history/tsetmc/checkpoint_{date}.json")
    start_idx = 0
    if checkpoint_path.exists():
        try:
            ck = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            rows = ck.get("rows", [])
            start_idx = ck.get("next_index", 0)
            errors = ck.get("errors", 0)
            print(f"  [resume] {len(rows)} rows done, start at {start_idx}", flush=True)
        except Exception:
            print("  [resume] checkpoint corrupt, fresh start", flush=True)
    for i in range(start_idx, total):
        item = records[i]
        ins_code = str(item.get("instrument_id") or "").strip()
        symbol = str(item.get("symbol") or "").strip()
        if not ins_code:
            continue
        closing_url = f"{BASE_URL}/ClosingPrice/GetClosingPriceHistory/{ins_code}/{date}"
        limits_url = f"{BASE_URL}/BestLimits/{ins_code}/{date}"
        try:
            cp, csha = fetch_json(closing_url)
            lp, lsha = fetch_json(limits_url)
            closing = at_or_before(cp.get("closingPriceHistory") or [], tt)
            limit = at_or_before(lp.get("bestLimitsHistory") or [], tt)
            rows.append({"identity":{"instrument_id":ins_code,"symbol":symbol,"contract_type":item.get("contract_type"),"underlying_id":item.get("underlying_id"),"underlying_symbol":item.get("underlying_symbol"),"strike":item.get("strike"),"begin_date":item.get("begin_date"),"end_date":item.get("end_date"),"remaining_days":item.get("remaining_days"),"contract_size":item.get("contract_size")},"observation":{"date":date,"requested_through":target_time,"closing":closing,"best_limits":limit},"evidence":{"source":"TSETMC","closing_history_endpoint":closing_url,"closing_history_sha256":csha,"best_limits_history_endpoint":limits_url,"best_limits_history_sha256":lsha}})
        except Exception as exc:
            errors += 1
            rows.append({"identity":{"instrument_id":ins_code,"symbol":symbol,"contract_type":item.get("contract_type"),"underlying_id":item.get("underlying_id"),"underlying_symbol":item.get("underlying_symbol"),"strike":item.get("strike"),"begin_date":item.get("begin_date"),"end_date":item.get("end_date"),"remaining_days":item.get("remaining_days"),"contract_size":item.get("contract_size")},"status":"INSUFFICIENT","error_type":type(exc).__name__,"error":str(exc)[:200]})
        time.sleep(RATE_LIMIT_DELAY)
        if (i + 1) % PROGRESS_EVERY == 0:
            elapsed = time.time() - t0
            rate = (i + 1 - start_idx) / elapsed if elapsed > 0 else 0
            eta_min = ((total - i - 1) / rate / 60) if rate > 0 else -1
            print(f"  [{i+1}/{total}] rows={len(rows)} err={errors} rate={rate:.1f}/s eta={eta_min:.0f}min", flush=True)
        if (i + 1) % 200 == 0:
            ck = {"next_index": i + 1, "rows": rows, "errors": errors}
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_path.write_text(json.dumps(ck, ensure_ascii=False), encoding="utf-8")
    return rows, errors, total

def main():
    dates = sys.argv[1:]
    if not dates:
        print("Usage: python3 scripts/backfill_v2.py 20261011 20261012", flush=True)
        return 1
    adapter = TSETMCAdapter()
    print("Loading universe...", flush=True)
    universe = adapter.option_market_watch_universe()
    print(f"Universe loaded: {universe.get("record_count")} records", flush=True)
    for date in dates:
        print(f"\n{chr(61)*50}\nBackfill {date} (target_time=123000)\n{chr(61)*50}", flush=True)
        rows, errors, total = backfill_date(adapter, universe, date)
        obs = {"captured_at_utc": datetime.now(timezone.utc).isoformat(), "requested_through": "123000", "rows": rows}
        snapshot = {"status":"SUCCESS" if rows else "INSUFFICIENT","source_of_truth":"TSETMC","snapshot_type":"HISTORICAL_BACKFILL_V2","target_date":date,"target_time":"123000","selection_rule":"latest explicit TSETMC record at or before target_time","generated_at_utc":datetime.now(timezone.utc).isoformat(),"universe_source":{"endpoint":universe.get("endpoint"),"snapshot_sha256":universe.get("snapshot_sha256"),"retrieved_at":universe.get("retrieved_at"),"record_count":universe.get("record_count")},"observation_count":1,"observations":[obs],"error_count":errors,"total_universe":total}
        snapshot["snapshot_sha256"] = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        out = Path(f"output/history/tsetmc/backfill_{date}.json")
        out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        succ = sum(1 for r in rows if r.get("status") != "INSUFFICIENT")
        print(f"\n  Saved: {out}\n  Rows: {len(rows)} | OK: {succ} | Err: {errors} | Univ: {total}\n  SHA256: {snapshot["snapshot_sha256"][:32]}...", flush=True)
        ck_path = Path(f"output/history/tsetmc/checkpoint_{date}.json")
        if ck_path.exists():
            ck_path.unlink()
            print(f"  Checkpoint cleaned: {ck_path}", flush=True)
    print(f"\n{chr(61)*50}\nAll backfills complete!", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
