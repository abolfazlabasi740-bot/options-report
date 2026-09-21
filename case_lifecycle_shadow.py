#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auditable Case Lifecycle Shadow for OptimusAI V4.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

ENGINE_VERSION = "CASE-LIFECYCLE-SHADOW-1.0"
ACTIVE_STATES = {"NEW", "PERSISTENT", "STRENGTHENING", "WEAKENING", "RECURRING"}
ALL_STATES = ACTIVE_STATES | {"RESOLVED"}


def case_key(case: dict[str, Any]) -> str:
    return f"{case.get('type')}::{case.get('symbol')}"


def strength(status: str | None) -> int:
    return {"REJECTED": 0, "INSUFFICIENT_DATA": 1, "WATCH": 2, "CONFIRMED": 3}.get(
        status or "", 1
    )


def load_events(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    events = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def append_events(
    path: str | Path,
    snapshot_id: str,
    cases: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    prior_events = load_events(p)

    latest: dict[str, dict[str, Any]] = {}
    for event in prior_events:
        key = event.get("case_key")
        if key:
            latest[key] = event

    current_cases = list(cases)
    current_keys = set()
    events = []

    for case in current_cases:
        key = case_key(case)
        current_keys.add(key)
        old = latest.get(key)
        current_strength = strength(case.get("status"))

        if old is None:
            state = "NEW"
            first_seen = snapshot_id
            seen_count = 1
            transition = "FIRST_SEEN"
        else:
            first_seen = old.get("first_seen_snapshot") or old.get("snapshot_id")
            seen_count = int(old.get("seen_count", 0)) + 1
            old_strength = int(old.get("strength", 1))
            old_state = old.get("state")
            if old_state == "RESOLVED":
                state = "RECURRING"
                transition = "RECURRED"
            elif current_strength > old_strength:
                state = "STRENGTHENING"
                transition = "STRENGTH_INCREASED"
            elif current_strength < old_strength:
                state = "WEAKENING"
                transition = "STRENGTH_DECREASED"
            else:
                state = "PERSISTENT"
                transition = "PERSISTED"

        events.append({
            "engine_version": ENGINE_VERSION,
            "snapshot_id": snapshot_id,
            "case_key": key,
            "case_id": case.get("case_id"),
            "symbol": case.get("symbol"),
            "type": case.get("type"),
            "status": case.get("status"),
            "strength": current_strength,
            "state": state,
            "transition": transition,
            "first_seen_snapshot": first_seen,
            "seen_count": seen_count,
        })

    for key, old in latest.items():
        if key in current_keys or old.get("state") == "RESOLVED":
            continue
        events.append({
            "engine_version": ENGINE_VERSION,
            "snapshot_id": snapshot_id,
            "case_key": key,
            "case_id": old.get("case_id"),
            "symbol": old.get("symbol"),
            "type": old.get("type"),
            "status": "REJECTED",
            "strength": 0,
            "state": "RESOLVED",
            "transition": "DISAPPEARED_FROM_CURRENT_SNAPSHOT",
            "first_seen_snapshot": old.get("first_seen_snapshot"),
            "seen_count": int(old.get("seen_count", 0)),
        })

    events.sort(key=lambda e: (e["case_key"], e["state"], e.get("case_id") or ""))
    with p.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "snapshot_id": snapshot_id,
        "events_written": len(events),
        "case_count": len(current_cases),
        "resolved_count": sum(e["state"] == "RESOLVED" for e in events),
        "states": sorted({e["state"] for e in events}),
        "file": p.name,
    }


def current_state(path: str | Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for event in load_events(path):
        key = event.get("case_key")
        if key:
            latest[key] = event
    return latest
