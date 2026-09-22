#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only standalone equity opportunity detection for V4.1."""
from __future__ import annotations
import hashlib
import json
from typing import Any

ENGINE_VERSION = "EQUITY-OPPORTUNITY-SHADOW-1.0"
MIN_FAMILIES = 2

def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()

def _clusters(value):
    if not value:
        return []
    if isinstance(value, dict):
        return list(value.get("clusters", []) or [])
    return list(value)

def _case_index(cases):
    return {str(c.get("case_id")): c for c in (cases or []) if c.get("case_id")}

def _families(cluster):
    return sorted({
        str(x.get("family")).strip()
        for x in cluster.get("supporting_evidence", []) or []
        if str(x.get("family") or "").strip()
    })

def _opportunity_type(families):
    s=set(families)
    if {"PRICE_VOLUME","MARKET_RELATIVE"} <= s:
        return "EQUITY_PRICE_VOLUME_RELATIVE_CONTEXT"
    if {"PRICE_VOLUME","LIQUIDITY"} <= s:
        return "EQUITY_PRICE_VOLUME_LIQUIDITY_CONTEXT"
    if {"FLOW","MARKET_RELATIVE"} <= s:
        return "EQUITY_FLOW_RELATIVE_CONTEXT"
    if "HISTORICAL_PATTERN" in s and len(s) >= 2:
        return "EQUITY_HISTORICAL_MULTI_FACTOR_CONTEXT"
    return "EQUITY_MULTI_FACTOR_ANOMALY"

def detect_equity_opportunities(cases, evidence_clusters=None,
                                historical_patterns=None, red_team=None,
                                snapshot_id=None, lifecycle_path=None):
    case_map = _case_index(cases)
    clusters = _clusters(evidence_clusters)
    patterns = historical_patterns or {}
    red = red_team or {}
    red_map = {str(x.get("case_id")): x for x in red.get("cases", []) or []}

    opportunities = []
    for cluster in sorted(clusters, key=lambda x: str(x.get("cluster_id", ""))):
        families = _families(cluster)
        if len(families) < MIN_FAMILIES:
            continue
        iid = str(cluster.get("instrument_id") or "").strip()
        if not iid:
            continue
        case_ids = sorted(str(x) for x in cluster.get("case_ids", []) if str(x))
        observed = [case_map[cid] for cid in case_ids if cid in case_map
                    and case_map[cid].get("status") == "OBSERVED"]
        if len({str(c.get("family")) for c in observed}) < MIN_FAMILIES:
            continue

        contradictions = []
        for cid in case_ids:
            if cid in red_map:
                contradictions.append(red_map[cid])

        historical = cluster.get("historical_patterns") or [
            p for p in patterns.get("patterns", []) or []
            if str(p.get("instrument_id") or p.get("identity") or p.get("symbol") or "") == iid
        ]
        opp = {
            "snapshot_id": snapshot_id,
            "instrument_id": iid,
            "opportunity_id": "",
            "type": _opportunity_type(families),
            "status": "WATCH",
            "evidence_status": "MULTI_FAMILY_OBSERVED",
            "independent_family_count": len(families),
            "evidence_families": families,
            "case_ids": case_ids,
            "cluster_id": cluster.get("cluster_id"),
            "supporting_cases": observed,
            "historical_patterns": historical,
            "red_team_challenges": contradictions,
            "reason": (
                "Multiple independently observed equity evidence families "
                "co-occur for the same explicit instrument. This is a review "
                "candidate only; no causal or directional conclusion is inferred."
            ),
            "direction_inference": "DISABLED",
            "score_change": "NONE",
            "engine_version": ENGINE_VERSION,
        }
        identity_payload = {
            "snapshot_id": snapshot_id,
            "instrument_id": iid,
            "cluster_id": cluster.get("cluster_id"),
            "case_ids": case_ids,
            "families": families,
        }
        opp["opportunity_id"] = _hash(identity_payload)[:24]
        opp["opportunity_sha256"] = _hash(opp)
        opportunities.append(opp)

    out = {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "snapshot_id": snapshot_id,
        "analysis_mode": "EQUITY_ONLY",
        "summary": {
            "opportunity_count": len(opportunities),
            "watch_count": sum(x["status"] == "WATCH" for x in opportunities),
            "instruments": len({x["instrument_id"] for x in opportunities}),
        },
        "opportunities": opportunities,
        "rules": {
            "minimum_independent_families": MIN_FAMILIES,
            "source": "observed_evidence_clusters_only",
            "symbol_inference": False,
            "direction_inference": "DISABLED",
            "score_change": "NONE",
            "missing_data_policy": "NO_ZERO_FILL",
            "causal_inference": False,
        },
    }
    out["opportunities_sha256"] = _hash(opportunities)
    if lifecycle_path:
        from equity_opportunity_lifecycle_shadow import append_opportunity_events, load_events
        lifecycle_result = append_opportunity_events(lifecycle_path, str(snapshot_id or ""), opportunities)
        out["lifecycle"] = lifecycle_result
        from equity_pattern_shadow import analyze_cross_snapshot_patterns
        out["cross_snapshot_patterns"] = analyze_cross_snapshot_patterns(load_events(lifecycle_path))
        from equity_historical_confirmation_shadow import enrich_opportunities
        out["historical_confirmation"] = enrich_opportunities(out["opportunities"], out["cross_snapshot_patterns"])
        out["opportunities"] = out["historical_confirmation"]["opportunities"]
    else:
        out["lifecycle"] = {
            "status": "NOT_PERSISTED",
            "engine_version": "EQUITY-LIFECYCLE-SHADOW-1.0",
            "reason": "NO_LIFECYCLE_PATH_SUPPLIED",
        }
    return out
