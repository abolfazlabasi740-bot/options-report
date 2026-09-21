#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic replay verification for OptimusAI V4.1 Shadow layers."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

import pandas as pd

from opportunity_engine import run_shadow

ENGINE_VERSION = "REPLAY-SHADOW-1.0"


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _stable(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    if isinstance(value, tuple):
        return [_stable(v) for v in value]
    if isinstance(value, float):
        return None if pd.isna(value) else value
    return value


def stable_shadow_payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(result)
    payload.pop("generated_at", None)
    return _stable(payload)


def fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        _stable(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_shadow_replay(
    scored: pd.DataFrame,
    snapshot_id: str,
    *,
    historical_previous: dict[str, Any] | None = None,
    historical_current: dict[str, Any] | None = None,
    historical_sequence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    first = run_shadow(
        scored.copy(deep=True),
        snapshot_id,
        memory_path=None,
        historical_previous=historical_previous,
        historical_current=historical_current,
        historical_sequence=historical_sequence,
    )
    second = run_shadow(
        scored.copy(deep=True),
        snapshot_id,
        memory_path=None,
        historical_previous=historical_previous,
        historical_current=historical_current,
        historical_sequence=historical_sequence,
    )

    first_payload = stable_shadow_payload(first)
    second_payload = stable_shadow_payload(second)
    first_hash = fingerprint(first_payload)
    second_hash = fingerprint(second_payload)

    return {
        "status": "REPLAY_MATCH" if first_hash == second_hash else "REPLAY_MISMATCH",
        "engine_version": ENGINE_VERSION,
        "snapshot_id": snapshot_id,
        "first_hash": first_hash,
        "second_hash": second_hash,
        "deterministic": first_hash == second_hash,
    }


def save_replay_evidence(path: str, result: dict[str, Any]) -> str:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
    return path
