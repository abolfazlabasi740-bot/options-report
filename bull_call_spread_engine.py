#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bull Call Spread strategy engine for TSETMC option snapshots.

Fail-closed: no strategy is produced when required structural or pricing
evidence is missing. This module does not place orders and does not create
buy/sell signals.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Iterable


ENGINE_VERSION = "BULL-CALL-SPREAD-1.0"
STRATEGY = "BULL_CALL_SPREAD"
SOURCE_OF_TRUTH = "TSETMC"


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if isfinite(x) else None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _identity(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("identity") or {}


def _canonical(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("canonical") or {}


def _field(row: dict[str, Any], *keys: str) -> Any:
    c = _canonical(row)
    for key in keys:
        if key in c:
            return c[key]
    return None


def _underlying(row: dict[str, Any]) -> str | None:
    i = _identity(row)
    return _text(i.get("underlying_symbol") or _field(row, "نماد سهم پایه", "underlying_symbol"))


def _expiry(row: dict[str, Any]) -> str | None:
    return _text(_field(row, "تاریخ سررسید", "expiry"))


def _strike(row: dict[str, Any]) -> float | None:
    return _num(_field(row, "قیمت اعمال", "strike"))


def _last(row: dict[str, Any]) -> float | None:
    return _num(_field(row, "آخرین قیمت", "option_last", "last"))


def _contract_type(row: dict[str, Any]) -> str | None:
    value = _identity(row).get("contract_type")
    if value is None:
        value = _field(row, "نوع قرارداد", "contract_type")
    return _text(value)


def _instrument_id(row: dict[str, Any]) -> str | None:
    return _text(_identity(row).get("instrument_id") or row.get("instrument_id"))


def _liquidity(row: dict[str, Any]) -> dict[str, float | None]:
    return {
        "volume": _num(_field(row, "حجم", "volume")),
        "trade_value": _num(_field(row, "ارزش معاملات", "trade_value")),
        "open_interest": _num(_field(row, "موقعیت های باز", "open_interest")),
    }


def _is_call(row: dict[str, Any]) -> bool:
    value = (_contract_type(row) or "").lower()
    return value in {"call", "c", "اختیار خرید", "خرید"}


@dataclass(frozen=True)
class BullCallSpread:
    long_call: dict[str, Any]
    short_call: dict[str, Any]
    underlying_symbol: str
    expiry: str
    lower_strike: float
    higher_strike: float
    long_premium: float
    short_premium: float
    net_debit: float
    max_loss: float
    max_profit: float
    breakeven: float
    payoff_at_expiry: str = "max(S-K1,0)-max(S-K2,0)-net_debit"

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy": STRATEGY,
            "engine_version": ENGINE_VERSION,
            "source_of_truth": SOURCE_OF_TRUTH,
            "status": "PASS",
            "underlying_symbol": self.underlying_symbol,
            "expiry": self.expiry,
            "long_call_instrument_id": _instrument_id(self.long_call),
            "short_call_instrument_id": _instrument_id(self.short_call),
            "long_call_symbol": _text(_field(self.long_call, "نماد", "symbol")),
            "short_call_symbol": _text(_field(self.short_call, "نماد", "symbol")),
            "lower_strike": self.lower_strike,
            "higher_strike": self.higher_strike,
            "long_premium": self.long_premium,
            "short_premium": self.short_premium,
            "net_debit": self.net_debit,
            "max_loss": self.max_loss,
            "max_profit": self.max_profit,
            "breakeven": self.breakeven,
            "payoff_at_expiry": self.payoff_at_expiry,
            "execution_signal": False,
            "buy_sell_recommendation": False,
        }


def form_bull_call_spread(long_call: dict[str, Any], short_call: dict[str, Any]) -> BullCallSpread | None:
    """Form one spread only when every structural/pricing requirement is evidenced."""
    if not isinstance(long_call, dict) or not isinstance(short_call, dict):
        return None

    if not _is_call(long_call) or not _is_call(short_call):
        return None

    underlying_long = _underlying(long_call)
    underlying_short = _underlying(short_call)
    expiry_long = _expiry(long_call)
    expiry_short = _expiry(short_call)
    k1 = _strike(long_call)
    k2 = _strike(short_call)
    p1 = _last(long_call)
    p2 = _last(short_call)

    if None in (underlying_long, underlying_short, expiry_long, expiry_short, k1, k2, p1, p2):
        return None
    if underlying_long != underlying_short or expiry_long != expiry_short:
        return None
    if _instrument_id(long_call) == _instrument_id(short_call):
        return None
    if k1 >= k2:
        return None
    if p1 < 0 or p2 < 0:
        return None

    net_debit = p1 - p2
    if net_debit <= 0:
        return None

    width = k2 - k1
    max_loss = net_debit
    max_profit = width - net_debit
    if max_profit <= 0:
        return None

    breakeven = k1 + net_debit
    return BullCallSpread(
        long_call=long_call,
        short_call=short_call,
        underlying_symbol=underlying_long,
        expiry=expiry_long,
        lower_strike=k1,
        higher_strike=k2,
        long_premium=p1,
        short_premium=p2,
        net_debit=net_debit,
        max_loss=max_loss,
        max_profit=max_profit,
        breakeven=breakeven,
    )


def _liquidity_score(spread: BullCallSpread) -> float | None:
    values: list[float] = []
    for row in (spread.long_call, spread.short_call):
        liq = _liquidity(row)
        observed = [v for v in liq.values() if v is not None and v >= 0]
        if not observed:
            return None
        values.append(sum(observed))
    return min(values)


def rank_bull_call_spreads(
    rows: Iterable[dict[str, Any]], top_count: int = 15
) -> list[dict[str, Any]]:
    """Build all valid same-underlying/same-expiry Bull Call Spreads.

    Ranking is deterministic and only uses evidenced fields. If required
    liquidity evidence is absent on either leg, the candidate is excluded.
    """
    calls = [r for r in rows if isinstance(r, dict) and _is_call(r)]
    candidates: list[tuple[float, float, dict[str, Any]]] = []

    for i, first in enumerate(calls):
        for second in calls[i + 1 :]:
            a, b = first, second
            ka, kb = _strike(a), _strike(b)
            if ka is None or kb is None:
                continue
            if ka < kb:
                long_call, short_call = a, b
            elif kb < ka:
                long_call, short_call = b, a
            else:
                continue

            spread = form_bull_call_spread(long_call, short_call)
            if spread is None:
                continue

            liquidity = _liquidity_score(spread)
            if liquidity is None:
                continue

            efficiency = spread.max_profit / spread.max_loss
            result = spread.as_dict()
            result["liquidity_evidence"] = liquidity
            result["profit_loss_efficiency"] = efficiency
            candidates.append((efficiency, liquidity, result))

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [item[2] for item in candidates[: max(0, int(top_count))]]


def build_strategy_report(rows: Iterable[dict[str, Any]], top_count: int = 15) -> dict[str, Any]:
    ranked = rank_bull_call_spreads(rows, top_count=top_count)
    return {
        "status": "PASS" if ranked else "NO_VALID_CANDIDATE",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": SOURCE_OF_TRUTH,
        "strategy": STRATEGY,
        "candidate_count": len(ranked),
        "execution_signal": False,
        "buy_sell_recommendation": False,
        "fail_closed": True,
        "results": ranked,
    }
