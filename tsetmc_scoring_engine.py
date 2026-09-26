#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-backed TSETMC ranking layer.

This is deliberately separate from the historical scoring_engine.py.
It uses only fields present in the canonical TSETMC snapshot or deterministic
derivations from those fields. Missing evidence stays unavailable; no external
source, guessed parameter, IV, Greeks, risk-free rate, or OI is fabricated.

The six-block weights remain the V4.1 weights:
Liquidity 20, Valuation 25, Payoff 18, Time 15, Greeks 12, Market 10.
Unavailable factors are redistributed only inside their block; blocks with no
supported factor are excluded and the remaining block weights are normalized
to 100. This is reported explicitly as TSETMC_EVIDENCE_RANKING.
"""
from __future__ import annotations
import math
from typing import Any

BLOCK_WEIGHTS = {
    "LIQUIDITY": 20.0,
    "VALUATION": 25.0,
    "PAYOFF": 18.0,
    "TIME": 15.0,
    "GREEKS": 12.0,
    "MARKET": 10.0,
}

FACTOR_WEIGHTS = {
    "LIQUIDITY": {"trade_value": 7.0, "volume": 5.0},
    # Valuation is a relative premium-burden proxy, not fair value.
    # It uses only TSETMC: time value as a fraction of the underlying price;
    # lower is treated as better. No IV/theoretical value is implied.
    "VALUATION": {"time_value_ratio": 5.0},
    "PAYOFF": {"breakeven_distance": 10.0, "leverage": 5.0, "moneyness": 3.0},
    "TIME": {"calendar_days": 2.0},
    "GREEKS": {},
    "MARKET": {"last_vs_close": 4.0, "intraday_range": 3.0},
}


def _num(v):
    try:
        if v in (None, ""):
            return None
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _pct_rank(values, higher=True):
    valid = sorted((v for v in values if v is not None))
    if not valid:
        return [None] * len(values)
    if len(valid) == 1:
        only = valid[0]
        return [1.0 if v == only else None for v in values]
    out = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        rank = sum(1 for x in valid if x <= v) / len(valid)
        out.append(rank if higher else 1.0 - rank + 1.0 / len(valid))
    return [max(0.0, min(1.0, x)) if x is not None else None for x in out]


def _derived(row):
    c = row.get("canonical") or {}
    ident = row.get("identity") or {}
    typ = str(ident.get("contract_type") or "").upper()
    S = _num(c.get("قیمت سهم پایه"))
    K = _num(c.get("قیمت اعمال"))
    P = _num(c.get("آخرین قیمت"))
    close = _num(c.get("قیمت پایانی"))
    high = _num(c.get("بیشترین قیمت"))
    low = _num(c.get("کمترین قیمت"))
    days = _num(c.get("روزهای تقویمی"))
    tv = None
    intrinsic = None
    breakeven = None
    leverage = None
    moneyness = None
    time_value_ratio = None
    if typ in {"CALL", "PUT"} and S is not None and K is not None and P is not None:
        intrinsic = max(S - K, 0.0) if typ == "CALL" else max(K - S, 0.0)
        tv = max(P - intrinsic, 0.0)
        breakeven = K + P if typ == "CALL" else K - P
        if P > 0:
            leverage = S / P
        moneyness = abs(S - K) / K if K > 0 else None
        time_value_ratio = tv / abs(S) if S not in (None, 0) else None
    return {
        "trade_value": _num(c.get("ارزش معاملات")),
        "volume": _num(c.get("حجم معاملات")),
        "time_value": tv,
        "time_value_ratio": time_value_ratio,
        "breakeven_distance": (
            abs(breakeven - S) / abs(S) if breakeven is not None and S not in (None, 0) else None
        ),
        "leverage": leverage,
        "moneyness": moneyness,
        "calendar_days": days,
        "last_vs_close": (
            abs(P - close) / abs(close) if P is not None and close not in (None, 0) else None
        ),
        "intraday_range": (
            abs(high - low) / abs(P) if high is not None and low is not None and P not in (None, 0) else None
        ),
        "contract_type": typ or None,
        "evidence": {
            "contract_type": "TSETMC:contract_type" if typ in {"CALL", "PUT"} else None,
            "time_value": "derived:TSETMC(S,K,last,contract_type)",
            "time_value_ratio": "derived:TSETMC(time_value,S)",
            "breakeven_distance": "derived:TSETMC(S,K,last,contract_type)",
            "leverage": "derived:TSETMC(S,last)",
            "moneyness": "derived:TSETMC(S,K,contract_type)",
            "last_vs_close": "derived:TSETMC(last,close)",
            "intraday_range": "derived:TSETMC(high,low,last)",
        },
    }


def build_evidence_ranking(rows, *, disabled_factors=None, disabled_blocks=None):
    """Build ranking; optional ablations are audit-only and default to production behavior."""
    rows = list(rows or [])
    disabled_factors = {str(x) for x in (disabled_factors or [])}
    disabled_blocks = {str(x) for x in (disabled_blocks or [])}
    derived = [_derived(r) for r in rows]
    scores = {b: {} for b in BLOCK_WEIGHTS}
    for block, factors in FACTOR_WEIGHTS.items():
        if block in disabled_blocks:
            continue
        for factor, weight in factors.items():
            if factor in disabled_factors:
                continue
            vals = [d.get(factor) for d in derived]
            higher = factor in {"trade_value", "volume", "leverage"}
            # Lower distance/range/calendar-days is treated as better, matching the
            # established time/opportunity scoring direction.
            scores[block][factor] = _pct_rank(vals, higher=higher)

    block_scores = []
    availability = {}
    for i, d in enumerate(derived):
        bs = {}
        for block, factors in FACTOR_WEIGHTS.items():
            if block in disabled_blocks:
                bs[block] = None
                continue
            numerator = 0.0
            available_weight = 0.0
            for factor, weight in factors.items():
                if factor in disabled_factors:
                    continue
                s = scores[block][factor][i]
                if s is not None:
                    numerator += s * weight
                    available_weight += weight
            bs[block] = (numerator / available_weight * BLOCK_WEIGHTS[block]) if available_weight else None
        # Greeks are explicitly unavailable from this TSETMC snapshot.
        bs["GREEKS"] = None
        block_scores.append(bs)

    supported_blocks = [
        b for b in BLOCK_WEIGHTS
        if any(x.get(b) is not None for x in block_scores)
    ]
    total_supported_weight = sum(BLOCK_WEIGHTS[b] for b in supported_blocks)
    ranked = []
    for i, row in enumerate(rows):
        available = [b for b in supported_blocks if block_scores[i].get(b) is not None]
        if not available:
            final = None
        else:
            # Normalize only across blocks with actual evidence for this row.
            denom = sum(BLOCK_WEIGHTS[b] for b in available)
            final = sum(block_scores[i][b] for b in available) * 100.0 / denom
        evidence = derived[i]["evidence"]
        ranked.append({
            "rank": None,
            "instrument_id": (row.get("identity") or {}).get("instrument_id"),
            "symbol": (row.get("canonical") or {}).get("نماد"),
            "contract_type": derived[i]["contract_type"],
            "score": round(final, 4) if final is not None else None,
            "supported_blocks": available,
            "unavailable_blocks": [b for b in BLOCK_WEIGHTS if b not in available],
            "block_scores": {b: (round(block_scores[i][b], 4) if block_scores[i][b] is not None else None) for b in BLOCK_WEIGHTS},
            "features": {
                k: (round(v, 8) if isinstance(v, float) else v)
                for k, v in derived[i].items() if k != "evidence"
            },
            "feature_evidence": evidence,
        })
    ranked.sort(key=lambda x: (x["score"] is not None, x["score"] if x["score"] is not None else -1), reverse=True)
    for n, item in enumerate(ranked, 1):
        item["rank"] = n if item["score"] is not None else None
    return {
        "status": "PASS" if ranked and any(x["score"] is not None for x in ranked) else "NO_RANKABLE_EVIDENCE",
        "mode": "TSETMC_EVIDENCE_RANKING",
        "source_of_truth": "TSETMC",
        "external_comparison_source": None,
        "weights": BLOCK_WEIGHTS,
        "supported_blocks": supported_blocks,
        "unsupported_blocks": [b for b in BLOCK_WEIGHTS if b not in supported_blocks],
        "supported_weight_total": total_supported_weight,
        "ranking_rows": ranked,
        "ranking_scope": "OPPORTUNITY_CANDIDATES",
        "ranking_scope_row_count": len(rows),
        "rules": {
            "missing_data": "UNAVAILABLE_NOT_ZERO",
            "external_source": "FORBIDDEN",
            "contract_type": "TSETMC_EXPLICIT_ONLY",
            "iv": "NOT_COMPUTED",
            "greeks": "NOT_COMPUTED",
            "open_interest": "NOT_USED",
            "risk_free_rate": "NOT_USED",
            "buy_sell_signal": "NOT_GENERATED",
        },
    }
