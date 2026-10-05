#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-first last-minute option opportunity engine.

Purpose:
    Find options that have the strongest *current* short-term opportunity
    based on live TSETMC evidence from the underlying and the option itself.

Important:
    This is NOT an expiry-day model. Remaining days to expiry is a risk/context
    feature only. There is no fixed +3% underlying scenario and no requirement
    for one day to expiry.

The engine ranks opportunity from:
    1) underlying momentum/trend,
    2) current board/order-flow evidence,
    3) volume/value confirmation,
    4) distance from the daily upper limit,
    5) option liquidity/quote quality,
    6) option sensitivity/leverage only after liquidity quality is proven,
    7) option moneyness and time-to-expiry as secondary context.

Missing evidence is never converted to zero or an invented positive signal.
Non-tradable/stale-looking option quotes are excluded from the opportunity
ranking instead of creating artificial leverage.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")
ENGINE_VERSION = "TSETMC-LAST-MINUTE-OPTION-OPPORTUNITY-2.1"

# Ranking weights. These describe opportunity evidence; they are not a
# buy/sell signal and do not predict a limit-up outcome.
WEIGHTS = {
    "underlying_momentum": 25.0,
    "board_strength": 20.0,
    "volume_value": 15.0,
    "upper_headroom": 10.0,
    "option_liquidity": 15.0,
    "option_sensitivity": 10.0,
    "moneyness_time": 5.0,
}


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _days_to_expiry(row: dict[str, Any], now=None) -> float | None:
    canonical = row.get("canonical") or {}
    days = _num(canonical.get("روزهای تقویمی"))
    if days is not None:
        return max(0.0, days)

    raw = canonical.get("تاریخ سررسید")
    if not raw:
        return None
    try:
        expiry = datetime.strptime(str(raw)[:8], "%Y%m%d").date()
        current = (now or datetime.now(TEHRAN)).date()
        return float(max(0, (expiry - current).days))
    except (TypeError, ValueError):
        return None


def _is_itm(typ: str, spot: float, strike: float) -> bool:
    if typ == "CALL":
        return spot > strike
    if typ == "PUT":
        return spot < strike
    return False


def _ratio(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return a / b


def _pick(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _option_fields(row: dict[str, Any]) -> dict[str, float | None]:
    c = row.get("canonical") or {}
    return {
        "last": _num(c.get("آخرین قیمت")),
        "close": _num(c.get("قیمت پایانی")),
        "volume": _num(c.get("حجم معاملات")),
        "trade_count": _num(c.get("تعداد معاملات")),
        "trade_value": _num(c.get("ارزش معاملات")),
        "bid_price": _num(c.get("قیمت بهترین تقاضا")),
        "bid_volume": _num(c.get("حجم بهترین تقاضا")),
        "ask_price": _num(c.get("قیمت بهترین عرضه")),
        "ask_volume": _num(c.get("حجم بهترین عرضه")),
        "open_interest": _num(c.get("موقعیت های باز")),
        "low": _num(c.get("کمترین قیمت")),
        "high": _num(c.get("بیشترین قیمت")),
    }


def _underlying_momentum_score(ctx: dict[str, Any]) -> tuple[float, list[str]]:
    evidence = []
    points = []

    r5 = _num(ctx.get("return_5_sessions_pct"))
    r20 = _num(ctx.get("return_20_sessions_pct"))
    rsi = _num(ctx.get("rsi_14"))
    macd = _num(ctx.get("macd_12_26"))
    last = _num(ctx.get("last_price"))
    sma5 = _num(ctx.get("sma_5"))
    sma10 = _num(ctx.get("sma_10"))
    sma20 = _num(ctx.get("sma_20"))
    sma50 = _num(ctx.get("sma_50"))

    if r5 is not None:
        points.append(_clamp(50.0 + r5 * 8.0))
        evidence.append(f"بازده ۵ جلسه: {r5:.2f}%")
    if r20 is not None:
        points.append(_clamp(50.0 + r20 * 3.0))
        evidence.append(f"بازده ۲۰ جلسه: {r20:.2f}%")
    if last is not None and sma5 is not None:
        points.append(70.0 if last > sma5 else 30.0)
    if last is not None and sma10 is not None:
        points.append(70.0 if last > sma10 else 30.0)
    if last is not None and sma20 is not None:
        points.append(75.0 if last > sma20 else 25.0)
    if last is not None and sma50 is not None:
        points.append(80.0 if last > sma50 else 20.0)
    if sma20 is not None and sma50 is not None:
        points.append(80.0 if sma20 > sma50 else 20.0)
    if rsi is not None:
        # Avoid rewarding extreme overbought values as continuation evidence.
        if 55.0 <= rsi <= 72.0:
            points.append(80.0)
        elif rsi > 80.0:
            points.append(35.0)
        elif rsi >= 50.0:
            points.append(65.0)
        else:
            points.append(25.0)
        evidence.append(f"RSI14: {rsi:.1f}")
    if macd is not None:
        points.append(75.0 if macd > 0 else 25.0)

    return (sum(points) / len(points) if points else 0.0, evidence)


def _board_strength_score(ctx: dict[str, Any]) -> tuple[float, list[str]]:
    imbalance = _num(ctx.get("orderbook_imbalance_5"))
    bid_ask = _num(ctx.get("bid_ask_volume_ratio_5"))
    individual_power = _num(ctx.get("individual_power_ratio"))
    legal_power = _num(ctx.get("legal_power_ratio"))
    score_parts = []
    evidence = []

    if imbalance is not None:
        score_parts.append(_clamp(50.0 + imbalance * 50.0))
        evidence.append(f"عدم‌تعادل سفارش‌ها: {imbalance:.2f}")
    if bid_ask is not None:
        score_parts.append(_clamp(50.0 + (bid_ask - 1.0) * 35.0))
    if individual_power is not None:
        score_parts.append(_clamp(50.0 + (individual_power - 1.0) * 30.0))
        evidence.append(f"قدرت حقیقی خرید/فروش: {individual_power:.2f}x")
    if legal_power is not None:
        score_parts.append(_clamp(50.0 + (legal_power - 1.0) * 20.0))

    touched = ctx.get("touched_upper_limit_today")
    headroom = _num(ctx.get("upper_limit_headroom_pct"))
    if touched is True:
        score_parts.append(90.0)
        evidence.append("سقف روزانه لمس شده است")
    elif headroom is not None and 0.0 <= headroom <= 2.0:
        score_parts.append(85.0)
        evidence.append(f"فاصله تا سقف روزانه: {headroom:.2f}%")
    elif headroom is not None and headroom <= 5.0:
        score_parts.append(70.0)
        evidence.append(f"فاصله تا سقف روزانه: {headroom:.2f}%")

    return (sum(score_parts) / len(score_parts) if score_parts else 0.0, evidence)


def _volume_value_score(ctx: dict[str, Any]) -> tuple[float, list[str]]:
    ratios = [
        _num(ctx.get("volume_ratio_5_to_20")),
        _num(ctx.get("volume_ratio_5_to_50")),
        _num(ctx.get("value_ratio_5_to_20")),
    ]
    valid = [x for x in ratios if x is not None]
    if not valid:
        return 0.0, []

    parts = [_clamp(50.0 + (x - 1.0) * 45.0) for x in valid]
    evidence = [
        f"حجم ۵/۲۰: {ratios[0]:.2f}x" if ratios[0] is not None else "",
        f"حجم ۵/۵۰: {ratios[1]:.2f}x" if ratios[1] is not None else "",
        f"ارزش ۵/۲۰: {ratios[2]:.2f}x" if ratios[2] is not None else "",
    ]
    return sum(parts) / len(parts), [x for x in evidence if x]


def _upper_headroom_score(ctx: dict[str, Any]) -> float:
    headroom = _num(ctx.get("upper_limit_headroom_pct"))
    touched = ctx.get("touched_upper_limit_today")
    if touched is True:
        return 95.0
    if headroom is None:
        return 0.0
    if headroom < 0:
        return 0.0
    if headroom <= 1:
        return 95.0
    if headroom <= 2:
        return 90.0
    if headroom <= 5:
        return 75.0
    if headroom <= 10:
        return 55.0
    if headroom <= 20:
        return 35.0
    return 20.0


def _option_liquidity_score(row: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    f = _option_fields(row)
    last, close = f["last"], f["close"]
    volume, trades, value = f["volume"], f["trade_count"], f["trade_value"]
    bid, ask = f["bid_price"], f["ask_price"]
    bid_v, ask_v = f["bid_volume"], f["ask_volume"]

    evidence = {}
    if last is None or last <= 0:
        return 0.0, {"status": "REJECT", "reason": "NON_POSITIVE_LAST_PRICE", "score": 0.0}

    if volume in (None, 0) and trades in (None, 0) and value in (None, 0):
        return 0.0, {"status": "REJECT", "reason": "NO_OPTION_ACTIVITY_EVIDENCE", "score": 0.0}

    score = 40.0
    if volume is not None and volume > 0:
        score += 20.0
        evidence["volume"] = volume
    if trades is not None and trades > 0:
        score += 10.0
        evidence["trades"] = trades
    if value is not None and value > 0:
        score += 10.0
        evidence["trade_value"] = value
    if close is not None and close > 0:
        last_close_gap = abs(last / close - 1.0) * 100.0
        evidence["last_close_gap_pct"] = last_close_gap
        if last_close_gap <= 2:
            score += 5.0
        elif last_close_gap <= 5:
            score += 2.0

    if bid is not None and ask is not None and bid > 0 and ask > 0 and ask >= bid:
        spread_pct = (ask - bid) / ((ask + bid) / 2.0) * 100.0
        evidence["spread_pct"] = spread_pct
        if spread_pct <= 2:
            score += 15.0
        elif spread_pct <= 5:
            score += 8.0
        elif spread_pct <= 10:
            score += 3.0
    else:
        evidence["spread_pct"] = None

    evidence["bid_volume"] = bid_v
    evidence["ask_volume"] = ask_v
    evidence["score"] = _clamp(score)
    evidence["status"] = "PASS"
    return evidence["score"], evidence


def _option_sensitivity_score(
    row: dict[str, Any],
    underlying_context: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    c = row.get("canonical") or {}
    spot = _num(c.get("قیمت سهم پایه"))
    strike = _num(c.get("قیمت اعمال"))
    option_price = _num(c.get("آخرین قیمت"))
    days = _days_to_expiry(row)

    if None in (spot, strike, option_price) or option_price <= 0:
        return 0.0, {"status": "UNAVAILABLE", "score": 0.0}

    moneyness = abs(spot / strike - 1.0) * 100.0 if strike else None
    delta = _num(c.get("دلتا"))
    leverage = spot / option_price

    # High leverage is useful only after the liquidity gate. It is deliberately
    # capped so a 1-rial stale quote cannot dominate the ranking.
    leverage_component = _clamp(35.0 + min(leverage, 15.0) * 4.0)

    if delta is not None:
        delta_component = _clamp(50.0 + abs(delta) * 50.0)
    else:
        delta_component = 50.0

    if moneyness is None:
        moneyness_component = 0.0
    elif moneyness <= 5:
        moneyness_component = 90.0
    elif moneyness <= 10:
        moneyness_component = 80.0
    elif moneyness <= 20:
        moneyness_component = 65.0
    elif moneyness <= 30:
        moneyness_component = 45.0
    else:
        moneyness_component = 25.0

    # Time is context only. We do not prefer one-day contracts.
    if days is None:
        time_component = 0.0
    elif days < 5:
        time_component = 35.0
    elif days <= 30:
        time_component = 80.0
    elif days <= 90:
        time_component = 65.0
    else:
        time_component = 45.0

    return (
        (leverage_component + delta_component) / 2.0,
        {
            "status": "PASS",
            "leverage_capped_for_score": min(leverage, 15.0),
            "raw_leverage": leverage,
            "delta": delta,
            "moneyness_pct": moneyness,
            "days_to_expiry": days,
            "time_context_score": time_component,
            "score": (leverage_component + delta_component) / 2.0,
        },
    )


def _moneyness_time_score(row: dict[str, Any]) -> float:
    c = row.get("canonical") or {}
    spot = _num(c.get("قیمت سهم پایه"))
    strike = _num(c.get("قیمت اعمال"))
    days = _days_to_expiry(row)
    if None in (spot, strike):
        return 0.0

    distance = abs(spot / strike - 1.0) * 100.0
    m = 90.0 if distance <= 5 else 80.0 if distance <= 10 else 65.0 if distance <= 20 else 45.0
    t = 0.0 if days is None else (35.0 if days < 5 else 80.0 if days <= 30 else 65.0 if days <= 90 else 45.0)
    return (m + t) / 2.0


def analyze_underlying_context(context: dict[str, Any] | None) -> dict[str, Any]:
    context = context or {}
    if not isinstance(context, dict) or context.get("status") == "UNAVAILABLE":
        return {
            "status": "UNAVAILABLE",
            "momentum_score": 0.0,
            "board_score": 0.0,
            "volume_score": 0.0,
            "queue_state": "داده موجود نیست",
            "trend_state": "داده موجود نیست",
            "volume_state": "داده موجود نیست",
            "evidence": [],
        }

    momentum, momentum_evidence = _underlying_momentum_score(context)
    board, board_evidence = _board_strength_score(context)
    volume, volume_evidence = _volume_value_score(context)
    headroom = _upper_headroom_score(context)

    imbalance = _num(context.get("orderbook_imbalance_5"))
    if context.get("touched_upper_limit_today") is True:
        queue_state = "سقف روزانه لمس شده؛ قدرت تقاضا باید با حجم/سفارش تأیید شود"
    elif imbalance is not None and imbalance >= 0.60:
        queue_state = "برتری تقاضا در سفارش‌های ثبت‌شده"
    elif imbalance is not None:
        queue_state = "برتری تقاضای قوی تأیید نشده"
    else:
        queue_state = "داده سفارش‌ها کافی نیست"

    trend_state = context.get("trend_state") or "داده موجود نیست"
    volume_state = " | ".join(volume_evidence) if volume_evidence else "داده حجم/ارزش کافی نیست"

    return {
        "status": context.get("status", "PARTIAL"),
        "momentum_score": momentum,
        "board_score": board,
        "volume_score": volume,
        "upper_headroom_score": headroom,
        "queue_state": queue_state,
        "trend_state": trend_state,
        "volume_state": volume_state,
        "evidence": momentum_evidence + board_evidence + volume_evidence,
        "orderbook_imbalance_5": imbalance,
        "individual_power_ratio": _num(context.get("individual_power_ratio")),
        "upper_limit_headroom_pct": _num(context.get("upper_limit_headroom_pct")),
    }


def _candidate(row: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
    canonical = row.get("canonical") or {}
    identity = row.get("identity") or {}
    typ = str(identity.get("contract_type") or "").upper()
    spot = _num(canonical.get("قیمت سهم پایه"))
    strike = _num(canonical.get("قیمت اعمال"))
    option_price = _num(canonical.get("آخرین قیمت"))
    days = _days_to_expiry(row)

    if typ not in {"CALL", "PUT"} or None in (spot, strike, option_price, days):
        return None
    if spot <= 0 or strike <= 0 or option_price <= 0:
        return None

    # A current opportunity can be either ITM or near-the-money. Deep OTM
    # contracts are excluded because their apparent leverage is unstable.
    moneyness_pct = abs(spot / strike - 1.0) * 100.0
    if moneyness_pct > 30.0:
        return None

    liquidity_score, liquidity = _option_liquidity_score(row)
    if liquidity.get("status") != "PASS":
        return None

    underlying = analyze_underlying_context(context)
    sensitivity_score, sensitivity = _option_sensitivity_score(row, context)
    moneyness_time = _moneyness_time_score(row)

    if underlying["status"] == "UNAVAILABLE":
        return None

    # Directional alignment: CALL benefits from a positive underlying score;
    # PUT benefits from a negative underlying structure. This is descriptive
    # opportunity matching, not a trade instruction.
    momentum_score = underlying["momentum_score"]
    if typ == "PUT":
        directional_momentum = 100.0 - momentum_score
        directional_board = 100.0 - underlying["board_score"]
        directional_volume = 100.0 - underlying["volume_score"]
        direction_label = "نزولی"
    else:
        directional_momentum = momentum_score
        directional_board = underlying["board_score"]
        directional_volume = underlying["volume_score"]
        direction_label = "صعودی"

    total = (
        directional_momentum * WEIGHTS["underlying_momentum"]
        + directional_board * WEIGHTS["board_strength"]
        + directional_volume * WEIGHTS["volume_value"]
        + underlying["upper_headroom_score"] * WEIGHTS["upper_headroom"]
        + liquidity_score * WEIGHTS["option_liquidity"]
        + sensitivity_score * WEIGHTS["option_sensitivity"]
        + moneyness_time * WEIGHTS["moneyness_time"]
    ) / 100.0

    return {
        "instrument_id": identity.get("instrument_id"),
        "symbol": canonical.get("نماد"),
        "underlying_symbol": identity.get("underlying_symbol"),
        "underlying_id": identity.get("underlying_id"),
        "contract_type": typ,
        "direction": direction_label,
        "days_to_expiry": days,
        "underlying_price": spot,
        "strike": strike,
        "current_option_price": option_price,
        "option_close": _num(canonical.get("قیمت پایانی")),
        "moneyness_pct": moneyness_pct,
        "raw_leverage": spot / option_price,
        "score": round(total, 2),
        "score_components": {
            "underlying_momentum": round(directional_momentum, 2),
            "board_strength": round(directional_board, 2),
            "volume_value": round(directional_volume, 2),
            "upper_headroom": round(underlying["upper_headroom_score"], 2),
            "option_liquidity": round(liquidity_score, 2),
            "option_sensitivity": round(sensitivity_score, 2),
            "moneyness_time": round(moneyness_time, 2),
        },
        "option_liquidity": liquidity,
        "option_sensitivity": sensitivity,
        "underlying_analysis": underlying,
        "method": "CURRENT_EVIDENCE_OPTION_OPPORTUNITY_RANKING",
        "expiry_not_primary": True,
    }


def build_last_minute_ranking(
    rows: list[dict[str, Any]],
    *,
    top_count: int = 15,
    now=None,
    underlying_context: dict[str, Any] | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = snapshot or {}
    underlying_context = underlying_context or {}

    excluded = {
        "invalid_contract": 0,
        "too_far_otm": 0,
        "non_tradable_option": 0,
        "missing_underlying_evidence": 0,
        "directionally_weak": 0,
    }

    candidates = []
    for row in list(rows or []):
        identity = row.get("identity") or {}
        underlying_id = str(identity.get("underlying_id") or "").strip()
        context = underlying_context.get(underlying_id)
        if not context:
            excluded["missing_underlying_evidence"] += 1
            continue

        item = _candidate(row, context)
        if item is None:
            c = row.get("canonical") or {}
            typ = str(identity.get("contract_type") or "").upper()
            spot = _num(c.get("قیمت سهم پایه"))
            strike = _num(c.get("قیمت اعمال"))
            last = _num(c.get("آخرین قیمت"))
            if typ not in {"CALL", "PUT"} or None in (spot, strike, last):
                excluded["invalid_contract"] += 1
            elif abs(spot / strike - 1.0) > 30.0:
                excluded["too_far_otm"] += 1
            else:
                excluded["non_tradable_option"] += 1
            continue

        # Do not let a weak underlying context create a false "last-minute"
        # opportunity. A candidate must have evidence on at least two of the
        # three core underlying dimensions.
        components = item["score_components"]
        supportive = sum(
            components[key] >= 60.0
            for key in ("underlying_momentum", "board_strength", "volume_value")
        )
        if supportive < 2:
            excluded["directionally_weak"] += 1
            continue
        candidates.append(item)

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["option_liquidity"]["score"],
            -x["moneyness_pct"],
            str(x.get("instrument_id") or ""),
        ),
        reverse=True,
    )

    ranked = candidates[: max(1, int(top_count))]

    for rank, item in enumerate(ranked, 1):
        item["rank"] = rank

    return {
        "status": "PASS" if ranked else "NO_ELIGIBLE_OPPORTUNITY",
        "mode": "LAST_MINUTE_OPTION_OPPORTUNITY",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": "TSETMC",
        "method": "CURRENT_EVIDENCE_OPPORTUNITY_RANKING",
        "candidate_count": len(candidates),
        "display_count": len(ranked),
        "excluded_counts": excluded,
        "weights": WEIGHTS,
        "rules": {
            "expiry_is_not_a_primary_selector": True,
            "fixed_underlying_scenario": False,
            "one_day_expiry_requirement": False,
            "deep_otm_excluded_above_moneyness_pct": 30.0,
            "option_activity_evidence_required": True,
            "positive_underlying_evidence_required": True,
            "stale_one_rial_leverage_is_not_allowed_to_dominate": True,
            "buy_sell_signal": False,
        },
        "ranking_rows": ranked,
        "snapshot_data_mode": snapshot.get("data_mode"),
        "snapshot_live_refresh_status": snapshot.get("live_refresh_status"),
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
    }
