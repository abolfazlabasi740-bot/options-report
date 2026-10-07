#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage-1 underlying intelligence from existing TSETMC evidence.

This module is deliberately conservative. It combines already-supported
TSETMC trend, momentum, volume, board and limit features into a descriptive
bias. It does not generate BUY/SELL signals and does not yet introduce
adaptive learning or additional indicators. Those belong to later stages.
"""

from __future__ import annotations
import math
from typing import Any

ENGINE_VERSION = "TSETMC-UNDERLYING-INTELLIGENCE-1.2-CORRECTION-DIRECTIONAL-PRELOCK"

def _num(v: Any) -> float | None:
    try:
        if v in (None, ""):
            return None
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None

def _vote(value: float | None, bullish: bool, bearish: bool) -> int:
    if value is None:
        return 0
    if bullish:
        return 1
    if bearish:
        return -1
    return 0

def analyze_underlying(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {"status": "UNAVAILABLE", "engine_version": ENGINE_VERSION}

    evidence = []
    score = 0.0
    available = 0

    # Early-move is a shadow analytical layer: it describes CHANGE + SEQUENCE
    # but does not alter the Stage-1 direction score or gate.
    early = context.get("early_move") or {}
    early_score = _num(early.get("score"))
    early_state = str(early.get("state") or "")
    if early_score is not None:
        if early_score > 0:
            early_direction = 1
        elif early_score < 0:
            early_direction = -1
        else:
            early_direction = 0
        evidence.append((
            "EARLY_MOVE",
            early_direction,
            f"امتیاز تغییرات زودهنگام={early_score:.1f} | وضعیت={early_state} | "
            f"تغییر 1 جلسه={early.get('price_change_1_session_pct', 'N/A')}% | "
            f"شیب SMA20 در 5 جلسه={early.get('sma20_slope_5_sessions_pct', 'N/A')}%"
        ))

    prelock = context.get("early_move", {}).get("pre_lock_sequence") or {}
    if prelock.get("status") == "PASS":
        raw_direction = str(prelock.get("sequence_direction") or "UNAVAILABLE").upper()
        bias_hint = str(context.get("trend_state") or "").upper()
        if raw_direction == "BULLISH":
            sequence_alignment = "BULLISH_SEQUENCE"
        elif raw_direction == "BEARISH":
            sequence_alignment = "BEARISH_SEQUENCE"
        elif raw_direction == "MIXED":
            sequence_alignment = "CONFLICTED_SEQUENCE"
        else:
            sequence_alignment = "DIRECTION_UNAVAILABLE"
        evidence.append((
            "PRE_LOCK_SEQUENCE",
            0,
            f"وضعیت پیش‌قفلی={prelock.get('state', 'N/A')} | توالی={prelock.get('sequence', 'N/A')} | "
            f"جهت توالی={raw_direction} | اعتبارسنجی={sequence_alignment} | "
            f"اعتماد={prelock.get('confidence', 'N/A')} | دانه‌بندی={prelock.get('data_granularity', 'N/A')}"
        ))

    # Correction is a separate state from primary direction.
    correction_state = str(context.get("correction_state") or "")
    correction_confidence = str(context.get("correction_confidence") or "")
    correction_active = bool(context.get("correction_active"))
    correction_from_peak = _num(context.get("correction_from_prior_peak_pct"))
    if correction_active:
        evidence.append((
            "CORRECTION", 0,
            f"وضعیت پایه={correction_state} | اعتماد={correction_confidence} | "
            f"افت از سقف اخیر={correction_from_peak:.2f}%"
            if correction_from_peak is not None
            else f"وضعیت پایه={correction_state} | اعتماد={correction_confidence}"
        ))

    trend = str(context.get("trend_state") or "")
    if trend == "UP_TREND_STRUCTURE":
        score += 20
        available += 1
        evidence.append(("TREND", 1, "قیمت بالای SMA20 و ساختار SMA20 بالای SMA50"))
    elif trend == "DOWN_TREND_STRUCTURE":
        score -= 20
        available += 1
        evidence.append(("TREND", -1, "قیمت زیر SMA20 و ساختار SMA20 زیر SMA50"))
    elif trend:
        available += 1
        evidence.append(("TREND", 0, "ساختار روند ترکیبی"))

    last = _num(context.get("last_price"))
    sma5 = _num(context.get("sma_5"))
    sma10 = _num(context.get("sma_10"))
    sma20 = _num(context.get("sma_20"))
    sma50 = _num(context.get("sma_50"))

    ma_score = 0
    ma_pairs = 0
    for ma, label in ((sma5, "SMA5"), (sma10, "SMA10"), (sma20, "SMA20"), (sma50, "SMA50")):
        if last is not None and ma is not None:
            ma_pairs += 1
            ma_score += 1 if last > ma else -1 if last < ma else 0
    if ma_pairs:
        normalized = ma_score / ma_pairs
        score += normalized * 15
        available += 1
        evidence.append(("MA", 1 if normalized > 0.25 else -1 if normalized < -0.25 else 0,
                         f"جایگاه قیمت نسبت به میانگین‌های موجود: {ma_score}/{ma_pairs}"))

    rsi = _num(context.get("rsi_14"))
    if rsi is not None:
        available += 1
        if rsi >= 55:
            score += 10
            direction = 1
        elif rsi <= 45:
            score -= 10
            direction = -1
        else:
            direction = 0
        evidence.append(("RSI", direction, f"RSI14={rsi:.2f}"))

    macd = _num(context.get("macd_12_26"))
    if macd is not None:
        available += 1
        direction = 1 if macd > 0 else -1 if macd < 0 else 0
        score += direction * 12
        evidence.append(("MACD", direction, f"MACD12/26={macd:.4f}"))

    r5 = _num(context.get("return_5_sessions_pct"))
    r20 = _num(context.get("return_20_sessions_pct"))
    if r5 is not None or r20 is not None:
        available += 1
        values = [x for x in (r5, r20) if x is not None]
        direction = 1 if sum(values) > 0 else -1 if sum(values) < 0 else 0
        score += max(-1, min(1, sum(values) / 10.0)) * 10
        evidence.append(("PRICE_MOMENTUM", direction,
                         f"بازده 5/20 جلسه‌ای: {r5 if r5 is not None else 'N/A'} / {r20 if r20 is not None else 'N/A'}"))

    vr = _num(context.get("volume_ratio_5_to_20"))
    valr = _num(context.get("value_ratio_5_to_20"))
    if vr is not None or valr is not None:
        available += 1
        values = [x for x in (vr, valr) if x is not None]
        direction = 1 if sum(values) / len(values) > 1.05 else -1 if sum(values) / len(values) < 0.95 else 0
        score += direction * 8
        evidence.append(("VOLUME_VALUE", direction,
                         f"نسبت حجم/ارزش 5 به 20: {vr if vr is not None else 'N/A'} / {valr if valr is not None else 'N/A'}"))

    imbalance = _num(context.get("orderbook_imbalance_5"))
    power = _num(context.get("individual_power_ratio"))
    if imbalance is not None or power is not None:
        available += 1
        board_score = 0
        if imbalance is not None:
            board_score += 1 if imbalance > 0.10 else -1 if imbalance < -0.10 else 0
        if power is not None:
            board_score += 1 if power > 1.10 else -1 if power < 0.90 else 0
        direction = 1 if board_score > 0 else -1 if board_score < 0 else 0
        score += direction * 15
        evidence.append(("BOARD", direction,
                         f"عدم‌تعادل سفارش={imbalance if imbalance is not None else 'N/A'} | قدرت حقیقی={power if power is not None else 'N/A'}"))

    headroom = _num(context.get("upper_limit_headroom_pct"))
    touched = context.get("touched_upper_limit_today")
    if touched is True:
        score += 5
        evidence.append(("LIMIT_STATE", 1, "سقف روزانه لمس شده است"))
    elif headroom is not None and headroom <= 2:
        score += 3
        evidence.append(("LIMIT_STATE", 1, f"فاصله تا سقف={headroom:.2f}%"))
    elif headroom is not None and headroom >= 8:
        evidence.append(("LIMIT_STATE", 0, f"فاصله تا سقف={headroom:.2f}%"))

    if available == 0:
        return {
            "status": "UNAVAILABLE",
            "engine_version": ENGINE_VERSION,
            "source_of_truth": "TSETMC",
            "bias": "INSUFFICIENT_DATA",
            "confidence": "LOW",
            "score": None,
            "evidence_count": 0,
            "evidence": [],
            "interpretation": "DESCRIPTIVE_ONLY_NOT_A_BUY_SELL_SIGNAL",
        }

    # The score is intentionally bounded and is a descriptive evidence score,
    # not a probability or expected return.
    bounded = max(-100.0, min(100.0, score))
    if bounded >= 35:
        bias = "BULLISH"
    elif bounded <= -35:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Explicit conflict check across independent evidence families.
    signs = [x[1] for x in evidence if x[1] != 0]
    positive = sum(1 for x in signs if x > 0)
    negative = sum(1 for x in signs if x < 0)
    if positive and negative and min(positive, negative) >= 2:
        bias = "CONFLICTED"

    confidence = (
        "HIGH" if abs(bounded) >= 55 and max(positive, negative) >= 4
        else "MEDIUM" if abs(bounded) >= 30 and max(positive, negative) >= 3
        else "LOW"
    )

    return {
        "status": "PASS",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": "TSETMC",
        "bias": bias,
        "confidence": confidence,
        "score": round(bounded, 2),
        "evidence_count": len(evidence),
        "bullish_evidence_count": positive,
        "bearish_evidence_count": negative,
        "evidence": [
            {"family": family, "direction": direction, "detail": detail}
            for family, direction, detail in evidence
        ],
        "rules": {
            "missing_data": "UNAVAILABLE_NOT_ZERO",
            "buy_sell_signal": "NOT_GENERATED",
            "adaptive_learning": "NOT_IN_STAGE_1",
            "additional_indicators": "DEFERRED_TO_LATER_STAGE",
            "early_move": "SHADOW_ONLY_CHANGE_SEQUENCE_NOT_A_GATE",
            "pre_lock_sequence": "SHADOW_ONLY_SESSION_SEQUENCE_WITH_DIRECTION_VALIDATION_NOT_A_GATE",
            "correction_state": "DESCRIPTIVE_SEPARATE_FROM_PRIMARY_BIAS",
        },
        "interpretation": "DESCRIPTIVE_UNDERLYING_BIAS_ONLY_NOT_A_BUY_SELL_SIGNAL",
    }

def build_underlying_intelligence(context_map: dict[str, Any]) -> dict[str, Any]:
    instruments = {}
    for instrument_id, context in (context_map or {}).items():
        instruments[str(instrument_id)] = analyze_underlying(context)
    statuses = [x.get("status") for x in instruments.values()]
    return {
        "status": "PASS" if instruments and all(x in {"PASS", "PARTIAL"} for x in statuses) else "PARTIAL" if instruments else "UNAVAILABLE",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": "TSETMC",
        "instrument_count": len(instruments),
        "instruments": instruments,
        "production_signal": "OFF",
        "stage": "STAGE_1",
    }
