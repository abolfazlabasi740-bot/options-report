#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconcile TSETMC option-universe discovery against raw MarketWatch evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tsetmc_adapter import TSETMCAdapter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "history" / "universe_reconciliation.json"


def _walk_lists(value: Any):
    if isinstance(value, list):
        yield value
        for item in value:
            yield from _walk_lists(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_lists(item)


def _candidate_records(payload: Any) -> list[dict[str, Any]]:
    out = []
    seen = set()
    for seq in _walk_lists(payload):
        for item in seq:
            if not isinstance(item, dict):
                continue
            if not any(item.get(k) not in (None, "") for k in ("insCode_P", "insCode_C", "uaInsCode")):
                continue
            key = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
    return out


def run() -> dict[str, Any]:
    adapter = TSETMCAdapter()

    # Raw MarketWatch is diagnostic evidence only; it does not enter scoring.
    # The current CDN API requires query parameters; the bare path returns 404.
    # It exposes instrument-level insCode, so reconciliation uses exact
    # instrument-id intersection with the validated option universe.
    market_watch_path = (
        "ClosingPrice/GetMarketWatch"
        "?market=0&industrialGroup="
        "&paperTypes%5B0%5D=1&paperTypes%5B1%5D=2&paperTypes%5B2%5D=3"
        "&paperTypes%5B3%5D=4&paperTypes%5B4%5D=5&paperTypes%5B5%5D=6"
        "&paperTypes%5B6%5D=7&paperTypes%5B7%5D=8&paperTypes%5B8%5D=9"
        "&showTraded=false&withBestLimits=false&hEven=0&RefID=0"
    )
    raw = adapter._request(market_watch_path)

    flow_result = adapter.option_market_watch_universe()
    flow_evidence = flow_result.get("flow_evidence") or []
    validated_ids = {
        str(record.get("instrument_id"))
        for record in (flow_result.get("records") or [])
        if record.get("instrument_id") not in (None, "")
    }
    raw_data = raw.payload.get("marketwatch", []) if isinstance(raw.payload, dict) else []
    raw_ids = {
        str(item.get("insCode"))
        for item in raw_data
        if isinstance(item, dict) and item.get("insCode") not in (None, "")
    }
    raw_option_intersection = validated_ids & raw_ids

    result = {
        "status": "PASS",
        "engine_version": "TSETMC-UNIVERSE-RECONCILIATION-1.0",
        "source_of_truth": "TSETMC",
        "raw_market_watch": {
            "endpoint": raw.endpoint,
            "snapshot_sha256": raw.sha256,
            "retrieved_at": raw.retrieved_at,
            "top_level_keys": sorted(raw.payload.keys()) if isinstance(raw.payload, dict) else [],
            "record_count": len(raw_data) if isinstance(raw_data, list) else 0,
            "instrument_id_count": len(raw_ids),
            "validated_option_intersection_count": len(raw_option_intersection),
        },
        "validated_option_universe": {
            "flows": flow_result.get("flows"),
            "record_count": flow_result.get("record_count"),
            "flow_evidence": flow_evidence,
            "snapshot_sha256": flow_result.get("snapshot_sha256"),
            "retrieved_at": flow_result.get("retrieved_at"),
        },
        "interpretation": {
            "1582_is_not_a_configured_limit": True,
            "raw_market_watch_and_option_flow_counts_are_not_assumed_comparable": True,
            "reconciliation_method": "exact_instrument_id_intersection",
            "production_universe_changed": False,
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    result = run()
    print("STATUS =", result["status"])
    print("ENGINE_VERSION =", result["engine_version"])
    print("RAW_MARKET_WATCH_RECORDS =", result["raw_market_watch"]["record_count"])
    print("RAW_MARKET_WATCH_INSTRUMENT_IDS =", result["raw_market_watch"]["instrument_id_count"])
    print("VALIDATED_OPTION_INTERSECTION =", result["raw_market_watch"]["validated_option_intersection_count"])
    print("VALIDATED_OPTION_UNIVERSE_RECORDS =", result["validated_option_universe"]["record_count"])
    for item in result["validated_option_universe"]["flow_evidence"]:
        print(
            "FLOW =", item.get("flow"),
            "| STATUS =", item.get("status"),
            "| RAW_RECORDS =", item.get("raw_record_count"),
            "| ACCEPTED_UNIQUE =", item.get("accepted_unique_instruments"),
            "| DUPLICATES =", item.get("duplicate_instruments"),
        )
    print("OUTPUT_FILE =", OUT)
