#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only base-share intelligence built from explicit market records."""

from __future__ import annotations

import math
from typing import Any, Iterable

import pandas as pd

ENGINE_VERSION = "BASE-SHARE-SHADOW-1.0"


def _num(record: dict[str, Any], key: str) -> float | None:
    try:
        value = record.get(key)
        if value is None or pd.isna(value):
            return None
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _direction(current: float | None, previous: float | None) -> str:
    if current is None or previous is None:
        return "INSUFFICIENT_DATA"
    if current > previous:
        return "UP"
    if current < previous:
        return "DOWN"
    return "UNCHANGED"


def _change(current: float | None, previous: float | None) -> dict[str, Any]:
    if current is None or previous is None:
        return {
            "current": current,
            "previous": previous,
            "direction": "INSUFFICIENT_DATA",
            "delta": None,
            "percent_change": None,
        }
    delta = current - previous
    pct = (delta / abs(previous) * 100.0) if previous != 0 else None
    return {
        "current": current,
        "previous": previous,
        "direction": _direction(current, previous),
        "delta": delta,
        "percent_change": pct,
    }


def _index(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for record in records:
        instrument_id = record.get("instrument_id")
        if instrument_id in (None, ""):
            continue
        result[str(instrument_id)] = record
    return result


def _option_context(option_records: Iterable[dict[str, Any]], underlying_id: str) -> dict[str, Any]:
    linked = [
        r for r in option_records
        if str(r.get("underlying_id") or "") == str(underlying_id)
    ]

    def total(field):
        values = [_num(r, field) for r in linked]
        values = [v for v in values if v is not None]
        return sum(values) if values else None

    def average(field):
        values = [_num(r, field) for r in linked]
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else None

    scores = [_num(r, "FinalScore") for r in linked]
    scores = [v for v in scores if v is not None]

    return {
        "linked_option_count": len(linked),
        "option_volume_total": total("volume"),
        "option_trade_value_total": total("trade_value"),
        "option_last_price_average": average("last_price"),
        "option_final_score_max": max(scores) if scores else None,
        "identity_rule": "EXPLICIT_UNDERLYING_ID_ONLY",
    }


def build_base_share_intelligence(
    current_records: Iterable[dict[str, Any]],
    previous_records: Iterable[dict[str, Any]] | None = None,
    option_records: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    current = _index(current_records)
    previous = _index(previous_records or [])
    options = list(option_records or [])

    rows = []
    for instrument_id in sorted(current):
        now = current[instrument_id]
        old = previous.get(instrument_id)

        last_price = _num(now, "last_price")
        prev_price = _num(old, "last_price") if old else None
        volume = _num(now, "volume")
        prev_volume = _num(old, "volume") if old else None
        trade_value = _num(now, "trade_value")
        prev_trade_value = _num(old, "trade_value") if old else None
        close_price = _num(now, "close_price")

        last_vs_close = None
        if last_price is not None and close_price not in (None, 0):
            last_vs_close = (last_price - close_price) / abs(close_price) * 100.0

        row = {
            "instrument_id": instrument_id,
            "symbol": now.get("symbol"),
            "market_timestamp": now.get("market_timestamp"),
            "sequence_state": "NEW" if old is None else "PERSISTENT",
            "last_price": _change(last_price, prev_price),
            "volume": _change(volume, prev_volume),
            "trade_value": _change(trade_value, prev_trade_value),
            "last_vs_close_pct": last_vs_close,
            "source_rule": "TSETMC_OR_EXPLICIT_MARKET_SOURCE",
        }

        if option_records is not None:
            row["option_context"] = _option_context(options, instrument_id)
        else:
            row["option_context"] = {"status": "NOT_AVAILABLE"}

        rows.append(row)

    summary = {
        "instruments_current": len(current),
        "new_instruments": sum(r["sequence_state"] == "NEW" for r in rows),
        "persistent_instruments": sum(r["sequence_state"] == "PERSISTENT" for r in rows),
        "price_up": sum(r["last_price"]["direction"] == "UP" for r in rows),
        "price_down": sum(r["last_price"]["direction"] == "DOWN" for r in rows),
        "price_unchanged": sum(r["last_price"]["direction"] == "UNCHANGED" for r in rows),
        "option_linking_rule": "EXPLICIT_UNDERLYING_ID_ONLY",
    }

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "summary": summary,
        "rows": rows,
    }
