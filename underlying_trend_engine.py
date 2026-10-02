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

ENGINE_VERSION = "TSETMC-UNDERLYING-TREND-1.0"
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
    value_ratio = (
        (_sma(values, 5) / _sma(values, 20))
        if _sma(values, 5) is not None and _sma(values, 20) not in (None, 0)
        else None
    )
    recent_high = max((_num(row.get("priceMax")) for row in rows[-20:] if _num(row.get("priceMax")) is not None), default=None)
    recent_low = min((_num(row.get("priceMin")) for row in rows[-20:] if _num(row.get("priceMin")) is not None), default=None)
    range_position = (
        (last_close - recent_low) / (recent_high - recent_low)
        if last_close is not None and recent_high is not None and recent_low is not None and recent_high > recent_low
        else None
    )

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
        "value_ratio_5_to_20": value_ratio,
        "range_position_20": range_position,
        "trend_state": trend_state,
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


def fetch_underlying_context(instrument_ids: list[str], adapter: TSETMCAdapter | None = None) -> dict[str, Any]:
    adapter = adapter or TSETMCAdapter()
    results = {}
    for instrument_id in sorted({str(x).strip() for x in instrument_ids if str(x).strip()}):
        try:
            history = adapter.daily_history(instrument_id, top=100)
            info = adapter.instrument_info(instrument_id)
            analysis = analyze_history(instrument_id, history, info)
            raw_rows = history.get("data") if isinstance(history.get("data"), list) else []
            exact_rows = [
                row for row in raw_rows
                if isinstance(row, dict) and str(row.get("insCode") or "").strip() == instrument_id
            ]
            archive_payload = {
                "archive_version": "TSETMC-UNDERLYING-HISTORY-1.0",
                "source_of_truth": "TSETMC",
                "instrument_id": instrument_id,
                "retrieved_at": history.get("retrieved_at"),
                "endpoint": history.get("endpoint"),
                "source_response_sha256": history.get("snapshot_sha256"),
                "rows": exact_rows,
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
                "interpretation": "NO_TECHNICAL_CLAIM",
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
            "technical_features": ["SMA_5", "SMA_10", "SMA_20", "SMA_50", "RSI_14", "MACD_12_26", "RETURN_5_20", "VOLUME_VALUE_RATIO_5_20"],
            "limit_headroom": "ONLY_WHEN_DAILY_HISTORY_DATE_MATCHES_CURRENT_TEHRAN_DATE",
            "missing_data": "UNAVAILABLE_NOT_ZERO",
            "signal_generation": "FORBIDDEN",
        },
    }
