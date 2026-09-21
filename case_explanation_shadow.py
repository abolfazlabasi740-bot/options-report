#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence classification shadow layer.

This layer explains what the existing evidence actually establishes. It never
adds a market assumption, changes scores, or converts evidence into a trade
direction.

Classes:
OBSERVED            = directly present in the case evidence.
EXPLAINED           = mechanically derivable from other observed evidence.
UNEXPLAINED         = an observed difference/condition without an approved
                      causal explanation.
DATA_GAP            = required evidence is missing/null.
RED_TEAM_CHALLENGE  = an explanation is explicitly challenged by Red Team.
"""

ENGINE_VERSION = "CASE-EXPLANATION-SHADOW-1.0"


def _is_missing(value):
    return value is None or (isinstance(value, float) and value != value)


def _is_derived(name):
    return (
        name.startswith("absolute_difference_")
        or name.endswith("_price_difference")
        or name.endswith("_iv_difference")
        or name == "score_dispersion"
    )


def explain_cases(cases, red_team=None, snapshot_id=None):
    """Return deterministic, evidence-traceable explanations for shadow cases."""
    red_by_case = {}
    for item in (red_team or {}).get("cases", []):
        red_by_case[item.get("case_id")] = item

    results = []
    for case in cases or []:
        evidence = case.get("evidence", [])
        items = []
        for item in evidence:
            name = str(item.get("name", ""))
            value = item.get("value")
            if _is_missing(value):
                classification = "DATA_GAP"
                reason = "Evidence field is unavailable in the current snapshot."
            elif _is_derived(name):
                classification = "EXPLAINED"
                reason = "Value is mechanically derived from observed fields; no economic causality is inferred."
            else:
                classification = "OBSERVED"
                reason = "Value is directly observed or explicitly supplied by an upstream engine."
            items.append({
                "name": name,
                "value": value,
                "source": item.get("source"),
                "classification": classification,
                "reason": reason,
            })

        rt = red_by_case.get(case.get("case_id"))
        challenges = (rt or {}).get("challenges", [])
        if challenges:
            for challenge in challenges:
                items.append({
                    "name": challenge.get("code"),
                    "value": challenge.get("evidence"),
                    "source": challenge.get("source"),
                    "classification": "RED_TEAM_CHALLENGE",
                    "reason": challenge.get("reason"),
                })

        counts = {key: 0 for key in (
            "OBSERVED", "EXPLAINED", "UNEXPLAINED",
            "DATA_GAP", "RED_TEAM_CHALLENGE"
        )}
        for item in items:
            counts[item["classification"]] += 1

        # No causal explanation is invented. If a case contains meaningful
        # observed evidence that is not mechanically explained, flag it.
        unexplained = [
            item for item in items
            if item["classification"] == "OBSERVED"
            and (
                "difference" in item["name"]
                or item["name"] in {"raw_black_scholes_difference", "breakeven_distance_pct"}
            )
        ]
        for item in unexplained:
            item["classification"] = "UNEXPLAINED"
            item["reason"] = "Observed condition has no approved causal explanation in the current rule set."
            counts["OBSERVED"] -= 1
            counts["UNEXPLAINED"] += 1

        results.append({
            "snapshot_id": str(snapshot_id) if snapshot_id is not None else case.get("snapshot_id"),
            "engine_version": ENGINE_VERSION,
            "case_id": case.get("case_id"),
            "symbol": case.get("symbol"),
            "type": case.get("type"),
            "status": case.get("status"),
            "items": items,
            "counts": counts,
            "explanation_status": (
                "RED_TEAM_CHALLENGED" if counts["RED_TEAM_CHALLENGE"] else
                "DATA_GAPS_PRESENT" if counts["DATA_GAP"] else
                "UNEXPLAINED_EVIDENCE" if counts["UNEXPLAINED"] else
                "STRUCTURALLY_EXPLAINED"
            ),
        })

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "snapshot_id": str(snapshot_id) if snapshot_id is not None else None,
        "case_count": len(results),
        "cases": results,
    }
