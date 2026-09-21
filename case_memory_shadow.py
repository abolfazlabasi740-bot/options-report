#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shadow Case Memory: persistence/recurrence only.

Historical cases never alter current scoring. They are used to classify whether
the same analytical condition is new, persistent, strengthening, weakening,
resolved, or recurring.
"""

from pathlib import Path
import json

MEMORY_VERSION = "CASE-MEMORY-SHADOW-1.0"
STATES = {"NEW", "PERSISTENT", "STRENGTHENING", "WEAKENING", "RESOLVED", "RECURRING"}


def _case_key(case):
    return f"{case.get('type')}::{case.get('symbol')}"


def _strength(case):
    status = case.get("status")
    if status == "CONFIRMED":
        return 3
    if status == "WATCH":
        return 2
    if status == "REJECTED":
        return 0
    return 1


def load_memory(path):
    p = Path(path)
    if not p.exists():
        return {"memory_version": MEMORY_VERSION, "cases": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), dict):
        raise ValueError("invalid case memory schema")
    return data


def update_memory(path, current_cases):
    previous = load_memory(path)
    previous_cases = previous.get("cases", {})
    current_keys = set()

    output = {
        "memory_version": MEMORY_VERSION,
        "cases": dict(previous_cases),
    }

    for case in current_cases:
        key = _case_key(case)
        current_keys.add(key)
        old = previous_cases.get(key)
        now_strength = _strength(case)

        if old is None:
            state = "NEW"
            history = []
        else:
            old_strength = int(old.get("last_strength", 1))
            if now_strength > old_strength:
                state = "STRENGTHENING"
            elif now_strength < old_strength:
                state = "WEAKENING"
            elif old.get("last_snapshot_id") == case.get("snapshot_id"):
                state = "PERSISTENT"
            else:
                state = "RECURRING" if old.get("state") == "RESOLVED" else "PERSISTENT"
            history = list(old.get("history", []))

        history.append({
            "snapshot_id": case.get("snapshot_id"),
            "status": case.get("status"),
            "strength": now_strength,
        })
        history = history[-20:]

        output["cases"][key] = {
            "key": key,
            "symbol": case.get("symbol"),
            "type": case.get("type"),
            "state": state,
            "last_snapshot_id": case.get("snapshot_id"),
            "last_status": case.get("status"),
            "last_strength": now_strength,
            "history": history,
        }

    for key, old in list(previous_cases.items()):
        if key not in current_keys:
            old = dict(old)
            old["state"] = "RESOLVED"
            output["cases"][key] = old

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return output
