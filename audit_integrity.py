#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed audit integrity checks for OptimusAI V4.1 artifacts."""

from __future__ import annotations

from typing import Any

ENGINE_VERSION = "AUDIT-INTEGRITY-1.1"


def verify_audit(audit: dict[str, Any]) -> dict[str, Any]:
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
