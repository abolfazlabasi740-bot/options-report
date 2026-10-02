#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build reproducible G7-5 evidence and TSETMC-supported case-family diagnostics."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import economic_scoring_engine as scoring
import tsetmc_outcome_engine as outcomes
import economic_validation_engine as validation

ENGINE_VERSION = "G7-5-ECONOMIC-EVIDENCE-1.3"
CASE_MAPPING_VERSION = "G7-5-TSETMC-CASE-MAP-1.1"
SOURCE_OF_TRUTH = "TSETMC"
UNAVAILABLE = "داده موجود نیست"


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        result = float(value)
        return result if result == result and abs(result) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _percentile(values: list[float], fraction: float) -> float | None:
    clean = sorted(x for x in values if _num(x) is not None)
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    position = (len(clean) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(clean) - 1)
    return clean[lower] + (clean[upper] - clean[lower]) * (position - lower)


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
    chain_members: dict[tuple[str, str, float], set[str]] = {}
    for row in rows:
        identity = row.get("identity") or {}
        canonical = row.get("canonical") or {}
        instrument_id = str(identity.get("instrument_id") or "").strip()
        if not instrument_id:
            continue
        features = scoring._derived(row)
        underlying_id = str(identity.get("underlying_id") or "").strip()
        expiry = str(canonical.get("تاریخ سررسید") or identity.get("end_date") or "").strip()
        strike = _num(canonical.get("قیمت اعمال"))
        contract_type = str(identity.get("contract_type") or "").upper()
        features.update({
            "underlying_id": underlying_id or None,
            "underlying_symbol": identity.get("underlying_symbol"),
            "expiry": expiry or None,
            "strike": strike,
            "underlying_price": _num(canonical.get("قیمت سهم پایه")),
            "option_last": _num(canonical.get("آخرین قیمت")),
            "bid_price": _num(canonical.get("قیمت بهترین تقاضا")),
            "ask_price": _num(canonical.get("قیمت بهترین عرضه")),
            "bid_volume": _num(canonical.get("حجم بهترین تقاضا")),
            "ask_volume": _num(canonical.get("حجم بهترین عرضه")),
            "contract_type": contract_type or features.get("contract_type"),
            "base_breakeven_context_available": all(
                _num(v) is not None for v in (
                    canonical.get("قیمت سهم پایه"),
                    canonical.get("قیمت اعمال"),
                    canonical.get("آخرین قیمت"),
                )
            ),
            "call_put_pair_available": False,
        })
        result[instrument_id] = features
        if underlying_id and expiry and strike is not None and contract_type in {"CALL", "PUT"}:
            key = (underlying_id, expiry, strike)
            chain_members.setdefault(key, set()).add(contract_type)

    paired = {
        key for key, types in chain_members.items()
        if {"CALL", "PUT"}.issubset(types)
    }
    for row in rows:
        identity = row.get("identity") or {}
        canonical = row.get("canonical") or {}
        instrument_id = str(identity.get("instrument_id") or "").strip()
        if instrument_id not in result:
            continue
        underlying_id = str(identity.get("underlying_id") or "").strip()
        expiry = str(canonical.get("تاریخ سررسید") or identity.get("end_date") or "").strip()
        strike = _num(canonical.get("قیمت اعمال"))
        if underlying_id and expiry and strike is not None:
            result[instrument_id]["call_put_pair_available"] = (
                underlying_id, expiry, strike
            ) in paired
    return result


def _case_family_diagnostics(observations: list[dict[str, Any]]) -> dict[str, Any]:
    by_snapshot: dict[str, list[dict[str, Any]]] = {}
    for row in observations:
        key = str(row.get("entry_snapshot_sha256") or "")
        by_snapshot.setdefault(key, []).append(row)

    definitions = {
        "BREAKEVEN_COMPRESSION_TSETMC_PROXY": {
            "feature": "breakeven_distance",
            "direction": "LE_P25",
            "description": "Cross-sectional lowest quartile of option-derived breakeven distance; not an expected-return claim.",
        },
        "LIQUIDITY_CONFIRMED_TSETMC_PROXY": {
            "feature": "trade_value_and_volume",
            "direction": "GE_P75_BOTH",
            "description": "Both trade value and volume at or above their entry-snapshot P75.",
        },
        "NEAR_EXPIRY_RISK_TSETMC": {
            "feature": "calendar_days",
            "direction": "LE_P25",
            "description": "Cross-sectional lowest quartile of remaining calendar days; risk flag only.",
        },
    }

    family_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in definitions}
    coverage = {
        "BASE_BREAKEVEN_CONTEXT_TSETMC": {"available": 0, "missing": 0},
        "CALL_PUT_STRUCTURE_AVAILABLE_TSETMC": {"paired": 0, "not_paired_or_missing": 0},
    }

    for snapshot_sha, rows in by_snapshot.items():
        breakeven_values = [
            _num((r.get("entry_features") or {}).get("breakeven_distance")) for r in rows
        ]
        liquidity_values = [
            _num((r.get("entry_features") or {}).get("trade_value")) for r in rows
        ]
        volume_values = [
            _num((r.get("entry_features") or {}).get("volume")) for r in rows
        ]
        days_values = [
            _num((r.get("entry_features") or {}).get("calendar_days")) for r in rows
        ]
        leverage_values = [
            _num((r.get("entry_features") or {}).get("leverage_efficiency")) for r in rows
        ]
        be_p25 = _percentile([x for x in breakeven_values if x is not None], 0.25)
        leverage_p75 = _percentile([x for x in leverage_values if x is not None], 0.75)
        value_p75 = _percentile([x for x in liquidity_values if x is not None], 0.75)
        volume_p75 = _percentile([x for x in volume_values if x is not None], 0.75)
        days_p25 = _percentile([x for x in days_values if x is not None], 0.25)

        for row in rows:
            features = row.get("entry_features") or {}
            be = _num(features.get("breakeven_distance"))
            value = _num(features.get("trade_value"))
            volume = _num(features.get("volume"))
            days = _num(features.get("calendar_days"))
            leverage = _num(features.get("leverage_efficiency"))
            family_rows["BREAKEVEN_COMPRESSION_TSETMC_PROXY"].append({
                **row, "case_triggered": be is not None and be_p25 is not None and be <= be_p25,
                "case_evaluable": be is not None and be_p25 is not None,
            })
            family_rows["LIQUIDITY_CONFIRMED_TSETMC_PROXY"].append({
                **row, "case_triggered": (
                    value is not None and volume is not None
                    and value_p75 is not None and volume_p75 is not None
                    and value >= value_p75 and volume >= volume_p75
                ),
                "case_evaluable": (
                    value is not None and volume is not None
                    and value_p75 is not None and volume_p75 is not None
                ),
            })
            family_rows["NEAR_EXPIRY_RISK_TSETMC"].append({
                **row, "case_triggered": days is not None and days_p25 is not None and days <= days_p25,
                "case_evaluable": days is not None and days_p25 is not None,
            })

            if features.get("base_breakeven_context_available"):
                coverage["BASE_BREAKEVEN_CONTEXT_TSETMC"]["available"] += 1
            else:
                coverage["BASE_BREAKEVEN_CONTEXT_TSETMC"]["missing"] += 1
            if features.get("call_put_pair_available"):
                coverage["CALL_PUT_STRUCTURE_AVAILABLE_TSETMC"]["paired"] += 1
            else:
                coverage["CALL_PUT_STRUCTURE_AVAILABLE_TSETMC"]["not_paired_or_missing"] += 1

    metrics = {}
    for family, rows in family_rows.items():
        evaluable = [
            r for r in rows
            if r.get("case_evaluable") and r.get("outcome_label") != "UNRESOLVED"
        ]
        tp = sum(1 for r in evaluable if r.get("case_triggered") and r.get("outcome_label") == "OBSERVED_CONFIRMED")
        fp = sum(1 for r in evaluable if r.get("case_triggered") and r.get("outcome_label") == "OBSERVED_NOT_CONFIRMED")
        fn = sum(1 for r in evaluable if not r.get("case_triggered") and r.get("outcome_label") == "OBSERVED_CONFIRMED")
        tn = sum(1 for r in evaluable if not r.get("case_triggered") and r.get("outcome_label") == "OBSERVED_NOT_CONFIRMED")
        unresolved = len(rows) - len(evaluable)
        metrics[family] = {
            "definition": definitions[family],
            "observed_rows": len(rows),
            "evaluable_rows": len(evaluable),
            "unresolved_rows": unresolved,
            "confusion_counts": {"TP": tp, "FP": fp, "FN": fn, "TN": tn},
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "label": "NEXT_RETAINED_TSETMC_OPTION_RETURN_GT_ZERO",
            "threshold_source": "ENTRY_SNAPSHOT_CROSS_SECTIONAL_PERCENTILE",
            "interpretation": "Descriptive research diagnostic only; not a production signal or proof of causality.",
        }

    return {
        "mapping_version": CASE_MAPPING_VERSION,
        "status": "PARTIAL",
        "supported_case_families": metrics,
        "coverage_only_families": coverage,
        "deferred_case_families": {
            "RELATIVE_VALUE_ANOMALY": {
                "status": "DEFERRED_NONBLOCKING",
                "replacement": "RELATIVE_VALUE_TSETMC_PROXY",
                "reason": "Theoretical Black-Scholes/IV anomaly variant is deferred because those source fields are not retained by TSETMC. The project uses the TSETMC-native breakeven/leverage proxy instead.",
            },
            "CHAIN_STRUCTURE_ANOMALY": {
                "status": "DEFERRED_NONBLOCKING",
                "reason": "No independently validated anomaly rule is required for the current approved release; CALL/PUT pairing remains a coverage diagnostic.",
            },
        },
        "unsupported_case_families": {},
        "global_closure": (
            "VERIFIED"
            if metrics
            and all(
                details["evaluable_rows"] > 0 and details["unresolved_rows"] == 0
                for details in metrics.values()
            )
            else "OPEN"
        ),
        "reason": (
            "G7-5 closure is based on independently observed forward TSETMC outcomes for supported native proxy families. "
            "Theoretical Black-Scholes relative-value and chain-anomaly variants are explicitly deferred and nonblocking for this release; "
            "production BUY/SELL remains forbidden."
            if metrics
            and all(
                details["evaluable_rows"] > 0 and details["unresolved_rows"] == 0
                for details in metrics.values()
            )
            else "G7-5 remains OPEN because retained forward observations are absent or at least one supported family is not fully evaluable."
        ),
    }


def build_evidence(root: Path) -> dict[str, Any]:
    _write_progress(root, "LOAD_ARCHIVES")
    archives = _archives(root)
    # Reuse unchanged verified evidence so the Finisher does not replay the
    # full retained transition set on every cycle.
    existing_path = root / "output" / "g7_5_economic_validation_evidence.json"
    if existing_path.exists():
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
            if (
                existing.get("status") == "EVIDENCE_ONLY"
                and existing.get("closure", {}).get("g7_5_status") == "VERIFIED"
                and sorted(existing.get("source_snapshot_shas") or []) == sorted(archives)
                and int(existing.get("unresolved_feature_matches") or 0) == 0
            ):
                _write_progress(
                    root,
                    "REUSED_EXISTING_EVIDENCE",
                    snapshot_count=len(archives),
                    evidence_sha256=existing.get("evidence_sha256"),
                )
                return existing
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
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
    family_diagnostics = _case_family_diagnostics(observations)

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
        "case_family_diagnostics": family_diagnostics,
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
            "g7_5_status": family_diagnostics["global_closure"],
            "reason": family_diagnostics["reason"],
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
        print("CASE_MAPPING_STATUS=", result["case_family_diagnostics"]["status"])
        for family, details in result["case_family_diagnostics"]["supported_case_families"].items():
            print("CASE_FAMILY=", family, json.dumps(details["confusion_counts"], ensure_ascii=False))
        print("G7_5_STATUS=", result["closure"]["g7_5_status"])
        print("EVIDENCE_SHA256=", result["evidence_sha256"])
    except Exception as exc:
        _write_progress(root, "FAILED", error_type=type(exc).__name__, error=str(exc))
        raise
