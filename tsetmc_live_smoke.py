#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live TSETMC source smoke test; does not modify scoring or runtime state."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path

from tsetmc_adapter import TSETMCAdapter


def _explicit_instrument_evidence(value):
    """Collect only explicit option/underlying IDs returned by the source; never infer identity."""
    option_records = []
    explicit_ids = []
    if isinstance(value, dict):
        if "insCode_P" in value or "insCode_C" in value:
            record = {
                "insCode_P": str(value["insCode_P"]) if value.get("insCode_P") not in (None, "") else None,
                "insCode_C": str(value["insCode_C"]) if value.get("insCode_C") not in (None, "") else None,
                "uaInsCode": str(value["uaInsCode"]) if value.get("uaInsCode") not in (None, "") else None,
            }
            option_records.append(record)
            explicit_ids.extend(v for v in (
                record["insCode_P"], record["insCode_C"], record["uaInsCode"]
            ) if v)
        for key, item in value.items():
            if key in {
                "insCode", "InsCode", "instrument_id", "InstrumentID",
                "insCode_P", "insCode_C", "uaInsCode"
            } and item not in (None, ""):
                explicit_ids.append(str(item))
            nested = _explicit_instrument_evidence(item)
            explicit_ids.extend(nested["explicit_ids"])
            option_records.extend(nested["option_records"])
    elif isinstance(value, list):
        for item in value:
            nested = _explicit_instrument_evidence(item)
            explicit_ids.extend(nested["explicit_ids"])
            option_records.extend(nested["option_records"])
    return {
        "explicit_ids": list(dict.fromkeys(explicit_ids)),
        "option_records": option_records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("output/tsetmc_live_smoke.json"))
    parser.add_argument("--flow", type=int, default=0)
    parser.add_argument("--option-market-watch", action="store_true")
    parser.add_argument("--allow-network-unavailable", action="store_true")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--retries", type=int, default=0)
    args = parser.parse_args()

    adapter = TSETMCAdapter(timeout=args.timeout, retries=args.retries)
    try:
        if args.option_market_watch:
            result = adapter.option_market_watch(flow=args.flow)
            test_name = "TSETMC_OPTION_MARKET_WATCH"
        else:
            result = adapter.market_overview(flow=args.flow)
            test_name = "TSETMC_MARKET_OVERVIEW"
    except Exception as exc:
        if not args.allow_network_unavailable:
            raise
        payload = {
            "status": "NETWORK_UNAVAILABLE",
            "test": "TSETMC_OPTION_MARKET_WATCH" if args.option_market_watch else "TSETMC_MARKET_OVERVIEW",
            "adapter_version": "1.0",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "TSETMC",
            "data_present": False,
            "network_error": type(exc).__name__,
            "network_error_message": str(exc),
            "explicit_ins_code_count": 0,
            "explicit_ins_codes": [],
            "explicit_option_record_count": 0,
            "explicit_option_records": [],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        args.output.with_suffix(".raw.json").write_text(json.dumps({"status": "NETWORK_UNAVAILABLE"}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    raw_evidence_path = args.output.with_suffix(".raw.json")
    raw_evidence_path.write_text(
        json.dumps(result.get("data"), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    evidence = _explicit_instrument_evidence(result.get("data"))
    explicit_ins_codes = evidence["explicit_ids"]
    option_records = evidence["option_records"]

    payload = {
        "status": "SUCCESS",
        "test": test_name,
        "adapter_version": "1.0",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": result.get("source"),
        "endpoint": result.get("endpoint"),
        "snapshot_sha256": result.get("snapshot_sha256"),
        "data_present": result.get("data") is not None,
        "raw_evidence_file": raw_evidence_path.name,
        "explicit_ins_code_count": len(explicit_ins_codes),
        "explicit_ins_codes": explicit_ins_codes,
        "explicit_option_record_count": len(option_records),
        "explicit_option_records": option_records,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
