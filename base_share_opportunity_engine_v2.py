#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-weighted base-share opportunity scoring, TSETMC-only.

This is a descriptive opportunity-ranking layer, not a buy/sell signal.
Missing evidence is excluded from the denominator; it is never imputed.
"""
from __future__ import annotations
import math
from typing import Any

ENGINE_VERSION = "BASE-SHARE-OPPORTUNITY-ENGINE-V2.0"

WEIGHTS = {
    "trend": 20.0,
    "momentum": 15.0,
    "technical": 15.0,
    "volume_value": 15.0,
    "early_move": 15.0,
    "board": 10.0,
    "entry_quality": 10.0,
}

def num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

def scale_signed(x: float | None, neutral: float, strong: float) -> float | None:
    """Map a signed/continuous indicator to 0..1 without inventing missing data."""
    if x is None:
        return None
    if strong == neutral:
        return None
    return clamp((x - neutral) / (strong - neutral))

def component(values: list[tuple[float | None, float]]) -> dict[str, Any]:
    present = [(clamp(v), w) for v, w in values if v is not None and math.isfinite(v)]
    if not present:
        return {"score": None, "coverage_weight": 0.0, "available_signals": 0}
    total = sum(w for _, w in present)
    return {
        "score": round(sum(v * w for v, w in present) / total * 100.0, 2),
        "coverage_weight": round(total, 2),
        "available_signals": len(present),
    }

def score_opportunity(a: dict[str, Any]) -> dict[str, Any]:
    early = a.get("early_move") if isinstance(a.get("early_move"), dict) else {}
    prelock = early.get("pre_lock_sequence") if isinstance(early.get("pre_lock_sequence"), dict) else {}
    rsi = num(a.get("rsi_14"))
    r5 = num(a.get("return_5_sessions_pct"))
    r20 = num(a.get("return_20_sessions_pct"))
    last = num(a.get("last_price"))
    sma5, sma10 = num(a.get("sma_5")), num(a.get("sma_10"))
    sma20, sma50 = num(a.get("sma_20")), num(a.get("sma_50"))
    macd = num(a.get("macd_12_26"))
    vr, valr = num(a.get("volume_ratio_5_to_20")), num(a.get("value_ratio_5_to_20"))
    power = num(a.get("individual_power_ratio"))
    imbalance = num(a.get("orderbook_imbalance_5"))
    buy_count, sell_count = num(a.get("individual_buy_count")), num(a.get("individual_sell_count"))
    buy_vol, sell_vol = num(a.get("individual_buy_volume")), num(a.get("individual_sell_volume"))
    early_score = num(early.get("score"))
    breakout = early.get("breakout_above_prior_20_high")
    correction = str(a.get("correction_state") or "")
    trend_state = str(a.get("trend_state") or "")

    # Trend structure: use only explicitly calculated averages/state.
    trend_vals = []
    if trend_state == "UP_TREND_STRUCTURE": trend_vals.append((1.0, 3.0))
    elif trend_state == "DOWN_TREND_STRUCTURE": trend_vals.append((0.0, 3.0))
    elif trend_state == "MIXED_STRUCTURE": trend_vals.append((0.5, 3.0))
    if last is not None:
        for ma, w in ((sma20, 2.0), (sma50, 2.0)):
            if ma is not None and ma > 0:
                trend_vals.append((1.0 if last > ma else 0.0, w))
    if sma20 is not None and sma50 is not None and sma50 > 0:
        trend_vals.append((1.0 if sma20 > sma50 else 0.0, 2.0))
    trend = component(trend_vals)

    # Momentum balances short and medium horizons rather than rewarding a single surge.
    momentum_vals = []
    if r5 is not None: momentum_vals.append((scale_signed(r5, -5.0, 5.0), 1.0))
    if r20 is not None: momentum_vals.append((scale_signed(r20, -15.0, 15.0), 1.0))
    p1 = num(early.get("price_change_1_session_pct"))
    p3 = num(early.get("price_change_3_sessions_pct"))
    if p1 is not None: momentum_vals.append((scale_signed(p1, -3.0, 3.0), 0.75))
    if p3 is not None: momentum_vals.append((scale_signed(p3, -6.0, 6.0), 0.75))
    momentum = component(momentum_vals)

    # Technical direction and momentum quality. RSI is deliberately non-monotonic:
    # oversold is not automatically bullish, and overbought does not earn more points.
    technical_vals = []
    if rsi is not None:
        if rsi < 30: rsi_score = 0.35
        elif rsi < 45: rsi_score = 0.55
        elif rsi <= 62: rsi_score = 1.0
        elif rsi <= 70: rsi_score = 0.75
        elif rsi <= 80: rsi_score = 0.35
        else: rsi_score = 0.10
        technical_vals.append((rsi_score, 1.0))
    if macd is not None:
        technical_vals.append((1.0 if macd > 0 else 0.0 if macd < 0 else 0.5, 1.0))
    if last is not None and sma5 is not None and sma10 is not None:
        technical_vals.append((1.0 if last > sma5 > sma10 else 0.7 if last > sma5 else 0.25, 0.75))
    if sma5 is not None and sma10 is not None:
        technical_vals.append((1.0 if sma5 > sma10 else 0.0 if sma5 < sma10 else 0.5, 0.75))
    technical = component(technical_vals)

    # Expansion should be corroborated by volume and traded value, not price alone.
    vv_vals = []
    if vr is not None: vv_vals.append((clamp((vr - 0.6) / 1.0), 1.0))
    if valr is not None: vv_vals.append((clamp((valr - 0.6) / 1.0), 1.0))
    if vr is not None and valr is not None:
        vv_vals.append((1.0 if vr >= 1.0 and valr >= 1.0 else 0.0 if vr < 0.8 and valr < 0.8 else 0.5, 0.5))
    volume_value = component(vv_vals)

    # Early move prioritizes sequence and a confirmed breakout, but does not reward
    # a mature price run simply because historical returns are already high.
    early_vals = []
    if early_score is not None: early_vals.append((clamp((early_score + 100.0) / 200.0), 1.0))
    if breakout is True: early_vals.append((1.0, 1.0))
    elif breakout is False: early_vals.append((0.35, 1.0))
    state = str(prelock.get("state") or "")
    if state == "EARLY": early_vals.append((1.0, 1.5))
    elif state == "DEVELOPING": early_vals.append((0.75, 1.5))
    elif state == "WATCH": early_vals.append((0.55, 1.5))
    elif state == "NO_SEQUENCE_EVIDENCE": early_vals.append((0.25, 1.5))
    early_component = component(early_vals)

    # Board signals are usable only when explicit underlying client-type/order-book
    # data were captured by the TSETMC context layer.
    board_vals = []
    if power is not None: board_vals.append((clamp((power - 0.7) / 1.3), 1.0))
    if buy_count is not None and sell_count not in (None, 0):
        board_vals.append((clamp(((buy_count / sell_count) - 0.5) / 1.5), 0.75))
    if buy_vol is not None and sell_vol not in (None, 0):
        board_vals.append((clamp(((buy_vol / sell_vol) - 0.5) / 1.5), 0.75))
    # BestLimits remains quarantined until its evidence gate passes.
    if imbalance is not None:
        board_vals.append((clamp((imbalance + 1.0) / 2.0), 0.5))
    board = component(board_vals)

    # Entry quality penalizes late/extended moves even when the primary trend is strong.
    entry_vals = []
    if rsi is not None:
        if rsi <= 68: entry_vals.append((1.0, 1.0))
        elif rsi <= 75: entry_vals.append((0.65, 1.0))
        elif rsi <= 82: entry_vals.append((0.30, 1.0))
        else: entry_vals.append((0.10, 1.0))
    if r5 is not None:
        entry_vals.append((1.0 if r5 <= 8 else 0.6 if r5 <= 15 else 0.2, 0.75))
    if r20 is not None:
        entry_vals.append((1.0 if r20 <= 20 else 0.6 if r20 <= 35 else 0.2, 0.75))
    if vr is not None and r5 is not None:
        # Strong price rise on weakening volume is a lower-quality entry.
        entry_vals.append((0.25 if r5 >= 8 and vr < 0.8 else 1.0 if vr >= 0.9 else 0.6, 0.75))
    if correction:
        if correction in {"CORRECTION_IN_UPTREND", "RECOVERY_BOUNCE"}:
            entry_vals.append((0.65, 0.5))
        elif correction in {"CORRECTION", "COUNTERTREND_BOUNCE_IN_DOWNTREND"}:
            entry_vals.append((0.25, 0.5))
    entry_quality = component(entry_vals)

    components = {
        "trend": trend,
        "momentum": momentum,
        "technical": technical,
        "volume_value": volume_value,
        "early_move": early_component,
        "board": board,
        "entry_quality": entry_quality,
    }
    available_weight = sum(WEIGHTS[k] for k, v in components.items() if v["score"] is not None)
    if available_weight <= 0:
        final_score = None
    else:
        final_score = sum((components[k]["score"] / 100.0) * WEIGHTS[k]
                          for k in components if components[k]["score"] is not None) / available_weight * 100.0

    # Confidence reflects evidence coverage, not predicted probability.
    coverage = available_weight / sum(WEIGHTS.values()) * 100.0
    if final_score is None: confidence = "INSUFFICIENT_DATA"
    elif coverage >= 75: confidence = "HIGH_EVIDENCE_COVERAGE"
    elif coverage >= 45: confidence = "MEDIUM_EVIDENCE_COVERAGE"
    else: confidence = "LOW_EVIDENCE_COVERAGE"

    if final_score is None: category = "C"
    elif final_score >= 75 and (rsi is None or rsi <= 75): category = "A"
    elif final_score >= 55: category = "B"
    else: category = "C"

    warnings = []
    if rsi is not None and rsi > 70: warnings.append("RSI_OVERBOUGHT_ENTRY_PENALTY")
    if rsi is not None and rsi > 80: warnings.append("RSI_EXTREME_OVERBOUGHT")
    if r5 is not None and r5 >= 8 and vr is not None and vr < 0.8:
        warnings.append("PRICE_RUN_WITH_WEAK_VOLUME")
    if correction in {"CORRECTION", "COUNTERTREND_BOUNCE_IN_DOWNTREND"}:
        warnings.append("CORRECTION_OR_COUNTERTREND_RISK")
    if coverage < 45: warnings.append("LOW_EVIDENCE_COVERAGE")

    return {
        "engine_version": ENGINE_VERSION,
        "final_score": round(final_score, 2) if final_score is not None else None,
        "classification": category,
        "confidence": confidence,
        "evidence_coverage_pct": round(coverage, 2),
        "components": components,
        "weights": WEIGHTS,
        "rsi_14": rsi,
        "return_5_sessions_pct": r5,
        "return_20_sessions_pct": r20,
        "trend_state": trend_state or None,
        "correction_state": correction or None,
        "warnings": warnings,
        "unavailable_families": [k for k, v in components.items() if v["score"] is None],
        "policy": {
            "source_of_truth": "TSETMC",
            "missing_data": "EXCLUDED_FROM_DENOMINATOR_NO_IMPUTATION",
            "bestlimits": "QUARANTINED_UNTIL_EVIDENCE_GATE_PASSES",
            "fundamental_data": "NOT_IN_CURRENT_CONTEXT_NOT_SCORED",
            "strategy_fit": "NOT_BACKTESTED_NOT_SCORED",
            "buy_sell_signal": "NOT_GENERATED",
        },
    }
