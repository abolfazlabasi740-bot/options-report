#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Historical replay/calibration engine for OptimusAI V4.1.

This module converts archived TSETMC snapshots into observed forward option
returns and deterministic, evidence-derived rule candidates. It does not
authorize production signals and never invents missing values.
"""
from __future__ import annotations

import json
from datetime import datetime
from math import isfinite
from pathlib import Path
from statistics import median
from typing import Any

ENGINE_VERSION = "REPLAY-CALIBRATION-1.0"
SOURCE_OF_TRUTH = "TSETMC"

FEATURES = (
    "time_value_ratio",
    "breakeven_distance",
    "leverage",
    "calendar_days",
    "trade_value",
    "volume",
    "last_vs_close",
)


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        x = float(value)
        return x if isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _obs_time(snapshot: dict[str, Any]) -> str | None:
    value = snapshot.get("observation_retrieved_at")
    if isinstance(value, str) and value.strip():
        return value
    value = snapshot.get("generated_at")
    return value if isinstance(value, str) and value.strip() else None


def _identity_id(row: dict[str, Any]) -> str | None:
    value = (row.get("identity") or {}).get("instrument_id")
    return str(value).strip() if value not in (None, "") else None


def _canonical(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("canonical") or {}


def _features(row: dict[str, Any]) -> dict[str, float | None]:
    canonical = _canonical(row)
    underlying = _num(canonical.get("قیمت سهم پایه"))
    option = _num(canonical.get("آخرین قیمت"))
    strike = _num(canonical.get("قیمت اعمال"))
    volume = _num(canonical.get("حجم معاملات"))
    value = _num(canonical.get("ارزش معاملات"))
    close = _num(canonical.get("قیمت پایانی"))

    contract_type = (row.get("identity") or {}).get("contract_type")
    intrinsic = None
    if underlying is not None and strike is not None:
        if contract_type == "CALL":
            intrinsic = max(underlying - strike, 0.0)
        elif contract_type == "PUT":
            intrinsic = max(strike - underlying, 0.0)

    time_value_ratio = None
    if option is not None and intrinsic is not None and underlying not in (None, 0):
        time_value_ratio = max(option - intrinsic, 0.0) / abs(underlying)

    breakeven = None
    if strike is not None and option is not None:
        if contract_type == "CALL":
            breakeven = strike + option
        elif contract_type == "PUT":
            breakeven = strike - option

    breakeven_distance = None
    if breakeven is not None and underlying not in (None, 0):
        breakeven_distance = abs(breakeven - underlying) / abs(underlying)

    leverage = None
    if underlying is not None and option is not None and option > 0:
        leverage = underlying / option

    last_vs_close = None
    if option is not None and close not in (None, 0):
        last_vs_close = abs(option - close) / abs(close)

    expiry = canonical.get("تاریخ سررسید")
    calendar_days = _calendar_days(expiry, _canonical(row).get("تاریخ"))
    return {
        "time_value_ratio": time_value_ratio,
        "breakeven_distance": breakeven_distance,
        "leverage": leverage,
        "calendar_days": calendar_days,
        "trade_value": value,
        "volume": volume,
        "last_vs_close": last_vs_close,
    }


def _calendar_days(expiry: Any, observation_date: Any) -> float | None:
    if not isinstance(expiry, str) or not expiry.strip():
        return None
    if not isinstance(observation_date, str) or not observation_date.strip():
        return None
    e = expiry.strip().replace("-", "")
    d = observation_date.strip().replace("-", "")
    if len(e) != 8 or len(d) != 8 or not e.isdigit() or not d.isdigit():
        return None
    try:
        from datetime import date
        return float((date(int(e[:4]), int(e[4:6]), int(e[6:8])) -
                      date(int(d[:4]), int(d[4:6]), int(d[6:8]))).days)
    except ValueError:
        return None


def _pct_change(entry: float | None, forward: float | None) -> float | None:
    if entry is None or forward is None or entry == 0:
        return None
    return (forward - entry) / abs(entry)


def _load(root: Path) -> list[dict[str, Any]]:
    paths = sorted((root / "output" / "history" / "tsetmc").glob("*.json"))
    snapshots = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("source_of_truth") != SOURCE_OF_TRUTH:
            continue
        if not payload.get("snapshot_sha256") or not isinstance(payload.get("rows"), list):
            continue
        snapshots.append(payload)
    snapshots.sort(key=lambda x: (_timestamp(_obs_time(x)) or datetime.min,
                                  str(x.get("snapshot_sha256"))))
    return snapshots


def build_replay_observations(root: Path) -> list[dict[str, Any]]:
    snapshots = _load(root)
    observations = []
    for entry_snapshot, forward_snapshot in zip(snapshots, snapshots[1:]):
        entry_time = _timestamp(_obs_time(entry_snapshot))
        forward_time = _timestamp(_obs_time(forward_snapshot))
        elapsed_minutes = None
        if entry_time and forward_time:
            elapsed_minutes = (forward_time - entry_time).total_seconds() / 60.0

        entry_rows = {_identity_id(r): r for r in entry_snapshot["rows"] if _identity_id(r)}
        forward_rows = {_identity_id(r): r for r in forward_snapshot["rows"] if _identity_id(r)}

        for instrument_id in sorted(set(entry_rows) & set(forward_rows)):
            entry = entry_rows[instrument_id]
            forward = forward_rows[instrument_id]
            ec = _canonical(entry)
            fc = _canonical(forward)
            entry_last = _num(ec.get("آخرین قیمت"))
            forward_last = _num(fc.get("آخرین قیمت"))
            entry_underlying = _num(ec.get("قیمت سهم پایه"))
            forward_underlying = _num(fc.get("قیمت سهم پایه"))
            contract_type = (entry.get("identity") or {}).get("contract_type")
            if contract_type not in {"CALL", "PUT"}:
                continue
            observations.append({
                "instrument_id": instrument_id,
                "symbol": ec.get("نماد"),
                "contract_type": contract_type,
                "entry_snapshot_sha256": entry_snapshot["snapshot_sha256"],
                "forward_snapshot_sha256": forward_snapshot["snapshot_sha256"],
                "entry_observation_time": _obs_time(entry_snapshot),
                "forward_observation_time": _obs_time(forward_snapshot),
                "elapsed_minutes": elapsed_minutes,
                "entry_last": entry_last,
                "forward_last": forward_last,
                "option_return_pct": _pct_change(entry_last, forward_last),
                "entry_underlying": entry_underlying,
                "forward_underlying": forward_underlying,
                "underlying_return_pct": _pct_change(entry_underlying, forward_underlying),
                "entry_features": _features(entry),
                "observed_outcome": (
                    "POSITIVE_OPTION_RETURN"
                    if _pct_change(entry_last, forward_last) is not None
                    and _pct_change(entry_last, forward_last) > 0
                    else "NON_POSITIVE_OR_UNAVAILABLE"
                ),
                "labels": "OBSERVED_RETURN_ONLY",
                "signal_generation": "FORBIDDEN",
                "external_sources": "FORBIDDEN",
            })
    return observations


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    frac = pos - lo
    return values[lo] + (values[hi] - values[lo]) * frac


def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    returns = [r["option_return_pct"] for r in rows if r.get("option_return_pct") is not None]
    positive = sum(1 for x in returns if x > 0)
    return {
        "count": len(returns),
        "positive_count": positive,
        "positive_rate": (positive / len(returns)) if returns else None,
        "mean_return_pct": (sum(returns) / len(returns)) if returns else None,
        "median_return_pct": median(returns) if returns else None,
        "p25_return_pct": _percentile(returns, 0.25),
        "p75_return_pct": _percentile(returns, 0.75),
    }


def _rule_rows(observations: list[dict[str, Any]], feature: str, threshold: float, op: str) -> list[dict[str, Any]]:
    rows = []
    for row in observations:
        value = (row.get("entry_features") or {}).get(feature)
        if value is None or row.get("option_return_pct") is None:
            continue
        matched = value <= threshold if op == "LE" else value >= threshold
        if matched:
            rows.append(row)
    return rows


def calibrate_rule_candidates(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = []
    for feature in FEATURES:
        values = [
            (r.get("entry_features") or {}).get(feature)
            for r in observations
            if (r.get("entry_features") or {}).get(feature) is not None
        ]
        for percentile_name, p in (("P25", 0.25), ("P50", 0.50), ("P75", 0.75)):
            threshold = _percentile([float(x) for x in values], p)
            if threshold is None:
                continue
            for op in ("LE", "GE"):
                matched = _rule_rows(observations, feature, threshold, op)
                stats = _stats(matched)
                rules.append({
                    "feature": feature,
                    "operator": op,
                    "threshold_source": percentile_name,
                    "threshold": threshold,
                    "scope": "OBSERVED_REPLAY",
                    "stats": stats,
                })
    return rules


def build_replay_calibration(root: Path) -> dict[str, Any]:
    observations = build_replay_observations(root)
    rules = calibrate_rule_candidates(observations)
    return {
        "status": "PASS",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": SOURCE_OF_TRUTH,
        "snapshot_count": len(_load(root)),
        "observation_count": len(observations),
        "rule_candidate_count": len(rules),
        "observations": observations,
        "rule_candidates": rules,
        "rules": {
            "matching": "EXACT_INSTRUMENT_ID_ONLY",
            "outcome": "OBSERVED_FORWARD_OPTION_RETURN",
            "threshold_source": "EMPIRICAL_ENTRY_FEATURE_PERCENTILES",
            "labels": "OBSERVED_RETURN_ONLY",
            "signal_generation": "FORBIDDEN",
            "external_sources": "FORBIDDEN",
            "transaction_costs": "NOT_ASSUMED",
            "slippage": "NOT_ASSUMED",
            "short_option_authorization": "FORBIDDEN",
        },
    }
