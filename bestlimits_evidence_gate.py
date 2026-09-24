#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a time-locked BestLimits evidence package.

This validator checks evidence completeness only. It never infers field semantics
and never unlocks scoring.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime
from pathlib import Path

REQUIRED_FIELDS = {
    "source", "instrument_id", "endpoint", "capture_started_at_utc",
    "retrieved_at_utc", "payload_sha256", "raw_payload", "level_count", "raw_levels",
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
    raw_payload = item.get("raw_payload")
    if not isinstance(raw_payload, dict):
        errors.append("raw_payload_not_object")
    else:
        if sha256_json(raw_payload) != item.get("payload_sha256"):
            errors.append("payload_sha256_mismatch")
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
    def role_set(role_name):
        result = set()
        for iid, value in roles.items():
            values = value if isinstance(value, list) else [value]
            if role_name in values:
                result.add(iid)
        return result
    options = role_set("option")
    underlyings = role_set("underlying")
    if options & underlyings:
        errors.append("instrument_role_overlap_option_underlying")
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
    semantic = package.get("independent_semantic_evidence")
    if not isinstance(semantic, list) or not semantic:
        errors.append("independent_same_time_semantic_evidence_missing")
    else:
        capture_pairs = {
            (str(item.get("instrument_id", "")).strip(), str(item.get("retrieved_at_utc", "")).strip())
            for item in captures
            if str(item.get("instrument_id", "")).strip() and str(item.get("retrieved_at_utc", "")).strip()
        }
        evidence_pairs = set()
        for idx, evidence in enumerate(semantic):
            if not isinstance(evidence, dict):
                errors.append(f"semantic_evidence[{idx}]:must_be_object")
                continue
            required_semantic = {"instrument_id", "capture_timestamp_utc", "evidence_source", "evidence_location", "evidence_type", "matched_fields"}
            missing_semantic = sorted(required_semantic - evidence.keys())
            if missing_semantic:
                errors.append(f"semantic_evidence[{idx}]:missing:" + ",".join(missing_semantic))
            iid = str(evidence.get("instrument_id", "")).strip()
            ts = str(evidence.get("capture_timestamp_utc", "")).strip()
            if iid not in seen:
                errors.append(f"semantic_evidence[{idx}]:instrument_not_captured")
            if not ts:
                errors.append(f"semantic_evidence[{idx}]:missing_capture_timestamp")
            if not str(evidence.get("evidence_source", "")).strip():
                errors.append(f"semantic_evidence[{idx}]:missing_source")
            if not str(evidence.get("evidence_location", "")).strip():
                errors.append(f"semantic_evidence[{idx}]:missing_location")
            evidence_type = str(evidence.get("evidence_type", "")).strip()
            if not evidence_type:
                errors.append(f"semantic_evidence[{idx}]:missing_evidence_type")
            elif evidence_type != "TSETMC_WEB_BOARD_OBSERVATION":
                errors.append(f"semantic_evidence[{idx}]:unsupported_evidence_type")
            matched_fields = evidence.get("matched_fields")
            required_fields = {"pd", "po", "qd", "qo", "zd", "zo"}
            if not isinstance(matched_fields, list) or set(matched_fields) != required_fields:
                errors.append(f"semantic_evidence[{idx}]:matched_fields_must_cover_pd_po_qd_qo_zd_zo")
            if iid in seen and ts:
                try:
                    evidence_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    capture_times = [datetime.fromisoformat(str(x).replace("Z", "+00:00")) for x in seen[iid] if x]
                    if not any(abs((evidence_time - ct).total_seconds()) <= 2 for ct in capture_times):
                        errors.append(f"semantic_evidence[{idx}]:timestamp_outside_2s_capture_window")
                except (ValueError, TypeError):
                    errors.append(f"semantic_evidence[{idx}]:invalid_timestamp")
            else:
                errors.append(f"semantic_evidence[{idx}]:cannot_correlate_timestamp")
        for iid, timestamps in seen.items():
            for raw_ts in timestamps:
                if not raw_ts:
                    continue
                try:
                    ct = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                    matching = False
                    for evidence in semantic:
                        if not isinstance(evidence, dict) or str(evidence.get("instrument_id", "")).strip() != iid:
                            continue
                        ets = str(evidence.get("capture_timestamp_utc", "")).strip()
                        if not ets:
                            continue
                        try:
                            et = datetime.fromisoformat(ets.replace("Z", "+00:00"))
                            if abs((et - ct).total_seconds()) <= 2:
                                matching = True
                                break
                        except (ValueError, TypeError):
                            continue
                    if not matching:
                        errors.append(f"semantic_evidence_missing_for_capture:{iid}:{raw_ts}")
                except (ValueError, TypeError):
                    errors.append(f"capture_timestamp_invalid:{iid}:{raw_ts}")
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
