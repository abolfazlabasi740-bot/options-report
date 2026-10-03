#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capture TSETMC live observations from 09:01 through 12:30 Tehran time."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from tsetmc_adapter import TSETMCAdapter

USER_AGENT = "OptimusAI-V4.1-TSETMC-LIVE-SNAPSHOT/1.0"


def request_json(url: str) -> tuple[dict, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.tsetmc.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
    return json.loads(body.decode("utf-8", errors="replace")), hashlib.sha256(body).hexdigest()


def capture_once(adapter: TSETMCAdapter, universe: dict, target_date: str, target_time: str) -> dict:
    rows = []
    for item in universe.get("records", []):
        ins_code = str(item.get("instrument_id") or "").strip()
        symbol = str(item.get("symbol") or "").strip()
        if not ins_code:
            continue

        closing_url = f"{adapter.base_url}/ClosingPrice/GetClosingPriceHistory/{ins_code}/{target_date}"
        limits_url = f"{adapter.base_url}/BestLimits/{ins_code}/{target_date}"

        try:
            closing_payload, closing_sha = request_json(closing_url)
            limits_payload, limits_sha = request_json(limits_url)

            def at_or_before(values):
                valid = [
                    x for x in values
                    if isinstance(x, dict) and x.get("hEven") is not None
                    and int(x["hEven"]) <= int(target_time)
                ]
                if not valid:
                    return None
                return max(valid, key=lambda x: int(x["hEven"]))

            closing = at_or_before(closing_payload.get("closingPriceHistory") or [])
            latest_limit = at_or_before(limits_payload.get("bestLimitsHistory") or [])

            rows.append({
                "identity": {
                    "instrument_id": ins_code,
                    "symbol": symbol,
                    "contract_type": item.get("contract_type"),
                    "underlying_id": item.get("underlying_id"),
                    "underlying_symbol": item.get("underlying_symbol"),
                    "strike": item.get("strike"),
                    "begin_date": item.get("begin_date"),
                    "end_date": item.get("end_date"),
                    "remaining_days": item.get("remaining_days"),
                    "contract_size": item.get("contract_size"),
                },
                "observation": {
                    "date": target_date,
                    "requested_through": target_time,
                    "closing": closing,
                    "best_limits": latest_limit,
                },
                "evidence": {
                    "source": "TSETMC",
                    "closing_history_endpoint": closing_url,
                    "closing_history_sha256": closing_sha,
                    "best_limits_history_endpoint": limits_url,
                    "best_limits_history_sha256": limits_sha,
                },
            })
        except Exception as exc:
            rows.append({
                "identity": {
                    "instrument_id": ins_code,
                    "symbol": symbol,
                    "contract_type": item.get("contract_type"),
                    "underlying_id": item.get("underlying_id"),
                    "underlying_symbol": item.get("underlying_symbol"),
                    "strike": item.get("strike"),
                    "begin_date": item.get("begin_date"),
                    "end_date": item.get("end_date"),
                    "remaining_days": item.get("remaining_days"),
                    "contract_size": item.get("contract_size"),
                },
                "status": "INSUFFICIENT",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_through": target_time,
        "rows": rows,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    p.add_argument("--start", default="090100")
    p.add_argument("--end", default="123000")
    p.add_argument("--interval-seconds", type=int, default=60)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    adapter = TSETMCAdapter()
    universe = adapter.option_market_watch_universe()
    observations = []
    start_h = int(args.start)
    end_h = int(args.end)

    while True:
        now = datetime.now().astimezone()
        hhmmss = int(now.strftime("%H%M%S"))
        if hhmmss < start_h:
            time.sleep(min(args.interval_seconds, 60))
            continue
        if hhmmss > end_h:
            break

        observations.append(capture_once(adapter, universe, args.date, now.strftime("%H%M%S")))
        time.sleep(args.interval_seconds)

    snapshot = {
        "status": "SUCCESS" if observations else "INSUFFICIENT",
        "source_of_truth": "TSETMC",
        "snapshot_type": "LIVE_INTRADAY_WINDOW",
        "target_date": args.date,
        "start_time": args.start,
        "end_time": args.end,
        "selection_rule": "each observation uses the latest explicit TSETMC record at or before capture time",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "universe_source": {
            "endpoint": universe.get("endpoint"),
            "snapshot_sha256": universe.get("snapshot_sha256"),
            "retrieved_at": universe.get("retrieved_at"),
            "record_count": universe.get("record_count"),
        },
        "observation_count": len(observations),
        "observations": observations,
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({
        "status": snapshot["status"],
        "source_of_truth": snapshot["source_of_truth"],
        "target_date": snapshot["target_date"],
        "start_time": snapshot["start_time"],
        "end_time": snapshot["end_time"],
        "observation_count": snapshot["observation_count"],
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "output": str(output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
