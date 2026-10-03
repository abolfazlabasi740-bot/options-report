#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capture a TSETMC historical snapshot at or before a requested market time."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from tsetmc_adapter import TSETMCAdapter

USER_AGENT = "OptimusAI-V4.1-TSETMC-HISTORICAL-SNAPSHOT/1.0"


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
    payload = json.loads(body.decode("utf-8", errors="replace"))
    return payload, hashlib.sha256(body).hexdigest()


def choose_latest(rows: list[dict], target_h_even: int) -> dict | None:
    valid = [
        row for row in rows
        if isinstance(row, dict)
        and row.get("hEven") is not None
        and int(row["hEven"]) <= target_h_even
    ]
    if not valid:
        return None
    return max(valid, key=lambda row: int(row["hEven"]))


def capture_historical(
    target_date: str,
    target_time: str,
    output: Path,
    symbol_prefix: str | None = None,
) -> dict:
    if len(target_date) != 8 or not target_date.isdigit():
        raise ValueError("target_date must be YYYYMMDD")
    if len(target_time) != 6 or not target_time.isdigit():
        raise ValueError("target_time must be HHMMSS")

    target_h_even = int(target_time)
    adapter = TSETMCAdapter()
    universe = adapter.option_market_watch_universe()

    records = []
    seen = set()

    for item in universe.get("records", []):
        ins_code = str(item.get("instrument_id") or "").strip()
        symbol = str(item.get("symbol") or "").strip()
        if not ins_code or ins_code in seen:
            continue
        if symbol_prefix and not symbol.startswith(symbol_prefix):
            continue
        seen.add(ins_code)

        closing_url = (
            f"{adapter.base_url}/ClosingPrice/GetClosingPriceHistory/"
            f"{ins_code}/{target_date}"
        )
        limits_url = (
            f"{adapter.base_url}/BestLimits/{ins_code}/{target_date}"
        )

        try:
            closing_payload, closing_sha = request_json(closing_url)
            closing_rows = closing_payload.get("closingPriceHistory") or []
            closing = choose_latest(closing_rows, target_h_even)

            limits_payload, limits_sha = request_json(limits_url)
            limits_rows = limits_payload.get("bestLimitsHistory") or []
            limits = [
                row for row in limits_rows
                if isinstance(row, dict)
                and row.get("hEven") is not None
                and int(row["hEven"]) <= target_h_even
            ]
            latest_limits_time = max(
                (int(row["hEven"]) for row in limits),
                default=None,
            )
            latest_limits = [
                row for row in limits
                if int(row["hEven"]) == latest_limits_time
            ] if latest_limits_time is not None else []

            records.append({
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
                "target": {
                    "date": target_date,
                    "time": target_time,
                },
                "closing_price_observation": closing,
                "best_limits_observation": latest_limits,
                "evidence": {
                    "source": "TSETMC",
                    "closing_history_endpoint": closing_url,
                    "closing_history_sha256": closing_sha,
                    "best_limits_history_endpoint": limits_url,
                    "best_limits_history_sha256": limits_sha,
                    "selection_rule": "latest explicit observation at or before target time",
                },
            })
        except Exception as exc:
            records.append({
                "identity": {
                    "instrument_id": ins_code,
                    "symbol": symbol,
                    "contract_type": item.get("contract_type"),
                    "underlying_id": item.get("underlying_id"),
                    "underlying_symbol": item.get("underlying_symbol"),
                    "strike": item.get("strike"),
                    "begin_date": item.get("begin_date"),
                    "end_date": item.get("end_date"),
                    "contract_size": item.get("contract_size"),
                },
                "target": {"date": target_date, "time": target_time},
                "status": "INSUFFICIENT",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

    snapshot = {
        "status": "SUCCESS",
        "source_of_truth": "TSETMC",
        "snapshot_type": "HISTORICAL_INTRADAY",
        "target_date": target_date,
        "target_time": target_time,
        "selection_rule": "latest explicit TSETMC observation at or before target time",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "universe_source": {
            "endpoint": universe.get("endpoint"),
            "snapshot_sha256": universe.get("snapshot_sha256"),
            "retrieved_at": universe.get("retrieved_at"),
            "record_count": universe.get("record_count"),
        },
        "row_count": len(records),
        "rows": records,
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--time", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--symbol-prefix", default=None)
    args = parser.parse_args()

    snapshot = capture_historical(
        target_date=args.date,
        target_time=args.time,
        output=Path(args.output),
        symbol_prefix=args.symbol_prefix,
    )
    print(json.dumps({
        "status": snapshot["status"],
        "source_of_truth": snapshot["source_of_truth"],
        "target_date": snapshot["target_date"],
        "target_time": snapshot["target_time"],
        "row_count": snapshot["row_count"],
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "output": args.output,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
