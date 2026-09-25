#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run G7-2 sensitivity over real saved TSETMC JSON snapshots only."""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
from pathlib import Path
from typing import Any

from historical_sensitivity_audit import pair_stability, run_snapshot


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_snapshot(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("SNAPSHOT_MUST_BE_OBJECT")
    return data


def run_file(path: Path, top_n: int) -> dict[str, Any]:
    file_sha = sha256_file(path)
    snapshot = load_snapshot(path)
    result = run_snapshot(snapshot, top_n=top_n)
    result["file"] = str(path)
    result["file_sha256"] = file_sha
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_glob", help="Glob for real saved TSETMC JSON snapshots")
    ap.add_argument("--output", default="output/g7_2_historical_sensitivity_evidence.json")
    ap.add_argument("--top-n", type=int, default=15)
    args = ap.parse_args()

    paths = [Path(p) for p in sorted(glob.glob(args.input_glob)) if Path(p).is_file()]
    if not paths:
        raise SystemExit("NO_HISTORICAL_TSETMC_SNAPSHOTS_MATCHED")

    results = []
    failures = []
    for path in paths:
        try:
            results.append(run_file(path, args.top_n))
        except Exception as exc:
            failures.append({
                "file": str(path),
                "file_sha256": sha256_file(path),
                "status": "UNRESOLVED",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

    output = {
        "engine_version": "G7-2-TSETMC-DATASET-RUNNER-1.0",
        "audit": "G7-2_HISTORICAL_DATASET_RUNNER",
        "status": "EVIDENCE_ONLY",
        "production_mutation": False,
        "source_of_truth": "TSETMC",
        "top_n": args.top_n,
        "files_processed": len(results),
        "files_unresolved": len(failures),
        "snapshots": results,
        "unresolved": failures,
        "pair_stability": pair_stability(results),
    }
    output["evidence_hash"] = hashlib.sha256(
        json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "files_processed": len(results),
        "files_unresolved": len(failures),
        "output": str(out),
        "evidence_hash": output["evidence_hash"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
