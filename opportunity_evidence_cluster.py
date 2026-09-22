#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V4.1 Shadow Multi-Factor Opportunity Evidence Cluster.

Aggregates already-observed evidence into deterministic, auditable clusters.
This layer does not change FinalScore, ranking, production eligibility, or trade
direction. It only proves when independent evidence families coexist.
"""

import hashlib
import json
import math
from collections import defaultdict

ENGINE_VERSION = "OPPORTUNITY-CLUSTER-SHADOW-1.1"
MIN_WATCH_FAMILIES = 2
MIN_CONFIRMED_FAMILIES = 3

_FAMILY_BY_CASE = {
    "RELATIVE_VALUE_ANOMALY": "RELATIVE_VALUE",
    "BREAKEVEN_COMPRESSION": "BREAKEVEN",
    "BASE_BREAKEVEN_CONTEXT": "BASE_CONTEXT",
    "LIQUIDITY_CONFIRMED": "LIQUIDITY_EXECUTION",
    "CHAIN_STRUCTURE_ANOMALY": "CHAIN_STRUCTURE",
    "CALL_PUT_STRUCTURE_AVAILABLE": "RELATIVE_VALUE",
    "NEAR_EXPIRY_RISK": "TIME_RISK",
}

def _clean(value):
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value

def _family(case):
    explicit = case.get("evidence_family")
    if explicit:
        return str(explicit)
    return _FAMILY_BY_CASE.get(str(case.get("type", "")), "OTHER")

def _source_family(source):
    """Classify market-data provenance without treating derived evidence as a new source."""
    value = str(source or "").strip().lower()
    if not value:
        return "UNKNOWN"
    if "tsetmc" in value or "tse" in value:
        return "TSETMC"
    if "optionschool" in value or any(token in value for token in (
        "black_scholes", "breakeven", "liquidity", "score_", "finalscore",
        "spread", "greeks", "iv", "volume", "tradevalue",
    )):
        return "OPTIONSCHOOL24_OR_DERIVED"
    return "OTHER_SOURCE_OR_UNSPECIFIED"


def _is_active_case(case):
    eligibility = case.get("eligibility") or {}
    if eligibility.get("status") == "EXPIRED":
        return str(case.get("type", "")).endswith("_RISK")
    return case.get("status") in {"CONFIRMED", "WATCH"}

def _hash(payload):
    canonical = json.dumps(_clean(payload), ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def build_opportunity_evidence_clusters(cases, historical_patterns=None, red_team=None):
    """Build deterministic clusters from existing evidence only."""
    cases = list(cases or [])
    historical_patterns = historical_patterns or {}
    red_team = red_team or {}

    grouped = defaultdict(list)
    for case in cases:
        symbol = str(case.get("symbol", "")).strip()
        if not symbol or not _is_active_case(case):
            continue
        grouped[symbol].append(case)

    red_by_case = defaultdict(list)
    for challenge in red_team.get("challenges", []) or []:
        case_id = challenge.get("case_id")
        if case_id:
            red_by_case[case_id].append(challenge)

    patterns_by_symbol = defaultdict(list)
    for pattern in historical_patterns.get("patterns", []) or []:
        symbol = pattern.get("identity") or pattern.get("symbol")
        if symbol:
            patterns_by_symbol[str(symbol)].append(pattern)

    clusters = []
    for symbol in sorted(grouped):
        members = grouped[symbol]
        families = defaultdict(list)
        source_families = set()
        contradictions = []
        gaps = []

        for case in sorted(members, key=lambda x: str(x.get("case_id", ""))):
            family = _family(case)
            families[family].append(case.get("case_id"))
            for evidence in case.get("evidence", []) or []:
                source_families.add(_source_family(evidence.get("source")))
                if evidence.get("value") is None:
                    gaps.append({
                        "case_id": case.get("case_id"),
                        "evidence": evidence.get("name"),
                        "source": evidence.get("source"),
                    })
            for challenge in red_by_case.get(case.get("case_id"), []):
                contradictions.append({
                    "case_id": case.get("case_id"),
                    "challenge": _clean(challenge),
                })

        family_names = sorted(families)
        if len(family_names) < MIN_WATCH_FAMILIES:
            continue

        known_source_families = sorted(source for source in source_families if source != "UNKNOWN")
        source_diversity = (
            "MULTI_SOURCE"
            if len(known_source_families) >= 2
            else "SINGLE_SOURCE_OR_DERIVED"
            if known_source_families
            else "SOURCE_METADATA_INSUFFICIENT"
        )

        historical = patterns_by_symbol.get(symbol, [])
        status = (
            "MULTI_FAMILY_CONFIRMED"
            if len(family_names) >= MIN_CONFIRMED_FAMILIES
            else "MULTI_FAMILY_WATCH"
        )

        evidence_refs = []
        for family in family_names:
            evidence_refs.append({
                "family": family,
                "case_ids": sorted(families[family]),
                "case_count": len(families[family]),
            })

        payload = {
            "engine_version": ENGINE_VERSION,
            "symbol": symbol,
            "status": status,
            "case_ids": sorted(c.get("case_id") for c in members if c.get("case_id")),
            "evidence_families": evidence_refs,
            "source_families": known_source_families,
            "source_diversity": source_diversity,
            "historical_pattern_count": len(historical),
            "contradiction_count": len(contradictions),
            "data_gap_count": len(gaps),
        }
        cluster_id = _hash(payload)[:24]
        cluster = {
            **payload,
            "cluster_id": cluster_id,
            "independent_family_count": len(family_names),
            "source_family_count": len(known_source_families),
            "supporting_evidence": evidence_refs,
            "historical_patterns": _clean(historical),
            "contradictory_evidence": contradictions,
            "data_gaps": gaps,
            "direction_inference": "DISABLED",
            "score_change": "NONE",
        }
        cluster["cluster_sha256"] = _hash(cluster)
        clusters.append(cluster)

    summary = {
        "cluster_count": len(clusters),
        "multi_family_watch": sum(c["status"] == "MULTI_FAMILY_WATCH" for c in clusters),
        "multi_family_confirmed": sum(c["status"] == "MULTI_FAMILY_CONFIRMED" for c in clusters),
        "max_independent_family_count": max((c["independent_family_count"] for c in clusters), default=0),
        "multi_source_cluster_count": sum(c["source_diversity"] == "MULTI_SOURCE" for c in clusters),
        "single_source_or_derived_cluster_count": sum(
            c["source_diversity"] == "SINGLE_SOURCE_OR_DERIVED" for c in clusters
        ),
    }
    result = {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "summary": summary,
        "clusters": clusters,
        "rules": {
            "minimum_watch_families": MIN_WATCH_FAMILIES,
            "minimum_confirmed_families": MIN_CONFIRMED_FAMILIES,
            "family_count_is_not_source_independence": True,
            "source_diversity_is_descriptive": True,
            "expired_non_risk_cases_active": False,
            "direction_inference": "DISABLED",
            "score_change": "NONE",
        },
    }
    result["clusters_sha256"] = _hash(result["clusters"])
    return result
