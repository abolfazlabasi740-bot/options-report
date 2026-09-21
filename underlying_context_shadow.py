#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Explicit TSETMC underlying-context enrichment for OptimusAI V4.1 Shadow."""

from __future__ import annotations

import math
from typing import Any, Iterable

import pandas as pd

ENGINE_VERSION = "UNDERLYING-CONTEXT-SHADOW-1.0"


def _clean(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _first(record: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for key in aliases:
        if key in record:
            value = _clean(record[key])
            if value is not None:
                return value
    return None


def build_underlying_index(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index only explicit underlying instrument identifiers."""
    index: dict[str, dict[str, Any]] = {}
    for raw in records:
        record = dict(raw)
        instrument_id = _first(record, ("instrument_id", "insCode"))
        if instrument_id is None:
            continue
        key = str(instrument_id)
        # Duplicate IDs are not silently overwritten.
        if key in index:
            index[key] = {"_AMBIGUOUS": True}
        elif not index.get(key, {}).get("_AMBIGUOUS"):
            index[key] = record
    return index


def attach_underlying_context(
    canonical: pd.DataFrame,
    underlying_records: Iterable[dict[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Attach explicit underlying last/close data by underlying_id only.

    No symbol matching, prefix parsing, or inferred CALL/PUT semantics are used.
    Missing/ambiguous identifiers remain INSUFFICIENT_DATA.
    """
    if not isinstance(canonical, pd.DataFrame):
        raise TypeError("canonical must be a pandas DataFrame")
    if "underlying_id" not in canonical.columns:
        raise ValueError("canonical must contain underlying_id")

    index = build_underlying_index(underlying_records)
    out = canonical.copy()
    out["underlying_last_price"] = pd.NA
    out["underlying_close_price"] = pd.NA
    out["underlying_context_status"] = "INSUFFICIENT_DATA"
    out["underlying_source_ref"] = pd.NA

    exact = 0
    ambiguous = 0
    missing = 0

    for idx, row in out.iterrows():
        underlying_id = _clean(row.get("underlying_id"))
        if underlying_id is None:
            missing += 1
            continue
        record = index.get(str(underlying_id))
        if record is None:
            missing += 1
            continue
        if record.get("_AMBIGUOUS"):
            ambiguous += 1
            out.at[idx, "underlying_context_status"] = "AMBIGUOUS"
            continue

        last = _first(record, ("last_price", "pDrCotVal", "pl"))
        close = _first(record, ("close_price", "pClosing", "pc"))
        if last is None or close is None:
            missing += 1
            continue

        try:
            last_f = float(last)
            close_f = float(close)
        except (TypeError, ValueError):
            missing += 1
            continue
        if not math.isfinite(last_f) or not math.isfinite(close_f) or close_f == 0:
            missing += 1
            continue

        out.at[idx, "underlying_last_price"] = last_f
        out.at[idx, "underlying_close_price"] = close_f
        out.at[idx, "underlying_context_status"] = "EXACT_UNDERLYING_ID"
        out.at[idx, "underlying_source_ref"] = record.get("source_refs") or {
            "instrument_id": str(underlying_id),
            "source": record.get("source", "TSETMC"),
            "endpoint": record.get("endpoint"),
            "retrieved_at": record.get("retrieved_at"),
            "snapshot_sha256": record.get("snapshot_sha256"),
        }
        exact += 1

    metadata = {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "identity_key": "underlying_id",
        "identity_inference": "DISABLED",
        "exact_attached": exact,
        "ambiguous": ambiguous,
        "insufficient_data": missing,
    }
    return out, metadata
