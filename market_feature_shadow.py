#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only technical feature builder for explicit market history."""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

import pandas as pd

ENGINE_VERSION = "MARKET-FEATURE-SHADOW-1.0"


def _num(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _clean_bar(bar: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": bar.get("timestamp") or bar.get("date"),
        "close": _num(bar.get("close") or bar.get("last_price")),
        "high": _num(bar.get("high")),
        "low": _num(bar.get("low")),
        "volume": _num(bar.get("volume")),
        "trade_value": _num(bar.get("trade_value")),
    }


def _sma(values: Sequence[float | None], window: int) -> float | None:
    tail = [v for v in values[-window:] if v is not None]
    if len(tail) < window:
        return None
    return sum(tail) / window


def _direction(first: float | None, last: float | None) -> str:
    if first is None or last is None:
        return "INSUFFICIENT_DATA"
    if last > first:
        return "UP"
    if last < first:
        return "DOWN"
    return "UNCHANGED"


def build_market_features(
    histories: Iterable[dict[str, Any]],
    *,
    moving_average_windows: Sequence[int],
) -> dict[str, Any]:
    if not moving_average_windows:
        raise ValueError("moving_average_windows is required")
    windows = []
    for window in moving_average_windows:
        if isinstance(window, bool) or not isinstance(window, int) or window < 1:
            raise ValueError("moving average windows must be positive integers")
        windows.append(window)

    rows = []
    for instrument in histories:
        instrument_id = instrument.get("instrument_id")
        if instrument_id in (None, ""):
            continue

        bars = [_clean_bar(b) for b in instrument.get("bars", [])]
        bars.sort(key=lambda b: str(b.get("timestamp") or ""))
        closes = [b["close"] for b in bars]
        volumes = [b["volume"] for b in bars]
        current = bars[-1] if bars else None
        previous = bars[-2] if len(bars) > 1 else None

        close = current.get("close") if current else None
        prev_close = previous.get("close") if previous else None
        high = current.get("high") if current else None
        low = current.get("low") if current else None
        range_pct = None
        if close not in (None, 0) and high is not None and low is not None:
            range_pct = (high - low) / abs(close) * 100.0

        return_pct = None
        if close is not None and prev_close not in (None, 0):
            return_pct = (close - prev_close) / abs(prev_close) * 100.0

        volume_change_pct = None
        current_volume = current.get("volume") if current else None
        previous_volume = previous.get("volume") if previous else None
        if current_volume is not None and previous_volume not in (None, 0):
            volume_change_pct = (
                (current_volume - previous_volume) / abs(previous_volume) * 100.0
            )

        item = {
            "engine_version": ENGINE_VERSION,
            "instrument_id": str(instrument_id),
            "symbol": instrument.get("symbol"),
            "bar_count": len(bars),
            "latest_timestamp": current.get("timestamp") if current else None,
            "last_close": close,
            "return_pct": return_pct,
            "range_pct": range_pct,
            "volume_change_pct": volume_change_pct,
            "sequence_direction": _direction(
                next((v for v in closes if v is not None), None),
                next((v for v in reversed(closes) if v is not None), None),
            ),
            "features": {},
        }

        for window in windows:
            sma = _sma(closes, window)
            distance = None
            relation = "INSUFFICIENT_DATA"
            if close is not None and sma not in (None, 0):
                distance = (close - sma) / abs(sma) * 100.0
                relation = "ABOVE" if close > sma else "BELOW" if close < sma else "AT"

            item["features"][f"sma_{window}"] = sma
            item["features"][f"close_vs_sma_{window}_pct"] = distance
            item["features"][f"close_vs_sma_{window}_relation"] = relation
            item["features"][f"price_direction_{window}"] = _direction(
                closes[-window] if len(closes) >= window else None,
                close,
            )
            item["features"][f"volume_direction_{window}"] = _direction(
                volumes[-window] if len(volumes) >= window else None,
                current_volume,
            )

        rows.append(item)

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "moving_average_windows": windows,
        "instrument_count": len(rows),
        "rows": rows,
    }
