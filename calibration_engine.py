#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only calibration primitives for OptimusAI V4.1.

This module does not create trading labels or authorize signals. It summarizes
observed TSETMC candidate features so future strategy thresholds can be derived
from replay evidence rather than guessed constants.
"""
from __future__ import annotations

from math import isfinite
from typing import Any

CALIBRATION_ENGINE_VERSION = "CALIBRATION-1.0"

CALIBRATION_FEATURES = (
    "trade_value",
    "volume",
    "time_value_ratio",
    "breakeven_distance",
    "leverage",
    "calendar_days",
    "last_vs_close",
    "intraday_range",
)


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
    frac = pos - lo
    return values[lo] + (values[hi] - values[lo]) * frac


def _values(candidates: list[dict[str, Any]], feature: str) -> list[float]:
    out = []
    for candidate in candidates:
        features = ((candidate.get("evidence") or {}).get("features") or {})
        value = _num(features.get(feature))
        if value is not None:
            out.append(value)
    return out


def summarize_feature(candidates: list[dict[str, Any]], feature: str) -> dict[str, Any]:
    values = _values(candidates, feature)
    return {
        "feature": feature,
        "count": len(values),
        "coverage": (len(values) / len(candidates)) if candidates else 0.0,
        "p05": _percentile(values, 0.05),
        "p25": _percentile(values, 0.25),
        "p50": _percentile(values, 0.50),
        "p75": _percentile(values, 0.75),
        "p95": _percentile(values, 0.95),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def calibrate_candidates(candidates: list[dict[str, Any]] | None) -> dict[str, Any]:
    candidates = candidates or []
    return {
        "status": "PASS",
        "engine_version": CALIBRATION_ENGINE_VERSION,
        "candidate_count": len(candidates),
        "features": [
            summarize_feature(candidates, feature)
            for feature in CALIBRATION_FEATURES
        ],
        "rules": {
            "signal_generation": "FORBIDDEN",
            "threshold_generation": "OBSERVATION_ONLY",
            "labels": "NOT_INFERRED",
            "missing_values": "EXCLUDED_FROM_FEATURE_STATISTICS",
            "external_sources": "FORBIDDEN",
        },
    }
