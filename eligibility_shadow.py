#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only eligibility classification for the V4.1 Shadow layer.

This module deliberately does not change FinalScore, ranking, or production
eligibility. It explains why a row is active, expired, incomplete, or has a
leverage-data issue so Opportunity discovery can preserve the distinction.
"""

import math
import pandas as pd

ENGINE_VERSION = "ELIGIBILITY-SHADOW-1.0"


def _number(row, key):
    value = row.get(key)
    if value is None or pd.isna(value):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def classify_row(row, min_leverage=None):
    """Return an auditable, non-blocking classification for one scored row."""
    symbol = str(row.get("نماد", "")).strip()
    if not symbol or symbol in {"nan", "None", "<NA>"}:
        return {"status": "INVALID_MARKET_DATA", "reason": "MISSING_SYMBOL"}

    last = _number(row, "آخرین")
    if last is None:
        last = _number(row, "آخرین قیمت")
    base = _number(row, "پایه")
    if base is None:
        base = _number(row, "قیمت سهم پایه")
    remaining = _number(row, "RemainingDays")
    leverage = _number(row, "اهرم")
    score = _number(row, "FinalScore")

    if last is None or last <= 0 or base is None or base <= 0:
        return {
            "status": "INVALID_MARKET_DATA",
            "reason": "NON_POSITIVE_OR_MISSING_PRICE",
            "remaining_days": remaining,
            "leverage": leverage,
        }

    if remaining is None:
        return {
            "status": "MISSING_REMAINING_DAYS",
            "reason": "REMAINING_DAYS_UNAVAILABLE",
            "leverage": leverage,
        }

    if remaining <= 0:
        return {
            "status": "EXPIRED",
            "reason": "REMAINING_DAYS_NOT_POSITIVE",
            "remaining_days": remaining,
            "leverage": leverage,
        }

    if score is None:
        return {
            "status": "UNSCORABLE",
            "reason": "FINAL_SCORE_UNAVAILABLE",
            "remaining_days": remaining,
            "leverage": leverage,
        }

    if leverage is None:
        return {
            "status": "LEVERAGE_UNAVAILABLE",
            "reason": "LEVERAGE_MISSING_OR_INVALID",
            "remaining_days": remaining,
            "leverage": None,
        }

    if min_leverage is not None and leverage < float(min_leverage):
        return {
            "status": "LEVERAGE_LOW",
            "reason": "LEVERAGE_BELOW_PRODUCTION_REFERENCE",
            "remaining_days": remaining,
            "leverage": leverage,
            "min_leverage_reference": float(min_leverage),
        }

    return {
        "status": "ACTIVE_ELIGIBLE",
        "reason": "REQUIRED_MARKET_AND_SCORE_FIELDS_AVAILABLE",
        "remaining_days": remaining,
        "leverage": leverage,
    }


def classify_dataframe(scored, min_leverage=None):
    if not isinstance(scored, pd.DataFrame):
        raise TypeError("scored must be a pandas DataFrame")
    results = []
    for _, row in scored.iterrows():
        result = classify_row(row, min_leverage=min_leverage)
        result["symbol"] = str(row.get("نماد", "")).strip()
        results.append(result)

    counts = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "rows": results,
        "summary": {
            "rows_scanned": len(results),
            "counts": counts,
        },
    }
