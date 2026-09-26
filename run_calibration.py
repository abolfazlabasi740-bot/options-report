#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run evidence-only calibration against the latest audited TSETMC ranking."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from calibration_engine import calibrate_candidates, CALIBRATION_ENGINE_VERSION

ROOT = Path(__file__).resolve().parent


def run_calibration(audit_path: Path, output_path: Path) -> dict:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    integrity = audit.get("audit_integrity") or {}
    if integrity.get("status") != "PASS":
        raise RuntimeError("AUDIT_NOT_PASS")
    if audit.get("source_of_truth") != "TSETMC":
        raise RuntimeError("SOURCE_OF_TRUTH_NOT_TSETMC")
    ranking = audit.get("ranking") or {}
    rows = ranking.get("ranking_rows") or []
    if not rows:
        raise RuntimeError("NO_RANKING_EVIDENCE_ROWS")

    candidates = [
        {
            "instrument_id": row.get("instrument_id"),
            "symbol": row.get("symbol"),
            "contract_type": row.get("contract_type"),
            "rank": row.get("rank"),
            "score": row.get("score"),
            "evidence": {
                "features": row.get("features") or {},
                "supported_blocks": row.get("supported_blocks") or [],
            },
        }
        for row in rows
    ]
    result = calibrate_candidates(candidates)
    result.update({
        "source_of_truth": "TSETMC",
        "source_snapshot_sha256": audit.get("snapshot_sha256"),
        "source_generated_at": audit.get("generated_at"),
        "source_row_count": audit.get("row_count"),
        "ranking_evidence_row_count": len(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_status": "SHADOW_ONLY",
        "signal_generation": "FORBIDDEN",
    })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    output_path.write_text(payload, encoding="utf-8")
    result["calibration_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", default=str(ROOT / "output" / "latest_audit.json"))
    parser.add_argument(
        "--output",
        default=str(ROOT / "output" / "calibration" / "latest_calibration.json"),
    )
    args = parser.parse_args()
    result = run_calibration(Path(args.audit), Path(args.output))
    print("CALIBRATION_STATUS =", result["status"])
    print("CALIBRATION_ENGINE_VERSION =", result["engine_version"])
    print("SOURCE_OF_TRUTH =", result["source_of_truth"])
    print("SOURCE_SNAPSHOT_SHA256 =", result["source_snapshot_sha256"])
    print("RANKING_EVIDENCE_ROWS =", result["ranking_evidence_row_count"])
    print("CALIBRATION_FILE =", args.output)
    print("CALIBRATION_SHA256 =", result["calibration_sha256"])
    print("SIGNAL_GENERATION =", result["signal_generation"])


if __name__ == "__main__":
    main()
