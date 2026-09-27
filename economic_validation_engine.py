#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Walk-forward economic validation for OptimusAI replay candidates.

This module evaluates deterministic feature rules out-of-sample using only
prior TSETMC observations. It does not generate production signals and does
not invent costs, slippage, labels, or market thresholds.
"""
from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Any

ENGINE_VERSION = "ECONOMIC-VALIDATION-1.0"
SOURCE_OF_TRUTH = "TSETMC"
PERCENTILES = (("P25", 0.25), ("P50", 0.50), ("P75", 0.75))
OPERATORS = ("LE", "GE")
MIN_TRAIN_SNAPSHOTS = 2


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        x = float(value)
        return x if isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def _groups(observations: list[dict[str, Any]]) -> list[str]:
    return sorted({
        str(r.get("entry_observation_time"))
        for r in observations
        if _time(r.get("entry_observation_time")) is not None
    }, key=lambda x: _time(x))


def _matched(rows: list[dict[str, Any]], feature: str, threshold: float, op: str) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        value = _num((row.get("entry_features") or {}).get(feature))
        ret = _num(row.get("option_return_pct"))
        if value is None or ret is None:
            continue
        if (value <= threshold if op == "LE" else value >= threshold):
            out.append(row)
    return out


def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    returns = [_num(r.get("option_return_pct")) for r in rows]
    returns = [x for x in returns if x is not None]
    positive = sum(1 for x in returns if x > 0)
    return {
        "count": len(returns),
        "positive_count": positive,
        "positive_rate": positive / len(returns) if returns else None,
        "mean_return_pct": sum(returns) / len(returns) if returns else None,
    }


def validate_walk_forward(observations: list[dict[str, Any]]) -> dict[str, Any]:
    groups = _groups(observations)
    results = []
    for idx in range(MIN_TRAIN_SNAPSHOTS, len(groups)):
        train_groups = set(groups[:idx])
        test_group = groups[idx]
        train = [r for r in observations if r.get("entry_observation_time") in train_groups]
        test = [r for r in observations if r.get("entry_observation_time") == test_group]
        for feature in sorted({
            f for r in train for f in (r.get("entry_features") or {})
            if any(_num((x.get("entry_features") or {}).get(f)) is not None for x in train)
        }):
            values = [_num((r.get("entry_features") or {}).get(feature)) for r in train]
            values = [x for x in values if x is not None]
            for name, p in PERCENTILES:
                threshold = _percentile(values, p)
                if threshold is None:
                    continue
                for op in OPERATORS:
                    matched = _matched(test, feature, threshold, op)
                    results.append({
                        "train_entry_snapshots": idx,
                        "test_entry_snapshot": test_group,
                        "feature": feature,
                        "operator": op,
                        "threshold_source": name,
                        "threshold": threshold,
                        "test_stats": _stats(matched),
                    })
    return {
        "status": "PASS",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": SOURCE_OF_TRUTH,
        "entry_snapshot_count": len(groups),
        "validation_window_count": max(0, len(groups) - MIN_TRAIN_SNAPSHOTS),
        "result_count": len(results),
        "results": results,
        "method": {
            "split": "CHRONOLOGICAL_WALK_FORWARD",
            "minimum_train_entry_snapshots": MIN_TRAIN_SNAPSHOTS,
            "threshold_source": "EMPIRICAL_TRAINING_FEATURE_PERCENTILES",
            "percentiles": ["P25", "P50", "P75"],
            "matching": "EXACT_INSTRUMENT_ID_ONLY",
            "outcome": "OBSERVED_FORWARD_OPTION_RETURN",
            "transaction_costs": "NOT_ASSUMED",
            "slippage": "NOT_ASSUMED",
            "labels": "OBSERVED_RETURN_ONLY",
            "signal_generation": "FORBIDDEN",
            "external_sources": "FORBIDDEN",
        },
    }
