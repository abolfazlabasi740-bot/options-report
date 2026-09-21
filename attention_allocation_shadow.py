#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Non-trading attention allocation for OptimusAI V4.1 Shadow cases."""

from __future__ import annotations

from typing import Any, Iterable

ENGINE_VERSION = "ATTENTION-SHADOW-1.0"


def allocate_attention(
    cases: Iterable[dict[str, Any]],
    *,
    red_team: dict[str, Any] | None = None,
    historical_patterns: dict[str, Any] | None = None,
) -> dict[str, Any]:
    red_map = {
        item.get("case_id"): item
        for item in (red_team or {}).get("cases", [])
    }
    pattern_map: dict[str, list[dict[str, Any]]] = {}
    for item in (historical_patterns or {}).get("patterns", []):
        pattern_map.setdefault(str(item.get("identity")), []).append(item)

    allocations = []
    for case in cases:
        case_id = case.get("case_id")
        symbol = str(case.get("symbol") or "")
        rt = red_map.get(case_id, {})
        challenges = rt.get("challenges", [])
        patterns = pattern_map.get(symbol, [])

        if not case.get("case_id"):
            route = "INVALID_CASE_ID"
            reason = "Case cannot be routed without a stable case identifier."
        elif challenges:
            route = "RED_TEAM_REVIEW"
            reason = "Case has explicit Red Team challenge evidence."
        elif case.get("status") == "INSUFFICIENT_DATA":
            route = "DATA_COMPLETION"
            reason = "Required evidence is missing; deeper interpretation is premature."
        elif case.get("status") == "CONFIRMED" and patterns:
            route = "CROSS_SNAPSHOT_REVIEW"
            reason = "Case has current confirmation plus historical descriptive patterns."
        elif case.get("status") == "CONFIRMED":
            route = "EVIDENCE_REVIEW"
            reason = "Case is confirmed by the current Shadow rule set."
        elif case.get("status") == "WATCH":
            route = "FOLLOW_UP"
            reason = "Case is noteworthy but current confirmation is incomplete."
        else:
            route = "CONTEXT_ONLY"
            reason = "No additional review route is triggered by current evidence."

        allocations.append({
            "case_id": case_id,
            "symbol": symbol,
            "route": route,
            "reason": reason,
            "pattern_count": len(patterns),
            "red_team_challenge_count": len(challenges),
        })

    summary = {}
    for item in allocations:
        summary[item["route"]] = summary.get(item["route"], 0) + 1

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "case_count": len(allocations),
        "summary": summary,
        "allocations": allocations,
    }
