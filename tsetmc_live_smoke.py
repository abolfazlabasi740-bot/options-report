#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live TSETMC source smoke test; does not modify scoring or runtime state."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path

from tsetmc_adapter import TSETMCAdapter


def _explicit_ins_codes(value):
    """Collect only explicitly returned insCode/instrument_id fields; never infer from symbols."""
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"insCode", "InsCode", "instrument_id", "InstrumentID"} and item not in (None, ""):
                found.append(str(item))
            found.extend(_explicit_ins_codes(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_explicit_ins_codes(item))
    return list(dict.fromkeys(found))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("output/tsetmc_live_smoke.json"))
    parser.add_argument("--flow", type=int, default=0)
    parser.add_argument("--option-market-watch", action="store_true")
    args = parser.parse_args()

    adapter = TSETMCAdapter()
    if args.option_market_watch:
        result = adapter.option_market_watch(flow=args.flow)
        test_name = "TSETMC_OPTION_MARKET_WATCH"
    else:
        result = adapter.market_overview(flow=args.flow)
        test_name = "TSETMC_MARKET_OVERVIEW"

    raw_evidence_path = args.output.with_suffix(".raw.json")
    raw_evidence_path.write_text(
        json.dumps(result.get("data"), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    explicit_ins_codes = _explicit_ins_codes(result.get("data"))

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
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()