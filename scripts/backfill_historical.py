#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Historical backfill — bypasses live clock, calls capture_once directly."""
from __future__ import annotations
import json, hashlib, sys, os, time
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to sys.path so we can import sibling modules
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PARENT_DIR)

from capture_tsetmc_historical_snapshot import capture_once
from tsetmc_adapter import TSETMCAdapter

def run_backfill(dates: list[str], target_time: str = "123000") -> int:
    adapter = TSETMCAdapter()
    print("Loading universe...", flush=True)
    universe = adapter.option_market_watch_universe()
    rec_count = universe.get("record_count", "?")
    print(f"Universe loaded: {rec_count} records", flush=True)

    for date in dates:
        t0 = time.time()
        print(f"\n{'='*50}", flush=True)
        print(f"Backfill {date} (target_time={target_time})", flush=True)
        print(f"{'='*50}", flush=True)

        obs = capture_once(adapter, universe, date, target_time)

        # capture_once returns {"rows": [...], "captured_at_utc": ..., "requested_through": ...}
        rows = obs.get("rows") or []
        row_count = len(rows) if isinstance(rows, list) else 0
        elapsed = time.time() - t0

        print(f"Rows captured: {row_count}", flush=True)
        print(f"Elapsed: {elapsed:.1f}s", flush=True)

        snapshot = {
            "status": "SUCCESS" if row_count else "INSUFFICIENT",
            "source_of_truth": "TSETMC",
            "snapshot_type": "HISTORICAL_BACKFILL",
            "target_date": date,
            "target_time": target_time,
            "selection_rule": "latest explicit TSETMC record at or before target_time",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "universe_source": {
                "endpoint": universe.get("endpoint"),
                "snapshot_sha256": universe.get("snapshot_sha256"),
                "retrieved_at": universe.get("retrieved_at"),
                "record_count": universe.get("record_count"),
            },
            "observation_count": 1,
            "observations": [obs],
        }
        snapshot["snapshot_sha256"] = hashlib.sha256(
            json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        output = Path(f"output/history/tsetmc/backfill_{date}.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8"
        )
        print(f"Saved: {output}", flush=True)
        print(f"SHA256: {snapshot['snapshot_sha256'][:32]}...", flush=True)

    print(f"\n{'='*50}", flush=True)
    print("All backfills complete!", flush=True)
    return 0

if __name__ == "__main__":
    dates = sys.argv[1:]
    if not dates:
        print("Usage: python3 scripts/backfill_historical.py 20261011 20261012", flush=True)
        raise SystemExit(1)
    raise SystemExit(run_backfill(dates))
