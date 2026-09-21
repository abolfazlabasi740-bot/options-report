#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only historical pattern detection for OptimusAI V4.1."""

from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

ENGINE_VERSION = "HIST-PATTERN-SHADOW-1.0"

DIRECTIONS = {"UP", "DOWN", "UNCHANGED", "INSUFFICIENT_DATA"}


def _num(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        value = float(value)
        return value if pd.notna(value) else None
    except (TypeError, ValueError):
        return None


def _records(snapshot: dict[str, Any], identity_key: str) -> dict[str, dict[str, Any]]:
    out = {}
    for record in snapshot.get("records", []):
        value = record.get(identity_key)
        if value in (None, ""):
            continue
        out[str(value)] = record
    return out


def _direction(old: Any, new: Any) -> str:
    old_num, new_num = _num(old), _num(new)
    if old_num is None or new_num is None:
        return "INSUFFICIENT_DATA"
    if new_num > old_num:
        return "UP"
    if new_num < old_num:
        return "DOWN"
    return "UNCHANGED"


def _sequence(values: list[str]) -> str:
    observed = [x for x in values if x != "INSUFFICIENT_DATA"]
    if not observed:
        return "INSUFFICIENT_DATA"
    if all(x == "UNCHANGED" for x in observed):
        return "STABLE"
    if len(observed) == len(values) and len(set(observed)) == 1:
        return "CONSISTENT_" + observed[0]
    if observed[-1] in {"UP", "DOWN"}:
        return "MIXED_ENDING_" + observed[-1]
    return "MIXED"


def _pair_pattern(price: list[str], volume: list[str]) -> str:
    pairs = [(p, v) for p, v in zip(price, volume)
             if p in {"UP", "DOWN", "UNCHANGED"} and v in {"UP", "DOWN", "UNCHANGED"}]
    if not pairs:
        return "INSUFFICIENT_DATA"
    if all(p == v and p in {"UP", "DOWN"} for p, v in pairs):
        return "CONCORDANT"
    if all((p == "UP" and v == "DOWN") or (p == "DOWN" and v == "UP") for p, v in pairs):
        return "DIVERGENT"
    if any(p == "UNCHANGED" or v == "UNCHANGED" for p, v in pairs):
        return "MIXED_WITH_STABLE"
    return "MIXED"


def build_historical_patterns(
    history: Iterable[dict[str, Any]],
    *,
    identity_key: str = "نماد",
    window: int = 3,
    fields: tuple[str, ...] = (
        "FinalScore",
        "BlockScore_Liquidity",
        "last_price",
        "volume",
        "trade_value",
    ),
) -> dict[str, Any]:
    snapshots = list(history)
    if isinstance(window, bool) or not isinstance(window, int) or window < 1:
        raise ValueError("window must be a positive integer")
    if len(snapshots) < 2:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "engine_version": ENGINE_VERSION,
            "identity_key": identity_key,
            "window": window,
            "patterns": [],
            "summary": {},
        }

    use = snapshots[-(window + 1):]
    current_id = use[-1].get("snapshot_id")
    previous_id = use[-2].get("snapshot_id")

    identities = set()
    indexed = [_records(s, identity_key) for s in use]
    for table in indexed:
        identities.update(table.keys())

    patterns = []
    for identity in sorted(identities):
        series = {}
        for field in fields:
            values = []
            for idx in range(1, len(indexed)):
                old = indexed[idx - 1].get(identity, {}).get(field)
                new = indexed[idx].get(identity, {}).get(field)
                values.append(_direction(old, new))
            series[field] = values

        for field, directions in series.items():
            if len(directions) < window:
                continue
            state = _sequence(directions)
            if state == "INSUFFICIENT_DATA":
                continue
            if state == "STABLE":
                pattern_type = f"{field.upper()}_STABLE_SEQUENCE"
            elif state.startswith("CONSISTENT_"):
                pattern_type = f"{field.upper()}_{state.replace('CONSISTENT_', '')}_SEQUENCE"
            else:
                pattern_type = f"{field.upper()}_{state}_SEQUENCE"
            patterns.append({
                "snapshot_id": current_id,
                "previous_snapshot_id": previous_id,
                "engine_version": ENGINE_VERSION,
                "identity": identity,
                "type": pattern_type,
                "field": field,
                "directions": directions,
                "classification": "DESCRIPTIVE_SEQUENCE",
            })

        price = series.get("last_price")
        volume = series.get("volume")
        if price and volume and len(price) >= window and len(volume) >= window:
            pair = _pair_pattern(price[-window:], volume[-window:])
            if pair != "INSUFFICIENT_DATA":
                patterns.append({
                    "snapshot_id": current_id,
                    "previous_snapshot_id": previous_id,
                    "engine_version": ENGINE_VERSION,
                    "identity": identity,
                    "type": f"PRICE_VOLUME_{pair}",
                    "fields": ["last_price", "volume"],
                    "price_directions": price[-window:],
                    "volume_directions": volume[-window:],
                    "classification": "DESCRIPTIVE_RELATIONSHIP",
                })

        score = series.get("FinalScore")
        if score and price and len(score) >= window and len(price) >= window:
            score_tail, price_tail = score[-window:], price[-window:]
            if all(x in {"UP", "DOWN"} for x in score_tail + price_tail):
                if all(a == b for a, b in zip(score_tail, price_tail)):
                    relation = "ALIGNED"
                else:
                    relation = "DIVERGENT"
                patterns.append({
                    "snapshot_id": current_id,
                    "previous_snapshot_id": previous_id,
                    "engine_version": ENGINE_VERSION,
                    "identity": identity,
                    "type": f"SCORE_PRICE_{relation}",
                    "fields": ["FinalScore", "last_price"],
                    "score_directions": score_tail,
                    "price_directions": price_tail,
                    "classification": "DESCRIPTIVE_RELATIONSHIP",
                })

    summary = {}
    for item in patterns:
        summary[item["type"]] = summary.get(item["type"], 0) + 1

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "identity_key": identity_key,
        "window": window,
        "snapshot_count": len(use),
        "current_snapshot_id": current_id,
        "previous_snapshot_id": previous_id,
        "pattern_count": len(patterns),
        "summary": summary,
        "patterns": patterns,
    }
