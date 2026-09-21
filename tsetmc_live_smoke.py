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
    args = parser.parse_args()

    adapter = TSETMCAdapter()
    result = adapter.market_overview(flow=0)

    payload = {
        "status": "SUCCESS",
        "test": "TSETMC_MARKET_OVERVIEW",
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