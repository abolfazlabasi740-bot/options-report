#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descriptive underlying-stock trend features from retained TSETMC daily history."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from tsetmc_adapter import TSETMCAdapter

ENGINE_VERSION = "TSETMC-UNDERLYING-TREND-1.2-CORRECTION-PRELOCK"
TEHRAN = ZoneInfo("Asia/Tehran")


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        result = float(value)
        return result if result == result and abs(result) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    value = sum(values[:period]) / period
    for item in values[period:]:
        value = alpha * item + (1.0 - alpha) * value
    return value


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    if len(changes) < period:
        return None
    gains = [max(x, 0.0) for x in changes]
    losses = [max(-x, 0.0) for x in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    relative = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative))


def _record_date(row: dict[str, Any]) -> str | None:
    try:
        return f"{int(row.get('dEven')):08d}"
    except (TypeError, ValueError):
        return None


def analyze_history(instrument_id: str, history_response: dict[str, Any], info_response: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = history_response.get("data")
    if not isinstance(raw, list):
        return {
            "status": "UNAVAILABLE",
            "instrument_id": str(instrument_id),
            "reason": "TSETMC_DAILY_HISTORY_NOT_LIST",
            "source": "TSETMC",
            "engine_version": ENGINE_VERSION,
        }

    records = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        if str(row.get("insCode") or "").strip() != str(instrument_id):
            continue
        date_key = _record_date(row)
        close = _num(row.get("pClosing"))
        if date_key and close is not None and close > 0:
            records.append((date_key, row))
    records.sort(key=lambda item: item[0])
    rows = [item[1] for item in records]
    closes = [_num(row.get("pClosing")) for row in rows]
    closes = [x for x in closes if x is not None]
    volumes = [_num(row.get("qTotTran5J")) for row in rows]
    volumes = [x for x in volumes if x is not None]
    values = [_num(row.get("qTotCap")) for row in rows]
    values = [x for x in values if x is not None]
    latest = rows[-1] if rows else {}
    latest_date = _record_date(latest)
    today = datetime.now(TEHRAN).strftime("%Y%m%d")

    sma5 = _sma(closes, 5)
    sma10 = _sma(closes, 10)
    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    last_close = closes[-1] if closes else None
    rsi14 = _rsi(closes, 14)
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd = ema12 - ema26 if ema12 is not None and ema26 is not None else None

    return_5 = (
        (closes[-1] / closes[-6] - 1.0) * 100.0
        if len(closes) >= 6 and closes[-6] else None
    )
    return_20 = (
        (closes[-1] / closes[-21] - 1.0) * 100.0
        if len(closes) >= 21 and closes[-21] else None
    )
    volume_ratio = (
        (_sma(volumes, 5) / _sma(volumes, 20))
        if _sma(volumes, 5) is not None and _sma(volumes, 20) not in (None, 0)
        else None
    )
    volume_ratio_5_to_50 = (
        (_sma(volumes, 5) / _sma(volumes, 50))
        if _sma(volumes, 5) is not None and _sma(volumes, 50) not in (None, 0)
        else None
    )
    value_ratio = (
        (_sma(values, 5) / _sma(values, 20))
        if _sma(values, 5) is not None and _sma(values, 20) not in (None, 0)
        else None
    )
    # Early-move evidence is deliberately shadow-only. It measures change and
    # sequence from retained TSETMC daily history; it does not generate a
    # BUY/SELL signal and does not alter Stage-1 direction eligibility.
    prev_closes = closes[:-1]
    price_change_1 = (
        (closes[-1] / closes[-2] - 1.0) * 100.0
        if len(closes) >= 2 and closes[-2] else None
    )
    price_change_3 = (
        (closes[-1] / closes[-4] - 1.0) * 100.0
        if len(closes) >= 4 and closes[-4] else None
    )
    sma20_slope_5_pct = (
        (sma20 / _sma(closes[:-5], 20) - 1.0) * 100.0
        if len(closes) >= 25 and _sma(closes[:-5], 20) not in (None, 0)
        else None
    )
    rsi_prev = _rsi(prev_closes, 14)
    rsi_change_1 = rsi14 - rsi_prev if rsi14 is not None and rsi_prev is not None else None
    ema12_prev = _ema(prev_closes, 12)
    ema26_prev = _ema(prev_closes, 26)
    macd_prev = (
        ema12_prev - ema26_prev
        if ema12_prev is not None and ema26_prev is not None
        else None
    )
    macd_change = macd - macd_prev if macd is not None and macd_prev is not None else None
    volume_ratio_prev = (
        (_sma(volumes[:-1], 5) / _sma(volumes[:-1], 20))
        if len(volumes) >= 21 and _sma(volumes[:-1], 5) is not None
        and _sma(volumes[:-1], 20) not in (None, 0)
        else None
    )
    volume_ratio_change = (
        volume_ratio - volume_ratio_prev
        if volume_ratio is not None and volume_ratio_prev is not None
        else None
    )
    prior_20_high = max(
        (_num(row.get("priceMax")) for row in rows[-21:-1] if _num(row.get("priceMax")) is not None),
        default=None,
    )
    breakout_20 = (
        last_close > prior_20_high
        if last_close is not None and prior_20_high is not None
        else None
    )
    early_components = []
    if price_change_1 is not None:
        early_components.append(1 if price_change_1 > 0 else -1 if price_change_1 < 0 else 0)
    if price_change_3 is not None:
        early_components.append(1 if price_change_3 > 0 else -1 if price_change_3 < 0 else 0)
    if sma20_slope_5_pct is not None:
        early_components.append(1 if sma20_slope_5_pct > 0.5 else -1 if sma20_slope_5_pct < -0.5 else 0)
    if rsi_change_1 is not None:
        early_components.append(1 if rsi_change_1 > 1 else -1 if rsi_change_1 < -1 else 0)
    if macd_change is not None:
        early_components.append(1 if macd_change > 0 else -1 if macd_change < 0 else 0)
    if volume_ratio_change is not None:
        early_components.append(1 if volume_ratio_change > 0.10 else -1 if volume_ratio_change < -0.10 else 0)
    if breakout_20 is not None:
        early_components.append(1 if breakout_20 else 0)
    early_score = (
        round(sum(early_components) / len(early_components) * 100.0, 2)
        if early_components else None
    )
    positive_early = sum(1 for x in early_components if x > 0)
    negative_early = sum(1 for x in early_components if x < 0)
    if early_score is None:
        early_state = "INSUFFICIENT_EVIDENCE"
    elif positive_early >= 4 and positive_early > negative_early:
        early_state = "EARLY_UPSIDE_CONFIRMATION"
    elif negative_early >= 4 and negative_early > positive_early:
        early_state = "EARLY_DOWNSIDE_CONFIRMATION"
    elif positive_early > negative_early:
        early_state = "BUILDING_UPSIDE"
    elif negative_early > positive_early:
        early_state = "BUILDING_DOWNSIDE"
    else:
        early_state = "MIXED_CHANGE"

    # PRE-LOCK / SESSION-SEQUENCE is a shadow evidence layer. Because the
    # retained TSETMC source is daily history, it measures session-to-session
    # ordering, not intraday tick ordering.
    sequence_rows = rows[-7:]
    sequence_events = []
    session_observations = []
    if len(sequence_rows) >= 4:
        prior_volumes = []
        prior_values = []
        prev_return = None
        prev_rsi = None
        prev_macd = None
        for row in sequence_rows:
            close_i = _num(row.get("pClosing"))
            volume_i = _num(row.get("qTotTran5J"))
            value_i = _num(row.get("qTotCap"))
            date_i = _record_date(row)
            ret_i = None
            if len(session_observations) > 0:
                prev_close = _num(sequence_rows[len(session_observations) - 1].get("pClosing"))
                if close_i is not None and prev_close not in (None, 0):
                    ret_i = (close_i / prev_close - 1.0) * 100.0
            vol_base = sum(prior_volumes[-5:]) / len(prior_volumes[-5:]) if prior_volumes else None
            val_base = sum(prior_values[-5:]) / len(prior_values[-5:]) if prior_values else None
            vol_ratio_i = volume_i / vol_base if volume_i is not None and vol_base not in (None, 0) else None
            value_ratio_i = value_i / val_base if value_i is not None and val_base not in (None, 0) else None
            prefix_closes = [_num(x.get("pClosing")) for x in rows if date_i is not None and _record_date(x) is not None and _record_date(x) <= date_i]
            prefix_closes = [x for x in prefix_closes if x is not None]
            rsi_i = _rsi(prefix_closes, 14)
            ema12_i = _ema(prefix_closes, 12)
            ema26_i = _ema(prefix_closes, 26)
            macd_i = ema12_i - ema26_i if ema12_i is not None and ema26_i is not None else None
            session_observations.append({"date": date_i, "return_pct": ret_i, "volume_ratio": vol_ratio_i, "value_ratio": value_ratio_i, "rsi": rsi_i, "macd": macd_i})
            if vol_ratio_i is not None and vol_ratio_i >= 1.20:
                sequence_events.append({"date": date_i, "event": "VOLUME_EXPANSION", "strength": round(vol_ratio_i, 3)})
            if value_ratio_i is not None and value_ratio_i >= 1.20:
                sequence_events.append({"date": date_i, "event": "VALUE_EXPANSION", "strength": round(value_ratio_i, 3)})
            if ret_i is not None and abs(ret_i) > 0.50 and (prev_return is None or abs(ret_i) > abs(prev_return)):
                sequence_events.append({"date": date_i, "event": "PRICE_ACCELERATION", "strength": round(ret_i, 3), "direction": "BULLISH" if ret_i > 0 else "BEARISH"})
            momentum_improving = ((macd_i is not None and prev_macd is not None and macd_i > prev_macd)
                                 or (rsi_i is not None and prev_rsi is not None and rsi_i > prev_rsi + 0.5))
            if momentum_improving:
                sequence_events.append({"date": date_i, "event": "MOMENTUM_IMPROVEMENT", "strength": 1.0, "direction": "BULLISH" if ((macd_i is not None and prev_macd is not None and macd_i > prev_macd) or (rsi_i is not None and prev_rsi is not None and rsi_i > prev_rsi + 0.5)) else "BEARISH"})
            if volume_i is not None: prior_volumes.append(volume_i)
            if value_i is not None: prior_values.append(value_i)
            prev_return, prev_rsi, prev_macd = ret_i, rsi_i, macd_i

    event_first = {}
    for event_name in ("VOLUME_EXPANSION", "VALUE_EXPANSION", "PRICE_ACCELERATION", "MOMENTUM_IMPROVEMENT"):
        dates = [x["date"] for x in sequence_events if x.get("event") == event_name and x.get("date")]
        if dates:
            event_first[event_name] = min(dates)
    canonical_chain = ["VOLUME_EXPANSION", "PRICE_ACCELERATION", "MOMENTUM_IMPROVEMENT"]
    chain_dates = [event_first[x] for x in canonical_chain if x in event_first]
    sequence_matches = len(chain_dates) >= 2 and chain_dates == sorted(chain_dates)
    if sequence_matches and all(x in event_first for x in canonical_chain):
        prelock_state, prelock_confidence = "EARLY", "HIGH"
    elif sequence_matches:
        prelock_state, prelock_confidence = "DEVELOPING", "LOW"
    elif "PRICE_ACCELERATION" in event_first and "MOMENTUM_IMPROVEMENT" in event_first:
        prelock_state, prelock_confidence = "DEVELOPING", "LOW"
    elif "VOLUME_EXPANSION" in event_first or "VALUE_EXPANSION" in event_first:
        prelock_state, prelock_confidence = "WATCH", "LOW"
    else:
        prelock_state, prelock_confidence = "NO_SEQUENCE_EVIDENCE", "LOW"
    if all(x in event_first for x in canonical_chain):
        sequence_label = "VOLUME → PRICE → MOMENTUM"
    elif "PRICE_ACCELERATION" in event_first and "MOMENTUM_IMPROVEMENT" in event_first:
        sequence_label = "PRICE → MOMENTUM"
    elif "VOLUME_EXPANSION" in event_first or "VALUE_EXPANSION" in event_first:
        sequence_label = "VOLUME/VALUE_ONLY"
    else:
        sequence_label = "NO_CONFIRMED_SEQUENCE"
    latest_sequence_return = next((x.get("return_pct") for x in reversed(session_observations) if x.get("return_pct") is not None), None)
    signed_price_events = [
        x.get("direction") for x in sequence_events
        if x.get("event") == "PRICE_ACCELERATION" and x.get("direction") in {"BULLISH", "BEARISH"}
    ]
    signed_momentum_events = [
        x.get("direction") for x in sequence_events
        if x.get("event") == "MOMENTUM_IMPROVEMENT" and x.get("direction") in {"BULLISH", "BEARISH"}
    ]
    signed_sequence = signed_price_events + signed_momentum_events
    if signed_sequence and all(x == "BULLISH" for x in signed_sequence):
        sequence_direction = "BULLISH"
    elif signed_sequence and all(x == "BEARISH" for x in signed_sequence):
        sequence_direction = "BEARISH"
    elif signed_sequence:
        sequence_direction = "MIXED"
    else:
        sequence_direction = "UNAVAILABLE"
    recent_high = max((_num(row.get("priceMax")) for row in rows[-20:] if _num(row.get("priceMax")) is not None), default=None)
    recent_low = min((_num(row.get("priceMin")) for row in rows[-20:] if _num(row.get("priceMin")) is not None), default=None)
    range_position = (
        (last_close - recent_low) / (recent_high - recent_low)
        if last_close is not None and recent_high is not None and recent_low is not None and recent_high > recent_low
        else None
    )

    # Correction / counter-trend state: descriptive only. A stock can remain in a
    # primary uptrend while undergoing a meaningful pullback; do not collapse this
    # state into BULLISH. Thresholds are deliberately conservative and use retained
    # TSETMC daily history only.
    prior_peak = max(closes[-11:-1], default=None) if len(closes) >= 3 else None
    correction_from_peak_pct = (
        (last_close / prior_peak - 1.0) * 100.0
        if last_close is not None and prior_peak not in (None, 0) else None
    )
    correction_return_3 = price_change_3
    correction_state = "NO_CORRECTION_EVIDENCE"
    correction_confidence = "LOW"
    if correction_from_peak_pct is not None and correction_return_3 is not None:
        if correction_from_peak_pct <= -1.0 and correction_return_3 <= -0.5:
            correction_state = "CORRECTION_IN_UPTREND" if (sma20 is not None and sma50 is not None and sma20 > sma50) else "CORRECTION"
            correction_confidence = "HIGH" if correction_from_peak_pct <= -3.0 and correction_return_3 <= -1.5 else "MEDIUM"
        elif correction_from_peak_pct >= 1.0 and correction_return_3 >= 0.5:
            correction_state = "COUNTERTREND_BOUNCE_IN_DOWNTREND" if (sma20 is not None and sma50 is not None and sma20 < sma50) else "RECOVERY_BOUNCE"
            correction_confidence = "HIGH" if correction_from_peak_pct >= 3.0 and correction_return_3 >= 1.5 else "MEDIUM"
    correction_active = correction_state in {"CORRECTION_IN_UPTREND", "CORRECTION"}

    if sma50 is not None and sma20 is not None and last_close is not None:
        if last_close > sma20 and sma20 > sma50:
            trend_state = "UP_TREND_STRUCTURE"
        elif last_close < sma20 and sma20 < sma50:
            trend_state = "DOWN_TREND_STRUCTURE"
        else:
            trend_state = "MIXED_STRUCTURE"
    elif sma20 is not None and last_close is not None:
        trend_state = "SHORT_HISTORY_ABOVE_SMA20" if last_close > sma20 else "SHORT_HISTORY_AT_OR_BELOW_SMA20"
    else:
        trend_state = "INSUFFICIENT_HISTORY"

    info = (info_response or {}).get("data") or {}
    threshold = info.get("staticThreshold") or {}
    upper_limit = _num(threshold.get("psGelStaMax"))
    lower_limit = _num(threshold.get("psGelStaMin"))
    latest_last = _num(latest.get("pDrCotVal"))
    limit_date_matches = latest_date == today
    headroom = (
        (upper_limit - latest_last) / latest_last * 100.0
        if limit_date_matches and upper_limit is not None and latest_last not in (None, 0)
        else None
    )
    prelock_distance = headroom

    touched_upper = (
        _num(latest.get("priceMax")) >= upper_limit
        if limit_date_matches and upper_limit is not None and _num(latest.get("priceMax")) is not None
        else None
    )

    raw_sha = history_response.get("snapshot_sha256")
    if not raw_sha:
        raw_sha = hashlib.sha256(
            json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    return {
        "status": "PASS" if len(closes) >= 20 else "PARTIAL",
        "engine_version": ENGINE_VERSION,
        "source": "TSETMC",
        "instrument_id": str(instrument_id),
        "source_endpoint": history_response.get("endpoint"),
        "source_retrieved_at": history_response.get("retrieved_at"),
        "history_snapshot_sha256": raw_sha,
        "history_count": len(closes),
        "latest_market_date": latest_date,
        "latest_source_market_time": latest.get("hEven"),
        "last_close": last_close,
        "last_price": latest_last,
        "sma_5": sma5,
        "sma_10": sma10,
        "sma_20": sma20,
        "sma_50": sma50,
        "return_5_sessions_pct": return_5,
        "return_20_sessions_pct": return_20,
        "rsi_14": rsi14,
        "macd_12_26": macd,
        "volume_ratio_5_to_20": volume_ratio,
        "volume_ratio_5_to_50": volume_ratio_5_to_50,
        "value_ratio_5_to_20": value_ratio,
        "early_move": {
            "status": "PASS" if early_components else "UNAVAILABLE",
            "score": early_score,
            "state": early_state,
            "price_change_1_session_pct": price_change_1,
            "price_change_3_sessions_pct": price_change_3,
            "sma20_slope_5_sessions_pct": sma20_slope_5_pct,
            "rsi_change_1_session": rsi_change_1,
            "macd_change_1_session": macd_change,
            "volume_ratio_change_1_session": volume_ratio_change,
            "breakout_above_prior_20_high": breakout_20,
            "positive_components": positive_early,
            "negative_components": negative_early,
            "available_components": len(early_components),
            "sequence_rule": "CHANGE_ONLY_SHADOW_EVIDENCE",
            "production_gate": "OFF",
            "pre_lock_sequence": {
                "status": "PASS" if session_observations else "UNAVAILABLE",
                "state": prelock_state,
                "confidence": prelock_confidence,
                "sequence": sequence_label,
                "event_first_dates": event_first,
                "events": sequence_events,
                "sessions_evaluated": len(session_observations),
                "latest_session_return_pct": latest_sequence_return,
                "sequence_direction": sequence_direction,
                "distance_to_upper_limit_pct": prelock_distance,
                "data_granularity": "DAILY_SESSION_SEQUENCE_NOT_INTRADAY",
                "production_gate": "OFF",
            },
        },
        "range_position_20": range_position,
        "trend_state": trend_state,
        "correction_state": correction_state,
        "correction_confidence": correction_confidence,
        "correction_active": correction_active,
        "correction_from_prior_peak_pct": correction_from_peak_pct,
        "correction_return_3_sessions_pct": correction_return_3,
        "upper_limit_price": upper_limit,
        "lower_limit_price": lower_limit,
        "upper_limit_headroom_pct": headroom,
        "touched_upper_limit_today": touched_upper,
        "limit_threshold_date_match": limit_date_matches,
        "limit_source_endpoint": (info_response or {}).get("endpoint"),
        "limit_source_retrieved_at": (info_response or {}).get("retrieved_at"),
        "limit_source_snapshot_sha256": (info_response or {}).get("snapshot_sha256"),
        "interpretation": "DESCRIPTIVE_TECHNICAL_FEATURES_ONLY_NOT_A_BUY_SELL_OR_LIMIT_UP_PREDICTION",
    }


def _board_metrics(orderbook_response: dict[str, Any] | None, client_type_response: dict[str, Any] | None) -> dict[str, Any]:
    orderbook_response = orderbook_response or {}
    client_type_response = client_type_response or {}
    levels = orderbook_response.get("data")
    levels = [x for x in levels if isinstance(x, dict)] if isinstance(levels, list) else []
    levels.sort(key=lambda x: int(x.get("number") or 999))

    bid_volume = sum(_num(x.get("qTitMeDem")) or 0.0 for x in levels)
    ask_volume = sum(_num(x.get("qTitMeOf")) or 0.0 for x in levels)
    bid_orders = sum(_num(x.get("zOrdMeDem")) or 0.0 for x in levels)
    ask_orders = sum(_num(x.get("zOrdMeOf")) or 0.0 for x in levels)
    best_bid = _num(levels[0].get("pMeDem")) if levels else None
    best_ask = _num(levels[0].get("pMeOf")) if levels else None
    spread = best_ask - best_bid if best_ask is not None and best_bid is not None else None
    mid = (best_ask + best_bid) / 2.0 if best_ask is not None and best_bid is not None else None
    client = client_type_response.get("data") or {}
    if not isinstance(client, dict):
        client = {}

    def ratio(a, b):
        return a / b if a is not None and b not in (None, 0) else None

    buy_i = _num(client.get("buy_I_Volume"))
    sell_i = _num(client.get("sell_I_Volume"))
    buy_n = _num(client.get("buy_N_Volume"))
    sell_n = _num(client.get("sell_N_Volume"))
    count_buy_i = _num(client.get("buy_CountI"))
    count_sell_i = _num(client.get("sell_CountI"))
    count_buy_n = _num(client.get("buy_CountN"))
    count_sell_n = _num(client.get("sell_CountN"))
    buy_i_power = ratio(buy_i, count_buy_i)
    sell_i_power = ratio(sell_i, count_sell_i)
    buy_n_power = ratio(buy_n, count_buy_n)
    sell_n_power = ratio(sell_n, count_sell_n)

    client_values = [buy_i, sell_i, buy_n, sell_n, count_buy_i, count_sell_i, count_buy_n, count_sell_n]
    client_status = "UNAVAILABLE" if not client else (
        "NO_RECORDED_ACTIVITY" if all(x in (None, 0) for x in client_values) else "SUCCESS"
    )
    return {
        "orderbook_status": "SUCCESS" if levels else "UNAVAILABLE",
        "orderbook_level_count": len(levels),
        "bid_depth_volume_5": bid_volume if levels else None,
        "ask_depth_volume_5": ask_volume if levels else None,
        "bid_order_count_5": bid_orders if levels else None,
        "ask_order_count_5": ask_orders if levels else None,
        "bid_ask_volume_ratio_5": ratio(bid_volume, ask_volume) if levels else None,
        "orderbook_imbalance_5": (
            (bid_volume - ask_volume) / (bid_volume + ask_volume)
            if levels and bid_volume + ask_volume > 0 else None
        ),
        "best_bid_price": best_bid,
        "best_ask_price": best_ask,
        "best_bid_ask_spread": spread,
        "best_bid_ask_spread_pct": spread / mid * 100.0 if spread is not None and mid not in (None, 0) else None,
        "orderbook_endpoint": orderbook_response.get("endpoint"),
        "orderbook_retrieved_at": orderbook_response.get("retrieved_at"),
        "orderbook_snapshot_sha256": orderbook_response.get("snapshot_sha256"),
        "client_type_status": client_status,
        "individual_buy_volume": buy_i,
        "individual_sell_volume": sell_i,
        "individual_buy_count": count_buy_i,
        "individual_sell_count": count_sell_i,
        "individual_buy_power": buy_i_power,
        "individual_sell_power": sell_i_power,
        "individual_power_ratio": ratio(buy_i_power, sell_i_power),
        "legal_buy_volume": buy_n,
        "legal_sell_volume": sell_n,
        "legal_buy_count": count_buy_n,
        "legal_sell_count": count_sell_n,
        "legal_buy_power": buy_n_power,
        "legal_sell_power": sell_n_power,
        "legal_power_ratio": ratio(buy_n_power, sell_n_power),
        "client_type_endpoint": client_type_response.get("endpoint"),
        "client_type_retrieved_at": client_type_response.get("retrieved_at"),
        "client_type_snapshot_sha256": client_type_response.get("snapshot_sha256"),
        "board_interpretation": "DESCRIPTIVE_ORDERBOOK_AND_CLIENT_TYPE_EVIDENCE_ONLY",
    }


def fetch_underlying_context(instrument_ids: list[str], adapter: TSETMCAdapter | None = None, *, include_board: bool = True) -> dict[str, Any]:
    adapter = adapter or TSETMCAdapter()
    results = {}
    for instrument_id in sorted({str(x).strip() for x in instrument_ids if str(x).strip()}):
        try:
            history = adapter.daily_history(instrument_id, top=100)
            if include_board:
                info = adapter.instrument_info(instrument_id)
                orderbook = adapter.order_book(instrument_id)
                client_type = adapter.client_type(instrument_id)
            else:
                # Closed-mode underlying intelligence may use retained TSETMC
                # daily history, but must not refresh current board/client flow.
                info = {"source": "TSETMC", "data": {}, "retrieved_at": None}
                orderbook = {"source": "TSETMC", "data": [], "retrieved_at": None}
                client_type = {"source": "TSETMC", "data": {}, "retrieved_at": None}
            analysis = analyze_history(instrument_id, history, info)
            board = _board_metrics(orderbook, client_type) if include_board else {
                "orderbook_status": "CLOSED_SNAPSHOT_NO_REFRESH",
                "client_type_status": "CLOSED_SNAPSHOT_NO_REFRESH",
                "board_interpretation": "CURRENT_BOARD_NOT_REFRESHED_IN_CLOSED_MODE",
            }
            analysis.update(board)

            raw_rows = history.get("data") if isinstance(history.get("data"), list) else []
            exact_rows = [
                row for row in raw_rows
                if isinstance(row, dict) and str(row.get("insCode") or "").strip() == instrument_id
            ]
            archive_payload = {
                "archive_version": "TSETMC-UNDERLYING-SNAPSHOT-1.0",
                "source_of_truth": "TSETMC",
                "instrument_id": instrument_id,
                "daily_history": {
                    "retrieved_at": history.get("retrieved_at"),
                    "endpoint": history.get("endpoint"),
                    "source_response_sha256": history.get("snapshot_sha256"),
                    "rows": exact_rows,
                },
                "instrument_info": info.get("data"),
                "instrument_info_endpoint": info.get("endpoint"),
                "instrument_info_retrieved_at": info.get("retrieved_at"),
                "instrument_info_snapshot_sha256": info.get("snapshot_sha256"),
                "orderbook": orderbook.get("data"),
                "orderbook_endpoint": orderbook.get("endpoint"),
                "orderbook_retrieved_at": orderbook.get("retrieved_at"),
                "orderbook_snapshot_sha256": orderbook.get("snapshot_sha256"),
                "client_type": client_type.get("data"),
                "client_type_endpoint": client_type.get("endpoint"),
                "client_type_retrieved_at": client_type.get("retrieved_at"),
                "client_type_snapshot_sha256": client_type.get("snapshot_sha256"),
            }
            archive_canonical = json.dumps(
                archive_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            archive_sha = hashlib.sha256(archive_canonical.encode("utf-8")).hexdigest()
            archive_payload["archive_sha256"] = archive_sha
            archive_dir = Path(__file__).resolve().parent / "output" / "history" / "underlying"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / f"{instrument_id}_{archive_sha}.json"
            archive_path.write_text(
                json.dumps(archive_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            analysis["archive_path"] = str(archive_path)
            analysis["archive_sha256"] = archive_sha
            results[instrument_id] = analysis
        except Exception as exc:
            results[instrument_id] = {
                "status": "UNAVAILABLE",
                "engine_version": ENGINE_VERSION,
                "source": "TSETMC",
                "instrument_id": instrument_id,
                "error_type": type(exc).__name__,
                "interpretation": "NO_TECHNICAL_OR_BOARD_CLAIM",
            }
    return {
        "status": "PASS" if results and all(x.get("status") in {"PASS", "PARTIAL"} for x in results.values()) else "PARTIAL",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": "TSETMC",
        "instrument_count": len(results),
        "instruments": results,
        "rules": {
            "history_match": "EXACT_INSTRUMENT_ID",
            "history_order": "SORTED_BY_TSETMC_D_EVEN",
            "technical_features": ["SMA_5", "SMA_10", "SMA_20", "SMA_50", "RSI_14_WILDER", "MACD_12_26", "RETURN_5_20", "VOLUME_VALUE_RATIO_5_20", "EARLY_MOVE_CHANGE_SEQUENCE"],
            "board_features": ["BEST_LIMITS_5_LEVELS", "CLIENT_TYPE_INDIVIDUAL_LEGAL"],
            "limit_headroom": "ONLY_WHEN_DAILY_HISTORY_DATE_MATCHES_CURRENT_TEHRAN_DATE",
            "retrieval_time_is_not_market_time": True,
            "missing_data": "UNAVAILABLE_NOT_ZERO",
            "signal_generation": "FORBIDDEN",
        },
    }
