#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed Shadow Signal Engine for OptimusAI V4.1."""
from __future__ import annotations
from typing import Any

SIGNAL_ENGINE_VERSION = "SIGNAL-SHADOW-1.1"
BLOCKED = "BLOCKED"
WATCH = "WATCH"
PRODUCTION_NOT_ENABLED = "PRODUCTION_SIGNAL_NOT_ENABLED"

def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        x = float(value)
        return x if x == x else None
    except (TypeError, ValueError):
        return None

def evaluate_shadow_candidate(candidate: dict[str, Any], *, strategy_policy=None,
                              risk_policy=None, production_enabled=False) -> dict[str, Any]:
    strategy_policy = strategy_policy or {}
    risk_policy = risk_policy or {}
    evidence = candidate.get("evidence") or {}
    features = evidence.get("features") or {}
    blockers = list(candidate.get("blockers") or [])
    score = candidate.get("economic_score") if "economic_score" in candidate else candidate.get("score")
    if not candidate.get("instrument_id") or candidate.get("contract_type") not in {"CALL", "PUT"}:
        blockers.append("IDENTITY_OR_CONTRACT_TYPE_UNAVAILABLE")
    if score is None:
        blockers.append("RANKING_SCORE_UNAVAILABLE")
    if not evidence.get("supported_blocks"):
        blockers.append("NO_SUPPORTED_RANKING_BLOCK")
    if not strategy_policy.get("version"):
        blockers.append("STRATEGY_POLICY_NOT_VERSIONED")
    if not risk_policy.get("version"):
        blockers.append("RISK_POLICY_NOT_VERSIONED")
    if not production_enabled:
        blockers.append(PRODUCTION_NOT_ENABLED)
    observed = {
        "ranking_score": _num(score),
        "ranking_rank": candidate.get("rank"),
        "contract_type": candidate.get("contract_type"),
        "calendar_days": _num(features.get("calendar_days")),
        "trade_value": _num(features.get("trade_value")),
        "volume": _num(features.get("volume")),
        "breakeven_distance": _num(features.get("breakeven_distance")),
        "last_vs_close": _num(features.get("last_vs_close")),
        "intraday_range": _num(features.get("intraday_range")),
    }
    return {
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
        "state": BLOCKED if blockers else WATCH,
        "proposed_signal": None,
        "production_signal": None,
        "instrument_id": candidate.get("instrument_id"),
        "symbol": candidate.get("symbol"),
        "contract_type": candidate.get("contract_type"),
        "ranking_rank": candidate.get("rank"),
        "ranking_score": score,
        "observed_evidence": observed,
        "strategy_policy_version": strategy_policy.get("version"),
        "risk_policy_version": risk_policy.get("version"),
        "blockers": sorted(set(blockers)),
        "reason_codes": ["SIGNAL_POLICY_OR_RELEASE_GATE_BLOCKED"] if blockers else ["NO_PRODUCTION_ACTION_AUTHORIZED"],
        "buy_sell_signal": "NOT_GENERATED",
    }

def evaluate_shadow_candidates(candidates: list[dict[str, Any]] | None, *, strategy_policy=None,
                               risk_policy=None, production_enabled=False) -> dict[str, Any]:
    items = [evaluate_shadow_candidate(c, strategy_policy=strategy_policy,
                                        risk_policy=risk_policy, production_enabled=production_enabled)
             for c in (candidates or [])]
    return {"status":"PASS","engine_version":SIGNAL_ENGINE_VERSION,
            "production_enabled":bool(production_enabled),"signal_count":len(items),
            "buy_sell_signal":"NOT_GENERATED","items":items,
            "rules":{"ranking_threshold_as_signal":"FORBIDDEN",
                     "missing_evidence":"FAIL_CLOSED",
                     "unversioned_strategy_policy":"BLOCKED",
                     "unversioned_risk_policy":"BLOCKED",
                     "production_without_gate7":"BLOCKED"}}
