#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a real TSETMC-only BestLimits evidence package.

This runner is deliberately fail-closed:
- discovers option/underlying identities from the live TSETMC option Market-Watch;
- captures BestLimits twice for each selected instrument;
- preserves raw payloads and hashes;
- never translates zo/zd/pd/po/qd/qo;
- never enables scoring or ranking.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from bestlimits_evidence_gate import validate_package
from live_capture_harness import capture
from tsetmc_first_source import build_tsetmc_snapshot


def build_package(*, option_count: int, pause_seconds: float, timeout: float, base_url: str) -> dict:
    snapshot = build_tsetmc_snapshot(flow=1, max_instruments=max(option_count * 3, option_count))
    rows = snapshot.get("rows", [])

    selected = []
    seen = set()
    for row in rows:
        identity = row.get("identity", {})
        iid = str(identity.get("instrument_id") or "").strip()
        uid = str(identity.get("underlying_id") or "").strip()
        if not iid or not uid or iid in seen:
            continue
        seen.add(iid)
        selected.append((iid, uid))
        if len(selected) >= option_count:
            break

    if len(selected) < option_count:
        raise RuntimeError("TSETMC did not provide enough explicit option/underlying identities")

    roles = {}
    for option_id, underlying_id in selected:
        roles[option_id] = ["option"]
        roles[underlying_id] = ["underlying"]

    captures = []
    for round_no in range(2):
        for option_id, underlying_id in selected:
            captures.append(capture(option_id, base_url, timeout))
            captures.append(capture(underlying_id, base_url, timeout))
        if round_no == 0 and pause_seconds > 0:
            time.sleep(pause_seconds)

    package = {
        "schema_version": "BESTLIMITS_LIVE_EVIDENCE_PACKAGE_V1",
        "source_of_truth": "TSETMC",
        "generated_from_snapshot_sha256": snapshot.get("snapshot_sha256"),
        "instrument_roles": roles,
        "captures": captures,
        "independent_semantic_evidence": [],
        "semantic_mapping_status": "OPEN",
        "scoring_status": "BLOCKED",
        "governance": {
            "optionschool_dependency": False,
            "semantic_translation_performed": False,
            "production_scoring_enabled": False,
        },
    }
    return package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--option-count", type=int, default=3)
    parser.add_argument("--pause-seconds", type=float, default=3.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--base-url", default="https://cdn.tsetmc.com/api")
    args = parser.parse_args()

    if args.option_count < 3:
        raise ValueError("--option-count must be at least 3")

    package = build_package(
        option_count=args.option_count,
        pause_seconds=args.pause_seconds,
        timeout=args.timeout,
        base_url=args.base_url,
    )
    result = validate_package(package)
    package["gate_result"] = result

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(package, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "SUCCESS",
        "gate_status": result["status"],
        "capture_count": result["capture_count"],
        "option_instruments": result["option_instruments"],
        "underlying_instruments": result["underlying_instruments"],
        "semantic_mapping_status": "OPEN",
        "scoring_status": "BLOCKED",
        "output": str(args.output),
    }, ensure_ascii=False))
    return 0 if result["status"] in {"READY_FOR_REVIEW", "INCOMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
