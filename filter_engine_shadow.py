#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Explicit rule/filter evaluator for Shadow analytical features."""

from __future__ import annotations

import math
from typing import Any, Iterable

ENGINE_VERSION = "FILTER-SHADOW-1.0"

SUPPORTED = {"EQ", "NE", "GT", "GTE", "LT", "LTE", "IN", "NOT_IN", "IS_MISSING", "IS_PRESENT"}


def _get_path(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for part in str(path).split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(math.isnan(float(value)))
    except (TypeError, ValueError):
        return False


def evaluate_rule(record: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    field = rule.get("field")
    operator = str(rule.get("operator", "")).upper()
    expected = rule.get("value")

    if not field or operator not in SUPPORTED:
        return {
            "status": "INVALID_RULE",
            "field": field,
            "operator": operator,
            "reason": "Rule field/operator is missing or unsupported.",
        }

    actual = _get_path(record, field)
    if operator == "IS_MISSING":
        matched = _missing(actual)
    elif operator == "IS_PRESENT":
        matched = not _missing(actual)
    elif _missing(actual):
        return {
            "status": "INSUFFICIENT_DATA",
            "field": field,
            "operator": operator,
            "actual": None,
            "expected": expected,
        }
    elif operator == "EQ":
        matched = actual == expected
    elif operator == "NE":
        matched = actual != expected
    elif operator == "GT":
        matched = actual > expected
    elif operator == "GTE":
        matched = actual >= expected
    elif operator == "LT":
        matched = actual < expected
    elif operator == "LTE":
        matched = actual <= expected
    elif operator == "IN":
        matched = actual in expected
    elif operator == "NOT_IN":
        matched = actual not in expected
    else:
        return {"status": "INVALID_RULE"}

    return {
        "status": "MATCH" if matched else "NO_MATCH",
        "field": field,
        "operator": operator,
        "actual": actual,
        "expected": expected,
    }


def evaluate_filter(
    record: dict[str, Any],
    rules: Iterable[dict[str, Any]],
    *,
    mode: str = "ALL",
) -> dict[str, Any]:
    normalized_mode = str(mode).upper()
    if normalized_mode not in {"ALL", "ANY"}:
        raise ValueError("mode must be ALL or ANY")

    results = [evaluate_rule(record, rule) for rule in rules]
    if not results:
        return {
            "status": "INVALID_FILTER",
            "mode": normalized_mode,
            "matched": False,
            "rules": [],
        }

    invalid = [r for r in results if r["status"] == "INVALID_RULE"]
    incomplete = [r for r in results if r["status"] == "INSUFFICIENT_DATA"]
    matched_results = [r for r in results if r["status"] == "MATCH"]

    if invalid:
        status = "INVALID_FILTER"
        matched = False
    elif normalized_mode == "ALL":
        matched = len(matched_results) == len(results)
        status = "MATCH" if matched else "INSUFFICIENT_DATA" if incomplete else "NO_MATCH"
    else:
        matched = bool(matched_results)
        status = "MATCH" if matched else "INSUFFICIENT_DATA" if incomplete else "NO_MATCH"

    return {
        "status": status,
        "mode": normalized_mode,
        "matched": matched,
        "rules": results,
    }
