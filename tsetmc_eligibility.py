#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Explicit TSETMC eligibility and opportunity-candidate gate.

This layer does not score profitability and does not generate buy/sell signals.
It only classifies each canonical TSETMC option row from explicit activity
evidence. No arbitrary volume/value thresholds are introduced.
"""
from __future__ import annotations

from typing import Any

INSUFFICIENT_ACTIVITY_EVIDENCE = "INSUFFICIENT_ACTIVITY_EVIDENCE"
RANKABLE = "RANKABLE"
OPPORTUNITY_CANDIDATE = "OPPORTUNITY_CANDIDATE"


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        result = float(value)
        return result if result == result else None
    except (TypeError, ValueError):
        return None


def _activity(row: dict[str, Any]) -> dict[str, Any]:
    canonical = row.get("canonical") or {}
    market = row.get("market_watch_fields") or {}
    raw = row.get("raw_market_watch") or {}

    volume = _num(canonical.get("حجم معاملات"))
    trade_count = _num(
        canonical.get("تعداد معاملات")
        if "تعداد معاملات" in canonical
        else market.get("trade_count")
    )
    bid_qty = _num(
        canonical.get("حجم بهترین تقاضا")
        if "حجم بهترین تقاضا" in canonical
        else market.get("bid_quantity")
    )
    ask_qty = _num(
        canonical.get("حجم بهترین عرضه")
        if "حجم بهترین عرضه" in canonical
        else market.get("ask_quantity")
    )

    # raw Market-Watch is retained as evidence, but canonical fields are
    # preferred. The adapter currently stores normalized market fields inside
    # the instrument record only; tolerate either representation.
    if not market:
        mw = raw.get("market_watch_fields")
        if isinstance(mw, dict):
            market = mw

    traded = volume is not None and volume > 0 and trade_count is not None and trade_count > 0
    two_sided_depth = (
        bid_qty is not None and bid_qty > 0
        and ask_qty is not None and ask_qty > 0
    )

    return {
        "volume": volume,
        "trade_count": trade_count,
        "bid_quantity": bid_qty,
        "ask_quantity": ask_qty,
        "traded": traded,
        "two_sided_depth": two_sided_depth,
        "volume_evidence": "TSETMC:حجم معاملات" if volume is not None else None,
        "trade_count_evidence": "TSETMC:تعداد معاملات" if trade_count is not None else None,
        "depth_evidence": (
            "TSETMC:حجم بهترین تقاضا+حجم بهترین عرضه"
            if two_sided_depth else None
        ),
    }


def classify_eligibility(row: dict[str, Any]) -> dict[str, Any]:
    canonical = row.get("canonical") or {}
    identity = row.get("identity") or {}
    activity = _activity(row)

    # A row with explicit traded activity or explicit two-sided Market-Watch
    # depth has enough activity evidence to become an opportunity candidate.
    if activity["traded"] or activity["two_sided_depth"]:
        state = OPPORTUNITY_CANDIDATE
        reason = "EXPLICIT_TSETMC_ACTIVITY_OR_TWO_SIDED_DEPTH"
    elif (
        activity["volume"] == 0
        or activity["trade_count"] == 0
    ):
        state = INSUFFICIENT_ACTIVITY_EVIDENCE
        reason = "ZERO_TSETMC_ACTIVITY"
    elif activity["volume"] is None and activity["trade_count"] is None:
        state = INSUFFICIENT_ACTIVITY_EVIDENCE
        reason = "ACTIVITY_EVIDENCE_UNAVAILABLE"
    else:
        state = RANKABLE
        reason = "ACTIVITY_PRESENT_BUT_CANDIDATE_RULE_NOT_SATISFIED"

    return {
        "state": state,
        "reason": reason,
        "instrument_id": identity.get("instrument_id"),
        "symbol": canonical.get("نماد"),
        "contract_type": identity.get("contract_type"),
        "activity": activity,
        "opportunity_eligible": state == OPPORTUNITY_CANDIDATE,
        "buy_sell_signal": False,
    }


def classify_universe(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    items = [classify_eligibility(row) for row in (rows or [])]
    counts = {
        INSUFFICIENT_ACTIVITY_EVIDENCE: sum(
            x["state"] == INSUFFICIENT_ACTIVITY_EVIDENCE for x in items
        ),
        RANKABLE: sum(x["state"] == RANKABLE for x in items),
        OPPORTUNITY_CANDIDATE: sum(
            x["state"] == OPPORTUNITY_CANDIDATE for x in items
        ),
    }
    return {
        "status": "PASS",
        "source_of_truth": "TSETMC",
        "rules_version": "ELIGIBILITY-1.0",
        "arbitrary_thresholds": False,
        "rows_evaluated": len(items),
        "counts": counts,
        "candidate_instrument_ids": [
            x["instrument_id"] for x in items
            if x["state"] == OPPORTUNITY_CANDIDATE
        ],
        "items": items,
        "rules": {
            "zero_volume_or_zero_trade_count": INSUFFICIENT_ACTIVITY_EVIDENCE,
            "missing_activity": INSUFFICIENT_ACTIVITY_EVIDENCE,
            "two_sided_depth": "TSETMC_EXPLICIT_BID_ASK_QUANTITY_ONLY",
            "profitability_score": "NOT_COMPUTED",
            "buy_sell_signal": "NOT_GENERATED",
        },
    }

def build_opportunity_candidates(
    rows: list[dict[str, Any]] | None,
    ranking: dict[str, Any] | None,
    eligibility: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build deterministic TSETMC-native opportunity cases from eligible rows.

    This layer does not create a new profitability score or a trading signal.
    It joins explicit activity eligibility with the already-computed evidence
    ranking and exposes only auditable observed/derived features.
    """
    rows = list(rows or [])
    ranking = ranking or {}
    eligibility = eligibility or {}
    candidate_ids = set(eligibility.get("candidate_instrument_ids") or [])
    ranking_by_id = {
        item.get("instrument_id"): item
        for item in ranking.get("ranking_rows", [])
        if item.get("instrument_id") is not None
    }

    cases = []
    for row in rows:
        identity = row.get("identity") or {}
        instrument_id = identity.get("instrument_id")
        if instrument_id not in candidate_ids:
            continue

        canonical = row.get("canonical") or {}
        activity = classify_eligibility(row)["activity"]
        ranked = ranking_by_id.get(instrument_id, {})
        features = ranked.get("features") or {}

        evidence = {
            "activity": activity,
            "ranking_score": ranked.get("score"),
            "ranking_rank": ranked.get("rank"),
            "supported_blocks": ranked.get("supported_blocks", []),
            "features": features,
        }

        blockers = []
        if ranked.get("score") is None:
            blockers.append("NO_RANKING_SCORE")
        if not ranked.get("supported_blocks"):
            blockers.append("NO_SUPPORTED_SCORING_BLOCK")
        if features.get("contract_type") not in {"CALL", "PUT"}:
            blockers.append("EXPLICIT_CONTRACT_TYPE_UNAVAILABLE")

        cases.append({
            "instrument_id": instrument_id,
            "symbol": canonical.get("نماد"),
            "contract_type": identity.get("contract_type"),
            "status": "EVIDENCE_BACKED_CANDIDATE" if not blockers else "CANDIDATE_WITH_BLOCKERS",
            "rank": ranked.get("rank"),
            "score": ranked.get("score"),
            "evidence": evidence,
            "blockers": blockers,
            "buy_sell_signal": False,
        })

    cases.sort(key=lambda x: (
        x.get("rank") is None,
        x.get("rank") if x.get("rank") is not None else 10**9,
        str(x.get("instrument_id") or ""),
    ))

    return {
        "status": "SUCCESS",
        "engine_version": "TSETMC-OPPORTUNITY-1.0",
        "source_of_truth": "TSETMC",
        "rows_evaluated": len(rows),
        "candidate_count": len(cases),
        "cases": cases,
        "rules": {
            "selection_basis": "OPPORTUNITY_CANDIDATE_PLUS_TSETMC_EVIDENCE_RANKING",
            "new_profitability_threshold": False,
            "buy_sell_signal": "NOT_GENERATED",
            "missing_data": "UNAVAILABLE_NOT_ZERO",
            "external_source": "FORBIDDEN",
        },
    }
\n