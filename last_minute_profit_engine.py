#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Last-minute option opportunity engine.

This engine is deliberately separate from the economic ranking engine.
It answers one narrow scenario question using only TSETMC row evidence:
which currently ITM options with exactly one calendar day remaining to
expiry would have the highest option return if the underlying rose by 3%
by expiry.

No implied volatility, Greeks, risk-free rate, or invented market value is
used. At one day remaining, the scenario value at expiry is the intrinsic
payoff after the specified underlying move.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")
UNDERLYING_SCENARIO_UP = 0.03
TARGET_DAYS_TO_EXPIRY = 1


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _days_to_expiry(row: dict[str, Any], now=None) -> int | None:
    canonical = row.get("canonical") or {}
    days = _num(canonical.get("روزهای تقویمی"))
    if days is not None and float(days).is_integer():
        return int(days)

    raw = canonical.get("تاریخ سررسید")
    if not raw:
        return None
    try:
        expiry = datetime.strptime(str(raw)[:8], "%Y%m%d").date()
        current = (now or datetime.now(TEHRAN)).date()
        return (expiry - current).days
    except (TypeError, ValueError):
        return None


def _is_itm(typ: str, spot: float, strike: float) -> bool:
    if typ == "CALL":
        return spot > strike
    if typ == "PUT":
        return spot < strike
    return False


def _scenario(row: dict[str, Any], now=None) -> dict[str, Any] | None:
    canonical = row.get("canonical") or {}
    identity = row.get("identity") or {}
    typ = str(identity.get("contract_type") or "").upper()

    spot = _num(canonical.get("قیمت سهم پایه"))
    strike = _num(canonical.get("قیمت اعمال"))
    option_price = _num(canonical.get("آخرین قیمت"))
    days = _days_to_expiry(row, now=now)

    if typ not in {"CALL", "PUT"}:
        return None
    if None in (spot, strike, option_price, days):
        return None
    if spot <= 0 or strike <= 0 or option_price <= 0:
        return None
    if days != TARGET_DAYS_TO_EXPIRY:
        return None
    if not _is_itm(typ, spot, strike):
        return None

    scenario_spot = spot * (1.0 + UNDERLYING_SCENARIO_UP)
    scenario_payoff = (
        max(scenario_spot - strike, 0.0)
        if typ == "CALL"
        else max(strike - scenario_spot, 0.0)
    )
    scenario_return = (scenario_payoff - option_price) / option_price * 100.0
    leverage = spot / option_price

    return {
        "instrument_id": identity.get("instrument_id"),
        "symbol": canonical.get("نماد"),
        "underlying_symbol": identity.get("underlying_symbol"),
        "underlying_id": identity.get("underlying_id"),
        "contract_type": typ,
        "days_to_expiry": days,
        "underlying_price": spot,
        "scenario_underlying_price": scenario_spot,
        "strike": strike,
        "current_option_price": option_price,
        "scenario_option_value_at_expiry": scenario_payoff,
        "scenario_profit_per_unit": scenario_payoff - option_price,
        "scenario_return_pct": scenario_return,
        "leverage": leverage,
        "itm": True,
        "scenario": "UNDERLYING_UP_3_PERCENT_AT_EXPIRY",
    }


def analyze_underlying_context(context: dict[str, Any] | None) -> dict[str, Any]:
    """Summarize TSETMC underlying board, trend and volume evidence."""
    context = context or {}
    if not isinstance(context, dict) or context.get("status") == "UNAVAILABLE":
        return {"status": "UNAVAILABLE", "queue_state": "داده موجود نیست", "trend_state": "داده موجود نیست", "volume_state": "داده موجود نیست", "persistence_evidence": "داده موجود نیست"}

    def num(key):
        return _num(context.get(key))

    last_price = num("last_price")
    sma20 = num("sma_20")
    sma50 = num("sma_50")
    volume_ratio = num("volume_ratio_5_to_20")
    value_ratio = num("value_ratio_5_to_20")
    volume_ratio_5_to_50 = num("volume_ratio_5_to_50")
    bid_depth = num("bid_depth_volume_5")
    ask_depth = num("ask_depth_volume_5")
    imbalance = num("orderbook_imbalance_5")
    upper_headroom = num("upper_limit_headroom_pct")

    if upper_headroom is not None and upper_headroom <= 0.05 and bid_depth is not None and bid_depth > 0 and ask_depth in (None, 0):
        queue_state = "صف خرید قابل‌تأیید در داده سفارش‌ها"
    elif imbalance is not None and imbalance >= 0.60:
        queue_state = "تقاضای سنگین‌تر از عرضه؛ صف قطعی تأیید نشده"
    elif imbalance is not None:
        queue_state = "برتری صف/تقاضا تأیید نشد"
    else:
        queue_state = "داده صف کافی نیست"

    if last_price is not None and sma20 is not None and sma50 is not None:
        trend_state = "ساختار صعودی: قیمت بالای SMA20 و SMA20 بالای SMA50" if last_price > sma20 > sma50 else "ساختار صعودی کامل تأیید نشد"
    else:
        trend_state = "داده میانگین 20/50 روزه کافی نیست"

    volume_parts = []
    if volume_ratio is not None:
        volume_parts.append(f"نسبت حجم ۵ به ۲۰ روزه: {volume_ratio:.2f}x")
    if value_ratio is not None:
        volume_parts.append(f"نسبت ارزش ۵ به ۲۰ روزه: {value_ratio:.2f}x")
    if volume_ratio_5_to_50 is not None:
        volume_parts.append(f"نسبت حجم ۵ به ۵۰ روزه: {volume_ratio_5_to_50:.2f}x")
    volume_state = " | ".join(volume_parts) if volume_parts else "داده حجم/ارزش کافی نیست"

    supportive = (
        queue_state.startswith("صف خرید قابل")
        and last_price is not None and sma20 is not None and sma50 is not None
        and last_price > sma20 > sma50
        and volume_ratio is not None and volume_ratio >= 1.0
    )
    persistence_evidence = (
        "مثبت: صف/تقاضا + ساختار قیمت + حجم هم‌جهت هستند؛ تداوم صف برای جلسه بعد قطعی نیست."
        if supportive
        else "شواهد کافی برای تأیید هم‌زمان صف، روند و حجم وجود ندارد."
    )

    return {
        "status": context.get("status", "PARTIAL"),
        "queue_state": queue_state,
        "trend_state": trend_state,
        "volume_state": volume_state,
        "persistence_evidence": persistence_evidence,
        "touched_upper_limit_today": context.get("touched_upper_limit_today"),
        "upper_limit_headroom_pct": upper_headroom,
        "volume_ratio_5_to_20": volume_ratio,
        "volume_ratio_5_to_50": volume_ratio_5_to_50,
        "value_ratio_5_to_20": value_ratio,
        "orderbook_imbalance_5": imbalance,
    }


def build_last_minute_ranking(rows: list[dict[str, Any]], *, top_count=15, now=None, underlying_context=None) -> dict[str, Any]:
    candidates = []
    excluded = {
        "not_one_day_to_expiry": 0,
        "not_itm": 0,
        "missing_or_invalid_data": 0,
        "non_positive_scenario_return": 0,
    }

    for row in list(rows or []):
        canonical = row.get("canonical") or {}
        identity = row.get("identity") or {}
        days = _days_to_expiry(row, now=now)
        typ = str(identity.get("contract_type") or "").upper()
        spot = _num(canonical.get("قیمت سهم پایه"))
        strike = _num(canonical.get("قیمت اعمال"))
        option_price = _num(canonical.get("آخرین قیمت"))

        if days != TARGET_DAYS_TO_EXPIRY:
            excluded["not_one_day_to_expiry"] += 1
            continue
        if typ not in {"CALL", "PUT"} or None in (spot, strike, option_price) or spot <= 0 or strike <= 0 or option_price <= 0:
            excluded["missing_or_invalid_data"] += 1
            continue
        if not _is_itm(typ, spot, strike):
            excluded["not_itm"] += 1
            continue

        item = _scenario(row, now=now)
        if item is None:
            excluded["missing_or_invalid_data"] += 1
            continue
        if item["scenario_return_pct"] <= 0:
            excluded["non_positive_scenario_return"] += 1
            continue
        candidates.append(item)

    candidates.sort(
        key=lambda x: (
            x["scenario_return_pct"],
            x["leverage"],
            str(x.get("instrument_id") or ""),
        ),
        reverse=True,
    )
    ranked = candidates[: int(top_count)]

    context_map = underlying_context or {}
    for rank, item in enumerate(ranked, 1):
        item["rank"] = rank
        context = context_map.get(str(item.get("underlying_id") or ""))
        item["underlying_analysis"] = analyze_underlying_context(context)

    return {
        "status": "PASS" if ranked else "NO_ELIGIBLE_OPPORTUNITY",
        "mode": "LAST_MINUTE_PROFIT",
        "source_of_truth": "TSETMC",
        "scenario_underlying_move_pct": UNDERLYING_SCENARIO_UP * 100.0,
        "target_days_to_expiry": TARGET_DAYS_TO_EXPIRY,
        "eligibility": {
            "exactly_one_day_to_expiry": True,
            "current_itm_only": True,
            "positive_scenario_return_only": True,
        },
        "candidate_count": len(candidates),
        "display_count": len(ranked),
        "excluded_counts": excluded,
        "ranking_rows": ranked,
    }
