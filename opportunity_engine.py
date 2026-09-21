#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V4.1 Shadow Opportunity Engine.

This engine is discovery-only: it never changes FinalScore, ranking, or Bale output.
It converts existing scored rows into auditable opportunity/risk cases using only
features already present in the active V4.1 pipeline.

Statuses:
- CONFIRMED: multiple independent evidence families support the case.
- WATCH: interesting evidence exists but confirmation is incomplete.
- REJECTED: evidence conflicts with the case definition.
- INSUFFICIENT_DATA: required evidence is unavailable.

Important:
- Thresholds are explicit and versioned here; they are not hidden in scoring.
- No buy/sell direction is inferred from a contract symbol.
- No synthetic market values are created.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
import json
from red_team_shadow import challenge_cases
from case_memory_shadow import update_memory
import math
import numpy as np
import pandas as pd

ENGINE_VERSION = "OPP-SHADOW-1.0"
TEHRAN = ZoneInfo("Asia/Tehran")

# Discovery thresholds are intentionally conservative and isolated from scoring.
RELATIVE_VALUE_RANK = 0.85
BREAKEVEN_RANK = 0.80
LIQUIDITY_RANK = 0.75
LIQUIDITY_BLOCK_WEIGHT = 20.0
EXECUTION_PENALTY_MAX = 0.10
CONFIRMATION_CONFIDENCE = 90.0
NEAR_EXPIRY_DAYS = 10


def _num(row, key):
    try:
        value = row.get(key)
        if value is None or pd.isna(value):
            return None
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _flag(row, prefix):
    flags = str(row.get("AnalyticsFlags", "") or "").split("|")
    return any(flag == prefix or flag.startswith(prefix + ":") for flag in flags)


def _evidence(name, value, source):
    return {"name": name, "value": value, "source": source}


def _case_id(snapshot_id, symbol, case_type):
    safe_symbol = str(symbol).replace(" ", "_")
    return f"{snapshot_id}:{case_type}:{safe_symbol}"


def _contract_cases(row, snapshot_id):
    symbol = str(row.get("نماد", "")).strip()
    if not symbol or symbol in {"nan", "None", "<NA>"}:
        return []

    confidence = _num(row, "DataConfidence")
    liquidity = _num(row, "BlockScore_Liquidity")
    valuation = _num(row, "Score_BlackScholesDiff")
    breakeven = _num(row, "Score_BreakevenDistance")
    execution_penalty = _num(row, "ExecutionPenalty")
    remaining_days = _num(row, "RemainingDays")
    final_score = _num(row, "FinalScore")
    diff = _num(row, "اختلاف تا بلک شولز")
    distance = _num(row, "BreakevenDistancePct")
    trade_value = _num(row, "ارزش معاملات")

    common = {
        "snapshot_id": snapshot_id,
        "engine_version": ENGINE_VERSION,
        "symbol": symbol,
        "final_score": final_score,
        "confidence": confidence,
    }
    cases = []

    # 1) Relative value: requires a real Black–Scholes difference score.
    if valuation is None:
        status = "INSUFFICIENT_DATA"
        evidence = [_evidence("black_scholes_difference_score", None, "Score_BlackScholesDiff")]
    else:
        evidence = [
            _evidence("black_scholes_difference_score", valuation, "Score_BlackScholesDiff"),
            _evidence("raw_black_scholes_difference", diff, "اختلاف تا بلک شولز"),
        ]
        if liquidity is not None:
            evidence.append(_evidence("liquidity_block_score", liquidity, "BlockScore_Liquidity"))
        if valuation >= RELATIVE_VALUE_RANK and confidence is not None and confidence >= CONFIRMATION_CONFIDENCE and liquidity is not None and liquidity / LIQUIDITY_BLOCK_WEIGHT >= LIQUIDITY_RANK:
            status = "CONFIRMED"
        elif valuation >= RELATIVE_VALUE_RANK:
            status = "WATCH"
        else:
            status = "REJECTED"
    cases.append({
        **common,
        "case_id": _case_id(snapshot_id, symbol, "RELATIVE_VALUE"),
        "type": "RELATIVE_VALUE_ANOMALY",
        "status": status,
        "reason": "Cross-sectional valuation deviation detected; direction is intentionally not inferred.",
        "evidence": evidence,
    })

    # 2) Breakeven: only a compact-distance candidate is discoverable without call/put semantics.
    if breakeven is None or distance is None:
        status = "INSUFFICIENT_DATA"
        evidence = [_evidence("breakeven_score", breakeven, "Score_BreakevenDistance"),
                    _evidence("breakeven_distance_pct", distance, "BreakevenDistancePct")]
    else:
        evidence = [
            _evidence("breakeven_score", breakeven, "Score_BreakevenDistance"),
            _evidence("breakeven_distance_pct", distance, "BreakevenDistancePct"),
        ]
        if breakeven >= BREAKEVEN_RANK and confidence is not None and confidence >= CONFIRMATION_CONFIDENCE:
            status = "CONFIRMED"
        elif breakeven >= BREAKEVEN_RANK:
            status = "WATCH"
        else:
            status = "REJECTED"
    cases.append({
        **common,
        "case_id": _case_id(snapshot_id, symbol, "BREAKEVEN"),
        "type": "BREAKEVEN_COMPRESSION",
        "status": status,
        "reason": "Small absolute breakeven distance is noteworthy; payoff direction is not inferred.",
        "evidence": evidence,
    })

    # 3) Execution/liquidity confirmation.
    if liquidity is None or execution_penalty is None:
        status = "INSUFFICIENT_DATA"
        evidence = [
            _evidence("liquidity_block_score", liquidity, "BlockScore_Liquidity"),
            _evidence("execution_penalty", execution_penalty, "ExecutionPenalty"),
        ]
    else:
        evidence = [
            _evidence("liquidity_block_score", liquidity, "BlockScore_Liquidity"),
            _evidence("execution_penalty", execution_penalty, "ExecutionPenalty"),
        ]
        if liquidity / LIQUIDITY_BLOCK_WEIGHT >= LIQUIDITY_RANK and execution_penalty <= EXECUTION_PENALTY_MAX:
            status = "CONFIRMED"
        elif liquidity / LIQUIDITY_BLOCK_WEIGHT >= LIQUIDITY_RANK:
            status = "WATCH"
        else:
            status = "REJECTED"
    cases.append({
        **common,
        "case_id": _case_id(snapshot_id, symbol, "EXECUTION"),
        "type": "LIQUIDITY_CONFIRMED",
        "status": status,
        "reason": "Liquidity and execution quality support analytical follow-up.",
        "evidence": evidence,
    })

    # 4) Risk case is explicit and separate from opportunity.
    if remaining_days is None:
        risk_status = "INSUFFICIENT_DATA"
        risk_evidence = [_evidence("remaining_days", None, "RemainingDays")]
    elif remaining_days <= NEAR_EXPIRY_DAYS:
        risk_status = "CONFIRMED"
        risk_evidence = [_evidence("remaining_days", remaining_days, "RemainingDays")]
    else:
        risk_status = "REJECTED"
        risk_evidence = [_evidence("remaining_days", remaining_days, "RemainingDays")]
    cases.append({
        **common,
        "case_id": _case_id(snapshot_id, symbol, "EXPIRY_RISK"),
        "type": "NEAR_EXPIRY_RISK",
        "status": risk_status,
        "reason": "Near-expiry exposure is a risk flag, not an opportunity signal.",
        "evidence": risk_evidence,
    })

    return cases


def run_shadow(scored, snapshot_id, memory_path=None):
    if not isinstance(scored, pd.DataFrame):
        raise TypeError("scored must be a pandas DataFrame")
    if not snapshot_id or not str(snapshot_id).strip():
        raise ValueError("snapshot_id is required")

    required = {"نماد", "FinalScore", "DataConfidence", "AnalyticsFlags"}
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

    cases = []
    for _, row in scored.iterrows():
        cases.extend(_contract_cases(row, str(snapshot_id)))

    counts = {}
    for case in cases:
        key = f"{case['type']}:{case['status']}"
        counts[key] = counts.get(key, 0) + 1

    red_team = challenge_cases(scored, cases, str(snapshot_id))
    memory = None
    if memory_path:
        memory = update_memory(memory_path, cases)
    confirmed = [c for c in cases if c["status"] == "CONFIRMED"]
    watch = [c for c in cases if c["status"] == "WATCH"]
    risks = [c for c in cases if c["type"].endswith("_RISK") and c["status"] == "CONFIRMED"]

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "snapshot_id": str(snapshot_id),
        "generated_at": datetime.now(TEHRAN).isoformat(),
        "summary": {
            "contracts_scanned": int(len(scored)),
            "cases_total": int(len(cases)),
            "confirmed_total": int(len(confirmed)),
            "watch_total": int(len(watch)),
            "confirmed_risk_total": int(len(risks)),
            "counts": counts,
            "red_team_challenged_total": red_team.get("summary", {}).get("challenged_total", 0),
        },
        "cases": cases,
        "red_team": red_team,
        "case_memory": {
            "status": "UPDATED" if memory is not None else "NOT_ENABLED",
            "version": memory.get("memory_version") if memory is not None else None,
            "case_count": len(memory.get("cases", {})) if memory is not None else 0,
        },
    }


def save_shadow(path, result):
    path = str(path)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
    return path
