#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V4.1 Market Red Team -- shadow only.

The Red Team does not produce a trading decision. It challenges Opportunity
Engine cases by looking for plausible alternative explanations and hard data/risk
conditions. Its output is advisory and non-blocking.
"""

ENGINE_VERSION = "REDTEAM-SHADOW-1.0"

CHALLENGE_FLAGS = {
    "DATA_": "data-integrity warning",
    "MISSING_": "missing-data warning",
    "ExtremeDelta": "extreme delta warning",
    "NearExpiry": "near-expiry warning",
    "LowLiquidity": "low-liquidity warning",
}


def _num(row, key):
    value = row.get(key)
    try:
        if value is None:
            return None
        value = float(value)
        return value if value == value else None
    except (TypeError, ValueError):
        return None


def _flags(row):
    return [x.strip() for x in str(row.get("AnalyticsFlags", "") or "").split("|") if x.strip()]


def _challenge_for_case(case, row):
    flags = _flags(row)
    challenges = []

    confidence = _num(row, "DataConfidence")
    liquidity = _num(row, "BlockScore_Liquidity")
    execution = _num(row, "ExecutionPenalty")
    days = _num(row, "RemainingDays")

    for flag in flags:
        for prefix, reason in CHALLENGE_FLAGS.items():
            if flag == prefix or flag.startswith(prefix):
                challenges.append({
                    "code": "FLAG_CHALLENGE",
                    "reason": reason,
                    "evidence": flag,
                    "source": "AnalyticsFlags",
                })
                break

    if confidence is not None and confidence < 90:
        challenges.append({
            "code": "LOW_CONFIDENCE",
            "reason": "Evidence quality is below the confirmation threshold.",
            "evidence": confidence,
            "source": "DataConfidence",
        })

    if liquidity is not None and liquidity < 15:
        challenges.append({
            "code": "LIQUIDITY_CHALLENGE",
            "reason": "Liquidity evidence is weaker than the shadow confirmation threshold.",
            "evidence": liquidity,
            "source": "BlockScore_Liquidity",
        })

    if execution is not None and execution > 0.10:
        challenges.append({
            "code": "EXECUTION_CHALLENGE",
            "reason": "Execution penalty exceeds the shadow confirmation threshold.",
            "evidence": execution,
            "source": "ExecutionPenalty",
        })

    if days is not None and days <= 10 and case["type"] != "NEAR_EXPIRY_RISK":
        challenges.append({
            "code": "EXPIRY_CHALLENGE",
            "reason": "Near-expiry exposure can materially alter interpretation of an apparent opportunity.",
            "evidence": days,
            "source": "RemainingDays",
        })

    return challenges


def challenge_cases(scored, cases, snapshot_id):
    required = {"نماد", "AnalyticsFlags"}
    missing = sorted(required.difference(scored.columns))
    if missing:
        return {
            "status": "INSUFFICIENT_DATA",
            "engine_version": ENGINE_VERSION,
            "snapshot_id": snapshot_id,
            "missing_columns": missing,
            "cases": [],
            "summary": {},
        }

    rows = {str(row["نماد"]).strip(): row for _, row in scored.iterrows()}
    challenged = []

    for case in cases:
        row = rows.get(case["symbol"])
        if row is None:
            challenged.append({
                "case_id": case["case_id"],
                "symbol": case["symbol"],
                "original_status": case["status"],
                "red_team_status": "INSUFFICIENT_DATA",
                "challenge_count": 1,
                "challenges": [{
                    "code": "ROW_NOT_FOUND",
                    "reason": "The contract row is not available in the scored snapshot.",
                    "evidence": None,
                    "source": "scored_snapshot",
                }],
            })
            continue

        challenges = _challenge_for_case(case, row)
        if challenges:
            status = "CHALLENGED"
        else:
            status = "NO_CHALLENGE_FOUND"

        challenged.append({
            "case_id": case["case_id"],
            "symbol": case["symbol"],
            "original_status": case["status"],
            "red_team_status": status,
            "challenge_count": len(challenges),
            "challenges": challenges,
        })

    summary = {
        "cases_reviewed": len(challenged),
        "challenged_total": sum(x["red_team_status"] == "CHALLENGED" for x in challenged),
        "unchallenged_total": sum(x["red_team_status"] == "NO_CHALLENGE_FOUND" for x in challenged),
        "insufficient_data_total": sum(x["red_team_status"] == "INSUFFICIENT_DATA" for x in challenged),
    }

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "snapshot_id": str(snapshot_id),
        "summary": summary,
        "cases": challenged,
    }
