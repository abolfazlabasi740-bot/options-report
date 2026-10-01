#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build reproducible G7-5 economic validation evidence from retained TSETMC archives."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import economic_scoring_engine as scoring
import tsetmc_outcome_engine as outcomes
import economic_validation_engine as validation

ENGINE_VERSION = "G7-5-ECONOMIC-EVIDENCE-1.1"
SOURCE_OF_TRUTH = "TSETMC"


def _write_progress(root: Path, stage: str, **extra: Any) -> None:
    payload = {
        "engine_version": ENGINE_VERSION,
        "status": "RUNNING",
        "stage": stage,
        "updated_at_epoch": time.time(),
        **extra,
    }
    out = root / "output" / "g7_5_economic_validation_progress.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _archives(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "output" / "history" / "tsetmc").glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sha = payload.get("snapshot_sha256")
        if payload.get("source_of_truth") == SOURCE_OF_TRUTH and sha and isinstance(payload.get("rows"), list):
            result[str(sha)] = payload
    return result


def _feature_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = snapshot.get("rows") or []
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        instrument_id = str((row.get("identity") or {}).get("instrument_id") or "").strip()
        if instrument_id:
            result[instrument_id] = scoring._derived(row)
    return result


def build_evidence(root: Path) -> dict[str, Any]:
    _write_progress(root, "LOAD_ARCHIVES")
    archives = _archives(root)
    _write_progress(root, "LOAD_OBSERVED_OUTCOMES", snapshot_count=len(archives))
    observed = outcomes.build_observed_outcomes(root)

    _write_progress(root, "DERIVE_FEATURES", transition_count=observed.get("transition_count", 0))
    indexes = {}
    for n, (sha, snapshot) in enumerate(archives.items(), 1):
        indexes[sha] = _feature_index(snapshot)
        if n == 1 or n % 5 == 0 or n == len(archives):
            _write_progress(root, "DERIVE_FEATURES", snapshot_done=n, snapshot_count=len(archives))

    observations: list[dict[str, Any]] = []
    unresolved = 0
    matched = 0
    for transition in observed.get("transitions", []):
        entry_sha = transition.get("entry_snapshot_sha256")
        instrument_id = str(transition.get("instrument_id") or "")
        features = indexes.get(str(entry_sha), {}).get(instrument_id)
        if not features:
            unresolved += 1
            continue
        matched += 1
        change = transition.get("option_change_pct")
        observations.append({
            "entry_observation_time": transition.get("entry_observation_time"),
            "instrument_id": instrument_id,
            "symbol": transition.get("symbol"),
            "contract_type": transition.get("contract_type"),
            "entry_snapshot_sha256": entry_sha,
            "forward_snapshot_sha256": transition.get("forward_snapshot_sha256"),
            "option_return_pct": change,
            "entry_features": features,
            "outcome_label": (
                "OBSERVED_CONFIRMED" if change is not None and change > 0
                else "OBSERVED_NOT_CONFIRMED" if change is not None
                else "UNRESOLVED"
            ),
            "label_provenance": "OBSERVED_FORWARD_TSETMC_OPTION_RETURN",
        })

    _write_progress(root, "WALK_FORWARD_VALIDATION", matched_transition_count=matched, unresolved_feature_matches=unresolved)
    validation_result = validation.validate_walk_forward(observations)

    source_files = sorted(
        str((root / "output" / "history" / "tsetmc" / f"{sha}.json").resolve())
        for sha in archives
    )
    evidence_payload = {
        "status": "EVIDENCE_ONLY",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": SOURCE_OF_TRUTH,
        "source_file_count": len(source_files),
        "source_snapshot_count": len(archives),
        "source_snapshot_shas": sorted(archives),
        "source_files": source_files,
        "observed_outcome_engine_version": observed.get("engine_version"),
        "observed_transition_count": observed.get("transition_count", 0),
        "matched_transition_count": matched,
        "unresolved_feature_matches": unresolved,
        "observation_count": len(observations),
        "validation": validation_result,
        "label_contract": {
            "independent_of_score": True,
            "source": "NEXT_RETAINED_TSETMC_SNAPSHOT",
            "matching": "EXACT_INSTRUMENT_ID_ONLY",
            "positive": "OBSERVED_FORWARD_OPTION_RETURN_GT_ZERO",
            "non_positive": "OBSERVED_FORWARD_OPTION_RETURN_LE_ZERO",
            "missing_return": "UNRESOLVED",
            "synthetic_labels": "FORBIDDEN",
        },
        "closure": {
            "g7_5_status": "OPEN",
            "reason": "Validation evidence exists, but the frozen protocol requires closure by case family with explicit confusion counts and the current economic engine does not map its features to the frozen Opportunity Shadow case-family definitions.",
            "production_signal_authorization": "FORBIDDEN",
        },
    }
    canonical = json.dumps(evidence_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    evidence_payload["evidence_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    _write_progress(root, "WRITE_EVIDENCE", validation_result_count=validation_result["result_count"])
    return evidence_payload


if __name__ == "__main__":
    root = Path(".")
    try:
        result = build_evidence(root)
        out = root / "output" / "g7_5_economic_validation_evidence.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_progress(root, "COMPLETE", status="COMPLETE", evidence_sha256=result["evidence_sha256"])
        print("STATUS=", result["status"])
        print("SNAPSHOTS=", result["source_snapshot_count"])
        print("TRANSITIONS=", result["observed_transition_count"])
        print("MATCHED=", result["matched_transition_count"])
        print("UNRESOLVED=", result["unresolved_feature_matches"])
        print("VALIDATION_WINDOWS=", result["validation"]["validation_window_count"])
        print("VALIDATION_RESULTS=", result["validation"]["result_count"])
        print("G7_5_STATUS=", result["closure"]["g7_5_status"])
        print("EVIDENCE_SHA256=", result["evidence_sha256"])
    except Exception as exc:
        _write_progress(root, "FAILED", error_type=type(exc).__name__, error=str(exc))
        raise
