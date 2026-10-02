#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic option Greeks/Black-Scholes metrics from TSETMC evidence only.

Model convention:
- Spot, strike, option premium and expiry come from TSETMC.
- Volatility is annualized historical volatility from TSETMC daily closes.
- Risk-free rate is a documented model convention of 0.0%, not an observed rate.
- Dividend yield is 0.0% because no TSETMC dividend-yield input is used.
- If the required TSETMC history is insufficient, the metric remains unavailable.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any


MIN_HISTORY_RETURNS = 20
HISTORY_TOP = 60
RISK_FREE_RATE = 0.0
DIVIDEND_YIELD = 0.0


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _history_prices(payload: Any) -> list[float]:
    rows = payload if isinstance(payload, list) else []
    dated: list[tuple[str, float]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        price = _num(
            row.get("pClosing")
            if row.get("pClosing") not in (None, "")
            else row.get("closingPrice")
        )
        date = row.get("dEven") or row.get("date") or row.get("DEven")
        if price is None or price <= 0 or date in (None, ""):
            continue
        try:
            dated.append((str(date), price))
        except Exception:
            continue
    dated.sort(key=lambda x: x[0])
    return [p for _, p in dated]


def historical_volatility(adapter, underlying_id: str) -> tuple[float | None, dict[str, Any]]:
    try:
        result = adapter.daily_history(str(underlying_id), top=HISTORY_TOP)
        data = result.get("data") or []
        prices = _history_prices(data)
        returns = [
            math.log(prices[i] / prices[i - 1])
            for i in range(1, len(prices))
            if prices[i] > 0 and prices[i - 1] > 0
        ]
        if len(returns) < MIN_HISTORY_RETURNS:
            return None, {
                "status": "INSUFFICIENT_HISTORY",
                "history_observations": len(prices),
                "return_observations": len(returns),
                "source": "TSETMC",
                "endpoint": result.get("endpoint"),
            }
        sample = returns[-MIN_HISTORY_RETURNS:]
        mean = sum(sample) / len(sample)
        variance = sum((x - mean) ** 2 for x in sample) / (len(sample) - 1)
        hv = math.sqrt(max(variance, 0.0)) * math.sqrt(252.0)
        if not math.isfinite(hv) or hv <= 0:
            return None, {
                "status": "INVALID_HV",
                "history_observations": len(prices),
                "return_observations": len(returns),
                "source": "TSETMC",
            }
        return hv, {
            "status": "SUCCESS",
            "history_observations": len(prices),
            "return_observations": len(returns),
            "volatility_observations": len(sample),
            "source": "TSETMC",
            "endpoint": result.get("endpoint"),
            "volatility_basis": "HV_20_DAILY_LOG_RETURNS_ANNUALIZED",
        }
    except Exception as exc:
        return None, {
            "status": "SOURCE_UNAVAILABLE",
            "source": "TSETMC",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def black_scholes_metrics(spot: float, strike: float, premium: float, days: float,
                          volatility: float, contract_type: str) -> dict[str, float] | None:
    if min(spot, strike, premium, days, volatility) <= 0:
        return None
    t = days / 365.0
    if t <= 0:
        return None
    sigma_sqrt_t = volatility * math.sqrt(t)
    if sigma_sqrt_t <= 0:
        return None
    d1 = (
        math.log(spot / strike)
        + (RISK_FREE_RATE - DIVIDEND_YIELD + 0.5 * volatility * volatility) * t
    ) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t
    disc_r = math.exp(-RISK_FREE_RATE * t)
    disc_q = math.exp(-DIVIDEND_YIELD * t)
    call_value = spot * disc_q * _norm_cdf(d1) - strike * disc_r * _norm_cdf(d2)
    put_value = strike * disc_r * _norm_cdf(-d2) - spot * disc_q * _norm_cdf(-d1)
    typ = str(contract_type or "").upper()
    if typ == "CALL":
        value = call_value
        delta = disc_q * _norm_cdf(d1)
    elif typ == "PUT":
        value = put_value
        delta = disc_q * (_norm_cdf(d1) - 1.0)
    else:
        return None
    return {
        "black_scholes": value,
        "delta": delta,
        "implied_volatility": None,
        "historical_volatility": volatility,
        "d1": d1,
        "d2": d2,
        "risk_free_rate": RISK_FREE_RATE,
        "dividend_yield": DIVIDEND_YIELD,
        "time_years": t,
        "market_premium": premium,
        "model_minus_market": value - premium,
    }


def attach_option_model_metrics(rows: list[dict[str, Any]], adapter) -> list[dict[str, Any]]:
    cache: dict[str, tuple[float | None, dict[str, Any]]] = {}
    for row in rows:
        canonical = row.get("canonical") or {}
        identity = row.get("identity") or {}
        underlying_id = str(identity.get("underlying_id") or "").strip()
        try:
            spot = float(canonical.get("قیمت سهم پایه"))
            strike = float(canonical.get("قیمت اعمال"))
            premium = float(canonical.get("آخرین قیمت"))
            days = float(canonical.get("روزهای تقویمی"))
        except (TypeError, ValueError):
            row["option_model"] = {"status": "INSUFFICIENT_INPUT"}
            continue
        if not underlying_id:
            row["option_model"] = {"status": "UNDERLYING_ID_UNAVAILABLE"}
            continue
        if underlying_id not in cache:
            cache[underlying_id] = historical_volatility(adapter, underlying_id)
        hv, evidence = cache[underlying_id]
        if hv is None:
            row["option_model"] = {"status": evidence.get("status"), "evidence": evidence}
            continue
        metrics = black_scholes_metrics(
            spot, strike, premium, days, hv, identity.get("contract_type")
        )
        if metrics is None:
            row["option_model"] = {"status": "MODEL_INPUT_INVALID", "evidence": evidence}
            continue
        row["option_model"] = {
            "status": "SUCCESS",
            "source_of_market_inputs": "TSETMC",
            "evidence": evidence,
            **metrics,
        }
    return rows
