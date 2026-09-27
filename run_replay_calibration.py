#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run historical replay calibration against archived TSETMC snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from signal_replay_engine import build_replay_calibration


def run(root: Path, output: Path) -> dict:
    result = build_replay_calibration(root)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    result["calibration_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    result["output_file"] = str(output)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    root = Path(args.root)
    output = Path(args.output) if args.output else root / "output" / "calibration" / "latest_replay_calibration.json"
    result = run(root, output)
    print("STATUS =", result.get("status"))
    print("ENGINE_VERSION =", result.get("engine_version"))
    print("SOURCE_OF_TRUTH =", result.get("source_of_truth"))
    print("SNAPSHOT_COUNT =", result.get("snapshot_count"))
    print("OBSERVATION_COUNT =", result.get("observation_count"))
    print("RULE_CANDIDATE_COUNT =", result.get("rule_candidate_count"))
    print("SIGNAL_GENERATION =", result.get("rules", {}).get("signal_generation"))
    print("CALIBRATION_SHA256 =", result.get("calibration_sha256"))
    print("OUTPUT_FILE =", result.get("output_file"))


if __name__ == "__main__":
    main()
