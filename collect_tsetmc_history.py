#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot TSETMC historical observation collector for OptimusAI V4.1."""
from __future__ import annotations

import argparse
from pathlib import Path

from tsetmc_first_source import build_tsetmc_snapshot
from tsetmc_history import archive_universe_snapshot

ROOT = Path(__file__).resolve().parent
ENGINE_VERSION = "TSETMC-HISTORY-COLLECTOR-1.0"


def collect_once(root: Path = ROOT) -> dict:
    snapshot = build_tsetmc_snapshot(
        flow=None,
        max_instruments=None,
        symbol_prefix=None,
    )
    if snapshot.get("source_of_truth") != "TSETMC":
        raise RuntimeError("SOURCE_OF_TRUTH_NOT_TSETMC")
    rows = list(snapshot.get("rows") or [])
    if not rows:
        raise RuntimeError("TSETMC_UNIVERSE_EMPTY")

    snapshot["universe_rows"] = rows
    snapshot["universe_row_count"] = len(rows)
    path = archive_universe_snapshot(snapshot, root)
    if path is None:
        raise RuntimeError("HISTORY_ARCHIVE_FAILED")

    evidence = snapshot.get("evidence") or {}
    market_watch = evidence.get("market_watch") or {}
    return {
        "status": "PASS",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": "TSETMC",
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "row_count": len(rows),
        "observation_retrieved_at": market_watch.get("retrieved_at"),
        "market_watch_snapshot_sha256": market_watch.get("snapshot_sha256"),
        "archive_file": str(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    result = collect_once(Path(args.root))
    for key, value in result.items():
        print(f"{key.upper()} = {value}")


if __name__ == "__main__":
    main()
