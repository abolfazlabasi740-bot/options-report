#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a time-locked BestLimits evidence package.

This validator checks evidence completeness only. It never infers field semantics
and never unlocks scoring.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

REQUIRED_FIELDS = {
    "source", "instrument_id", "endpoint", "capture_started_at_utc",
    "retrieved_at_utc", "payload_sha256", "level_count", "raw_levels",
}

def sha256_json(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def validate_capture(item):
    errors = []
    missing = sorted(REQUIRED_FIELDS - item.keys())
    if missing:
        return ["missing:" + ",".join(missing)]
    if item.get("source") != "TSETMC":
        errors.append("source_not_tsetmc")
    if not str(item.get("instrument_id", "")).strip():
        errors.append("missing_instrument_id")
    if not str(item.get("endpoint", "")).strip():
        errors.append("missing_endpoint")
    raw = item.get("raw_levels")
    if not isinstance(raw, list):
        errors.append("raw_levels_not_list")
    elif item.get("level_count") != len(raw):
        errors.append("level_count_mismatch")
    if item.get("semantic_mapping_status") not in {None, "OPEN"}:
        errors.append("semantic_mapping_status_must_remain_open")
    if item.get("scoring_status") not in {None, "BLOCKED"}:
        errors.append("scoring_status_must_remain_blocked")
    return errors

def validate_package(package):
    captures = package.get("captures")
    errors = []
    if not isinstance(captures, list) or not captures:
        return {"status":"INCOMPLETE","capture_count":0,"option_instruments":0,
                "underlying_instruments":0,"errors":["captures_missing_or_empty"],
                "mapping_freeze":"BLOCKED","scoring":"BLOCKED"}
    seen = {}
    for idx, item in enumerate(captures):
        for e in validate_capture(item):
            errors.append(f"capture[{idx}]:{e}")
        iid = str(item.get("instrument_id", "")).strip()
        if iid:
            seen.setdefault(iid, []).append(item.get("retrieved_at_utc"))
    roles = package.get("instrument_roles", {})
    if not isinstance(roles, dict):
        roles = {}
    options = {i for i,r in roles.items() if r == "option"}
    underlyings = {i for i,r in roles.items() if r == "underlying"}
    if len(options) < 3:
        errors.append("need_at_least_3_explicit_option_instruments")
    if len(underlyings) < 1:
        errors.append("need_at_least_1_explicit_underlying_instrument")
    for iid in options | underlyings:
        if iid not in seen:
            errors.append(f"role_instrument_without_capture:{iid}")
    for iid, timestamps in seen.items():
        if len(set(timestamps)) < 2:
            errors.append(f"multiple_timestamps_required:{iid}")
    if not package.get("independent_semantic_evidence"):
        errors.append("independent_same_time_semantic_evidence_missing")
    return {
        "status": "READY_FOR_REVIEW" if not errors else "INCOMPLETE",
        "capture_count": len(captures),
        "option_instruments": len(options),
        "underlying_instruments": len(underlyings),
        "errors": errors,
        "mapping_freeze": "BLOCKED",
        "scoring": "BLOCKED",
        "note": "Completeness is not semantic proof; review of independent same-time evidence is still required.",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    result = validate_package(json.loads(args.package.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "READY_FOR_REVIEW" else 2

if __name__ == "__main__":
    raise SystemExit(main())
