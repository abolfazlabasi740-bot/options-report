#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live TSETMC source smoke test; does not modify scoring or runtime state."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path

from tsetmc_adapter import TSETMCAdapter


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

    payload = {
        "status": "SUCCESS",
        "test": test_name,
        "adapter_version": "1.0",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": result.get("source"),
        "endpoint": result.get("endpoint"),
        "snapshot_sha256": result.get("snapshot_sha256"),
        "data_present": result.get("data") is not None,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()