#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic Shadow Signal Engine for OptimusAI V4.1.

This module deliberately does not emit a production BUY/SELL signal.
It evaluates whether a candidate has enough evidence and policy state to
permit a future strategy decision. Missing policy/evidence fails closed.
"""
from __future__ import annotations

from typing import Any

SIGNAL_ENGINE_VERSION = "SIGNAL-SHADOW-1.0"

BUY_CALL = "BUY_CALL"
BUY_PUT = "BUY_PUT"
SELL_CALL = "SELL_CALL"
SELL_PUT = "SELL_PUT"
WATCH = "WATCH"
BLOCKED = "BLOCKED"

PRODUCTION_NOT_ENABLED = "PRODUCTION_SIGNAL_NOT_ENABLED"


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        x = float(value)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def evaluate_shadow_candidate(
    candidate: dict[str, Any],
    *,
    strategy_policy: dict[str, Any] | None = None,
    risk_policy: dict[str, Any] | None = None,
    production_enabled: bool = False,
) -> dict[str, Any]:
    """Return a fail-closed, auditable shadow decision for one candidate.

    No score threshold is converted into BUY/SELL. Directional action requires
    an explicitly versioned strategy policy and production release gate.
    """
    strategy_policy = strategy_policy or {}
    risk_policy = risk_policy or {}

    evidence = candidate.get("evidence") or {}
    features = evidence.get("features") or {}
    blockers = list(candidate.get("blockers") or [])

    required_identity = bool(candidate.get("instrument_id")) and (
        candidate.get("contract_type") in {"CALL", "PUT"}
    )
    if not required_identity:
        blockers.append("IDENTITY_OR_CONTRACT_TYPE_UNAVAILABLE")

    if candidate.get("score") is None:
        blockers.append("RANKING_SCORE_UNAVAILABLE")

    if not evidence.get("supported_blocks"):
        blockers.append("NO_SUPPORTED_RANKING_BLOCK")

    if not strategy_policy.get("version"):
        blockers.append("STRATEGY_POLICY_NOT_VERSIONED")

    if not risk_policy.get("version"):
        blockers.append("RISK_POLICY_NOT_VERSIONED")

    if not production_enabled:
        blockers.append(PRODUCTION_NOT_ENABLED)

    # These are evidence observations, never invented values.
    observed = {
        "ranking_score": _num(candidate.get("score")),
        "ranking_rank": candidate.get("rank"),
        "contract_type": candidate.get("contract_type"),
        "calendar_days": _num(features.get("calendar_days")),
        "trade_value": _num(features.get("trade_value")),
        "volume": _num(features.get("volume")),
        "breakeven_distance": _num(features.get("breakeven_distance")),
        "leverage": _num(features.get("leverage")),
        "time_value_ratio": _num(features.get("time_value_ratio")),
        "last_vs_close": _num(features.get("last_vs_close")),
        "intraday_range": _num(features.get("intraday_range")),
    }

    if blockers:
        state = BLOCKED
        proposed_signal = None
    else:
        # Deliberately unreachable for the current release: production is not
        # enabled without a released strategy/risk policy and Gate 7 evidence.
        state = WATCH
        proposed_signal = None

    return {
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
        "state": state,
        "proposed_signal": proposed_signal,
        "production_signal": None,
        "instrument_id": candidate.get("instrument_id"),
        "symbol": candidate.get("symbol"),
        "contract_type": candidate.get("contract_type"),
        "ranking_rank": candidate.get("rank"),
        "ranking_score": candidate.get("score"),
        "observed_evidence": observed,
        "strategy_policy_version": strategy_policy.get("version"),
        "risk_policy_version": risk_policy.get("version"),
        "blockers": sorted(set(blockers)),
        "reason_codes": (
            ["SIGNAL_POLICY_OR_RELEASE_GATE_BLOCKED"]
            if blockers else ["NO_PRODUCTION_ACTION_AUTHORIZED"]
        ),
        "buy_sell_signal": "NOT_GENERATED",
    }


def evaluate_shadow_candidates(
    candidates: list[dict[str, Any]] | None,
    *,
    strategy_policy: dict[str, Any] | None = None,
    risk_policy: dict[str, Any] | None = None,
    production_enabled: bool = False,
) -> dict[str, Any]:
    items = [
        evaluate_shadow_candidate(
            candidate,
            strategy_policy=strategy_policy,
            risk_policy=risk_policy,
            production_enabled=production_enabled,
        )
        for candidate in (candidates or [])
    ]
    return {
        "status": "PASS",
        "engine_version": SIGNAL_ENGINE_VERSION,
        "production_enabled": bool(production_enabled),
        "signal_count": len(items),
        "buy_sell_signal": "NOT_GENERATED",
        "items": items,
        "rules": {
            "ranking_threshold_as_signal": "FORBIDDEN",
            "missing_evidence": "FAIL_CLOSED",
            "unversioned_strategy_policy": "BLOCKED",
            "unversioned_risk_policy": "BLOCKED",
            "production_without_gate7": "BLOCKED",
        },
    }
