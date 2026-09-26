#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed audit integrity checks for OptimusAI V4.1 artifacts."""

from __future__ import annotations

from typing import Any

ENGINE_VERSION = "AUDIT-INTEGRITY-1.3"


def verify_audit(audit: dict[str, Any]) -> dict[str, Any]:
    # TSETMC-only report artifacts use a dedicated evidence contract.
    # The retired OptionSchool/shadow requirements must not block them.
    if audit.get("source_of_truth") == "TSETMC" and audit.get("data_mode"):
        required = [
            "audit_version", "source_of_truth", "data_mode", "live_refresh_status",
            "snapshot_sha256", "row_count", "generated_at",
            "live_movement_claim", "scoring_status", "ranking_status",
            "market_watch", "best_limits_evidence", "market_state", "report_sha256",
        ]
        missing = [key for key in required if key not in audit]
        failures = []
        if audit.get("audit_version") != ENGINE_VERSION:
            failures.append("AUDIT_VERSION_INVALID")
        if audit.get("data_mode") not in {"LIVE_TSETMC_REFRESH", "LAST_KNOWN_TSETMC_SNAPSHOT"}:
            failures.append("TSETMC_DATA_MODE_INVALID")
        if audit.get("live_movement_claim") != "NOT_CLAIMED":
            failures.append("LIVE_MOVEMENT_CLAIM_MUST_REMAIN_NOT_CLAIMED")
        if not audit.get("snapshot_sha256"):
            failures.append("SNAPSHOT_HASH_MISSING")
        if not isinstance(audit.get("row_count"), int) or audit.get("row_count") < 0:
            failures.append("ROW_COUNT_INVALID")
        if audit.get("scoring_status") not in {"OFF_FIELD_EVIDENCE_GATE_OPEN", "TSETMC_EVIDENCE_RANKING"}:
            failures.append("SCORING_STATUS_INVALID")
        if audit.get("ranking_status") not in {"OFF", "TSETMC_EVIDENCE_RANKING"}:
            failures.append("RANKING_STATUS_INVALID")
        if not isinstance(audit.get("market_watch"), dict):
            failures.append("MARKET_WATCH_EVIDENCE_INVALID")
        else:
            mw = audit["market_watch"]
            if not mw.get("endpoint") or not mw.get("snapshot_sha256") or not mw.get("retrieved_at"):
                failures.append("MARKET_WATCH_EVIDENCE_INCOMPLETE")
        best = audit.get("best_limits_evidence")
        if not isinstance(best, dict):
            failures.append("BEST_LIMITS_EVIDENCE_INVALID")
        else:
            contract = best.get("contract") or {}
            rows = best.get("rows")
            if contract.get("status") != "RAW_ONLY_QUARANTINED":
                failures.append("BEST_LIMITS_MUST_REMAIN_QUARANTINED")
            if contract.get("source") != "TSETMC":
                failures.append("BEST_LIMITS_SOURCE_INVALID")
            if contract.get("identity_binding") != "instrument_id":
                failures.append("BEST_LIMITS_IDENTITY_BINDING_INVALID")
            if contract.get("market_watch_binding") != "market_watch_snapshot_sha256":
                failures.append("BEST_LIMITS_MARKET_WATCH_BINDING_INVALID")
            if contract.get("source_timestamp_binding") != "source_market_timestamp":
                failures.append("BEST_LIMITS_TIMESTAMP_BINDING_INVALID")
            if contract.get("delta_seconds_limit") != 2.0:
                failures.append("BEST_LIMITS_DELTA_LIMIT_INVALID")
            if contract.get("consumption_status") != "NOT_CONSUMED_BY_SCORING_OR_RANKING":
                failures.append("BEST_LIMITS_CONSUMPTION_INVALID")
            if not isinstance(rows, list):
                failures.append("BEST_LIMITS_ROWS_INVALID")
            else:
                mw_hash = (audit.get("market_watch") or {}).get("snapshot_sha256")
                seen = set()
                for item in rows:
                    if not isinstance(item, dict):
                        failures.append("BEST_LIMITS_ROW_INVALID")
                        continue
                    iid = item.get("instrument_id")
                    if not iid or iid in seen:
                        failures.append("BEST_LIMITS_IDENTITY_DUPLICATE_OR_MISSING")
                    seen.add(iid)
                    if item.get("status") == "NOT_REQUESTED":
                        if item.get("reason") != "AUXILIARY_BEST_LIMITS_DISABLED_BY_DEFAULT":
                            failures.append("BEST_LIMITS_NOT_REQUESTED_REASON_INVALID")
                        if item.get("source") != "TSETMC" or item.get("endpoint") != "BestLimits/{instrument_id}":
                            failures.append("BEST_LIMITS_NOT_REQUESTED_METADATA_INVALID")
                        continue
                    for key in ("endpoint", "snapshot_sha256", "retrieved_at", "market_watch_snapshot_sha256"):
                        if not item.get(key):
                            failures.append("BEST_LIMITS_EVIDENCE_INCOMPLETE")
                    if item.get("market_watch_snapshot_sha256") != mw_hash:
                        failures.append("BEST_LIMITS_MARKET_WATCH_BINDING_MISMATCH")
                    if item.get("status") != "SUCCESS":
                        failures.append("BEST_LIMITS_REQUEST_FAILED")
                    if item.get("delta_status") != "WITHIN_2_SECONDS" or not isinstance(item.get("delta_seconds"), (int, float)):
                        failures.append("BEST_LIMITS_DELTA_NOT_WITHIN_2_SECONDS")
        if not isinstance(audit.get("market_state"), dict):
            failures.append("MARKET_STATE_EVIDENCE_INVALID")
        if not audit.get("report_sha256"):
            failures.append("REPORT_HASH_MISSING")
        status = "PASS" if not missing and not failures else "FAIL"
        return {
            "status": status,
            "engine_version": ENGINE_VERSION,
            "contract": "TSETMC_ONLY_REPORT",
            "missing_fields": missing,
            "failures": failures,
            "checks": {
                "audit_version": audit.get("audit_version") == ENGINE_VERSION,
                "source_of_truth": audit.get("source_of_truth") == "TSETMC",
                "data_mode": audit.get("data_mode") in {"LIVE_TSETMC_REFRESH", "LAST_KNOWN_TSETMC_SNAPSHOT"},
                "snapshot_hash_present": bool(audit.get("snapshot_sha256")),
                "row_count_valid": isinstance(audit.get("row_count"), int) and audit.get("row_count") >= 0,
                "live_movement_not_claimed": audit.get("live_movement_claim") == "NOT_CLAIMED",
                "scoring_contract_valid": audit.get("scoring_status") in {"OFF_FIELD_EVIDENCE_GATE_OPEN", "TSETMC_EVIDENCE_RANKING"},
                "ranking_contract_valid": audit.get("ranking_status") in {"OFF", "TSETMC_EVIDENCE_RANKING"},
                "market_watch_evidence": isinstance(audit.get("market_watch"), dict) and all(
                    audit["market_watch"].get(k) for k in ("endpoint", "snapshot_sha256", "retrieved_at")
                ) if isinstance(audit.get("market_watch"), dict) else False,
                "best_limits_evidence": isinstance(audit.get("best_limits_evidence"), dict),
                "market_state_evidence": isinstance(audit.get("market_state"), dict),
                "report_hash_present": bool(audit.get("report_sha256")),
            },
        }

    required = [
        "source_file",
        "source_sha256",
        "source_sha256_recomputed",
        "report_sha256",
        "freshness_status",
        "selected_count",
        "selected",
        "opportunity_shadow",
        "historical_snapshot",
        "replay_verification",
    ]
    missing = [key for key in required if key not in audit]

    failures = []
    replay = audit.get("replay_verification") or {}
    historical = audit.get("historical_snapshot") or {}
    shadow = audit.get("opportunity_shadow") or {}
    tsetmc = audit.get("tsetmc_evidence") or {}

    shadow_failed = shadow.get("status") == "FAILED"
    if shadow_failed:
        if replay.get("status") != "SKIPPED_SHADOW_FAILURE":
            failures.append("SHADOW_FAILURE_REPLAY_STATE_INVALID")
    else:
        if replay.get("status") not in {"REPLAY_MATCH"}:
            failures.append("REPLAY_NOT_VERIFIED")
        if not replay.get("deterministic"):
            failures.append("REPLAY_NON_DETERMINISTIC")
        if not replay.get("baseline_hash"):
            failures.append("REPLAY_BASELINE_HASH_MISSING")
        if not replay.get("first_hash") or not replay.get("second_hash"):
            failures.append("REPLAY_HASH_MISSING")
    if audit.get("source_sha256") != audit.get("source_sha256_recomputed"):
        failures.append("SOURCE_HASH_MISMATCH")
    if not audit.get("report_sha256"):
        failures.append("REPORT_HASH_MISSING")
    selected = audit.get("selected")
    if isinstance(selected, list):
        if audit.get("selected_count") != len(selected):
            failures.append("SELECTED_COUNT_MISMATCH")
    elif "selected" not in missing:
        failures.append("SELECTED_ARTIFACT_INVALID")
    if not historical.get("snapshot_id"):
        failures.append("HISTORICAL_SNAPSHOT_ID_MISSING")
    if not historical.get("records_hash"):
        failures.append("HISTORICAL_RECORDS_HASH_MISSING")
    if not shadow.get("snapshot_id"):
        failures.append("OPPORTUNITY_SNAPSHOT_ID_MISSING")
    if shadow.get("snapshot_id") != historical.get("snapshot_id"):
        failures.append("SNAPSHOT_ID_MISMATCH")
    # TSETMC evidence is optional Shadow enrichment. If present, its declared
    # status must be structurally valid; it must never silently claim success
    # without an evidence summary.
    if tsetmc and tsetmc.get("status") == "SUCCESS" and "summary" not in tsetmc:
        failures.append("TSETMC_EVIDENCE_SUMMARY_MISSING")

    status = "PASS" if not missing and not failures else "FAIL"
    return {
        "status": status,
        "engine_version": ENGINE_VERSION,
        "missing_fields": missing,
        "failures": failures,
        "checks": {
            "required_fields": not missing,
            "replay_match": replay.get("status") == "REPLAY_MATCH",
            "shadow_failure_nonblocking": shadow_failed,
            "replay_deterministic": bool(replay.get("deterministic")),
            "replay_baseline_hash": bool(replay.get("baseline_hash")),
            "source_hash_match": audit.get("source_sha256") == audit.get("source_sha256_recomputed"),
            "report_hash_present": bool(audit.get("report_sha256")),
            "selected_count_match": isinstance(audit.get("selected"), list) and audit.get("selected_count") == len(audit.get("selected")),
            "historical_snapshot": bool(historical.get("snapshot_id")),
            "historical_records_hash": bool(historical.get("records_hash")),
            "opportunity_snapshot": bool(shadow.get("snapshot_id")),
            "snapshot_consistency": shadow.get("snapshot_id") == historical.get("snapshot_id"),
            "tsetmc_evidence_structurally_valid": not (tsetmc and tsetmc.get("status") == "SUCCESS" and "summary" not in tsetmc),
        },
    }
