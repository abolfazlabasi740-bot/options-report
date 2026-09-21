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
from chain_identity_shadow import build_chain_identity
from relative_value_shadow import analyze_chain
from case_explanation_shadow import explain_cases
from schema_audit import audit_schema
from historical_snapshot import case_historical_context
from historical_pattern_shadow import build_historical_patterns
from attention_allocation_shadow import allocate_attention
from case_lifecycle_shadow import append_events
from opportunity_config import CONFIG
from eligibility_shadow import classify_dataframe
import math
import numpy as np
import pandas as pd

ENGINE_VERSION = "OPP-SHADOW-1.0"
TEHRAN = ZoneInfo("Asia/Tehran")

# Discovery thresholds are intentionally conservative and isolated from scoring.
RELATIVE_VALUE_RANK = CONFIG.relative_value_rank
BREAKEVEN_RANK = CONFIG.breakeven_rank
LIQUIDITY_RANK = CONFIG.liquidity_rank
LIQUIDITY_BLOCK_WEIGHT = CONFIG.liquidity_block_weight
EXECUTION_PENALTY_MAX = CONFIG.execution_penalty_max
CONFIRMATION_CONFIDENCE = CONFIG.confirmation_confidence
NEAR_EXPIRY_DAYS = CONFIG.near_expiry_days


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




def _chain_cases(scored, snapshot_id, chain_result):
    """Create structural cases from validated full option chains."""
    if chain_result.get("status") != "SUCCESS":
        return []

    by_symbol = {}
    for _, row in scored.iterrows():
        symbol = str(row.get("نماد", "")).strip()
        if symbol:
            by_symbol[symbol] = row

    cases = []
    for key, chain in chain_result.get("chains", {}).items():
        members = [by_symbol[s] for s in chain.get("members", []) if s in by_symbol]
        if len(members) < 2:
            continue

        scores = []
        score_symbols = []
        for row in members:
            value = _num(row, "FinalScore")
            if value is not None:
                scores.append(value)
                score_symbols.append(str(row.get("نماد", "")).strip())

        if len(scores) < 2:
            continue

        spread = max(scores) - min(scores)
        if spread < 20.0:
            continue

        evidence = [
            _evidence("chain_key", key, "chain_identity_shadow"),
            _evidence("member_count", len(members), "chain_identity_shadow"),
            _evidence("strike_count", chain.get("strike_count"), "chain_identity_shadow"),
            _evidence("score_dispersion", spread, "FinalScore"),
            _evidence("members", chain.get("members", []), "chain_identity_shadow"),
            _evidence("score_members", dict(zip(score_symbols, scores)), "FinalScore"),
        ]

        cases.append({
            "snapshot_id": snapshot_id,
            "engine_version": ENGINE_VERSION,
            "case_id": _case_id(snapshot_id, key, "CHAIN_STRUCTURE"),
            "type": "CHAIN_STRUCTURE_ANOMALY",
            "status": "WATCH",
            "symbol": key,
            "final_score": max(scores),
            "confidence": None,
            "reason": (
                "Validated contracts in one explicit underlying/expiry chain show "
                "material cross-contract score dispersion. This is a review signal, "
                "not a trade direction."
            ),
            "evidence": evidence,
        })

        # A parity case requires unique explicit identities. Duplicate identities
        # are retained for audit but cannot support a clean pairwise comparison.
        if chain.get("duplicate_identities"):
            continue

        # A complete parity case is created only when both sides are explicit
        # and share the same strike. No type inference is permitted.
        call_by_strike = {}
        put_by_strike = {}
        for member in chain.get("members", []):
            row = by_symbol.get(member)
            if row is None:
                continue
            identity_rows = [
                x for x in chain_result.get("rows", [])
                if x.get("symbol") == member and x.get("status") == "VALID"
            ]
            if not identity_rows:
                continue
            ident = identity_rows[0]
            if ident.get("contract_type") == "CALL":
                call_by_strike[ident.get("strike")] = member
            elif ident.get("contract_type") == "PUT":
                put_by_strike[ident.get("strike")] = member

        common_strikes = sorted(set(call_by_strike) & set(put_by_strike))
        if common_strikes:
            cases.append({
                "snapshot_id": snapshot_id,
                "engine_version": ENGINE_VERSION,
                "case_id": _case_id(snapshot_id, key, "CALL_PUT_STRUCTURE"),
                "type": "CALL_PUT_STRUCTURE_AVAILABLE",
                "status": "WATCH",
                "symbol": key,
                "final_score": None,
                "confidence": None,
                "reason": (
                    "Both explicit CALL and PUT contracts exist at common strike(s). "
                    "This unlocks parity/relative-structure analysis but is not itself "
                    "evidence of mispricing."
                ),
                "evidence": [
                    _evidence("common_strikes", common_strikes, "chain_identity_shadow"),
                    _evidence("call_symbols", [call_by_strike[k] for k in common_strikes], "chain_identity_shadow"),
                    _evidence("put_symbols", [put_by_strike[k] for k in common_strikes], "chain_identity_shadow"),
                ],
            })

    return cases

def run_shadow(scored, snapshot_id, memory_path=None, historical_previous=None, historical_current=None, historical_sequence=None, lifecycle_path=None):
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

    schema_audit_result = audit_schema(scored)
    # Eligibility is evidence-only: it explains production-gate side effects
    # without removing rows from Shadow opportunity discovery.
    eligibility = classify_dataframe(scored, min_leverage=CONFIG.production_min_leverage_reference)
    eligibility_by_symbol = {item.get("symbol"): item for item in eligibility.get("rows", [])}
    chain_result = build_chain_identity(scored)
    cases = []
    for _, row in scored.iterrows():
        cases.extend(_contract_cases(row, str(snapshot_id)))
    cases.extend(_chain_cases(scored, str(snapshot_id), chain_result))
    cases.extend(analyze_chain(scored, chain_result, str(snapshot_id)))

    for case in cases:
        item = eligibility_by_symbol.get(case.get("symbol"))
        case["eligibility"] = item or {
            "status": "CHAIN_LEVEL",
            "reason": "CASE_IS_NOT_TIED_TO_A_SINGLE_CONTRACT",
        }
        # Expired contracts remain visible for history/audit, but cannot become
        # active opportunity cases. Risk cases remain explicitly observable.
        if item and item.get("status") == "EXPIRED" and not case["type"].endswith("_RISK"):
            case["status"] = "REJECTED"
            case["reason"] = "Expired contract retained for evidence/history; not an active opportunity."

    counts = {}
    for case in cases:
        key = f"{case['type']}:{case['status']}"
        counts[key] = counts.get(key, 0) + 1

    red_team = challenge_cases(scored, cases, str(snapshot_id))
    explanations = explain_cases(cases, red_team, str(snapshot_id))
    memory = None
    if memory_path:
        memory = update_memory(memory_path, cases)

    lifecycle = None
    if lifecycle_path:
        lifecycle = append_events(lifecycle_path, str(snapshot_id), cases)
    if historical_current is not None:
        historical_context = case_historical_context(
            cases,
            historical_previous,
            historical_current,
            identity_key="نماد",
        )
    else:
        historical_context = {
            "engine_version": "HIST-SNAPSHOT-1.0",
            "status": "NOT_ATTACHED",
            "cases": [],
        }

    if historical_sequence is not None:
        historical_patterns = build_historical_patterns(
            historical_sequence,
            identity_key="نماد",
            window=CONFIG.historical_pattern_window,
        )
    else:
        historical_patterns = {
            "status": "NOT_ATTACHED",
            "engine_version": "HIST-PATTERN-SHADOW-1.0",
            "patterns": [],
            "summary": {},
        }

    attention = allocate_attention(
        cases,
        red_team=red_team,
        historical_patterns=historical_patterns,
    )

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
            "chain_count": chain_result.get("summary", {}).get("chain_count", 0),
            "chain_identity_status": chain_result.get("status"),
            "schema_identity_readiness": schema_audit_result.get("identity_readiness"),
            "schema_contract_type_readiness": schema_audit_result.get("contract_type_readiness"),
            "eligibility_counts": eligibility.get("summary", {}).get("counts", {}),
        },
        "cases": cases,
        "red_team": red_team,
        "case_explanations": explanations,
        "chain_identity": chain_result,
        "schema_audit": schema_audit_result,
        "eligibility": eligibility,
        "historical_context": historical_context,
        "historical_patterns": historical_patterns,
        "attention_allocation": attention,
        "case_memory": {
            "status": "UPDATED" if memory is not None else "NOT_ENABLED",
            "version": memory.get("memory_version") if memory is not None else None,
            "case_count": len(memory.get("cases", {})) if memory is not None else 0,
        },
        "case_lifecycle": lifecycle or {
            "status": "NOT_ENABLED",
            "engine_version": "CASE-LIFECYCLE-SHADOW-1.0",
            "events_written": 0,
        },
    }


def save_shadow(path, result):
    path = str(path)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
    return path
