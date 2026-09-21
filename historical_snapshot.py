#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic historical snapshot store and evidence diff for OptimusAI V4.1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

ENGINE_VERSION = "HIST-SNAPSHOT-1.0"


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
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    try:
        if hasattr(value, "item"):
            return _clean(value.item())
    except (TypeError, ValueError):
        pass
    return value


def canonical_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = []
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("snapshot records must be dictionaries")
        cleaned.append({str(k): _clean(v) for k, v in record.items()})
    return sorted(
        cleaned,
        key=lambda r: (
            str(r.get("instrument_id") or r.get("نماد") or r.get("symbol") or ""),
            json.dumps(r, ensure_ascii=False, sort_keys=True, default=str),
        ),
    )


def dataframe_records(df: pd.DataFrame, columns: Iterable[str] | None = None) -> list[dict[str, Any]]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    work = df.copy()
    if columns is not None:
        selected = [c for c in columns if c in work.columns]
        work = work[selected]
    return canonical_records(work.to_dict(orient="records"))


def records_hash(records: Iterable[dict[str, Any]]) -> str:
    normalized = canonical_records(records)
    raw = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_snapshot(
    snapshot_id: str,
    records: Iterable[dict[str, Any]],
    *,
    source: str | None = None,
    retrieved_at: str | None = None,
    identity_mode: str = "UNSPECIFIED",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not str(snapshot_id).strip():
        raise ValueError("snapshot_id is required")
    normalized = canonical_records(records)
    return {
        "engine_version": ENGINE_VERSION,
        "snapshot_id": str(snapshot_id),
        "source": source,
        "retrieved_at": retrieved_at,
        "identity_mode": identity_mode,
        "record_count": len(normalized),
        "records_hash": records_hash(normalized),
        "metadata": metadata or {},
        "records": normalized,
    }


def append_snapshot(path: str | Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(snapshot, dict) or not snapshot.get("snapshot_id"):
        raise ValueError("invalid snapshot")

    existing: list[dict[str, Any]] = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.append(json.loads(line))

    for item in existing:
        if item.get("snapshot_id") == snapshot.get("snapshot_id"):
            if item.get("records_hash") != snapshot.get("records_hash"):
                raise ValueError("same snapshot_id has different records_hash")
            previous = existing[-2] if len(existing) > 1 else None
            return {"status": "DUPLICATE", "snapshot": item, "previous": previous}

    with p.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")

    previous = existing[-1] if existing else None
    return {"status": "APPENDED", "snapshot": snapshot, "previous": previous}


def load_history(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _identity(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    if value in (None, ""):
        return None
    return str(value).strip()


def _numeric(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        value = float(value)
        return value if pd.notna(value) else None
    except (TypeError, ValueError):
        return None


def field_delta(old: Any, new: Any) -> dict[str, Any]:
    old_num, new_num = _numeric(old), _numeric(new)
    item = {"old": _clean(old), "new": _clean(new)}

    if old_num is not None and new_num is not None:
        item["delta"] = new_num - old_num
        item["direction"] = (
            "UP" if new_num > old_num else "DOWN" if new_num < old_num else "UNCHANGED"
        )
        if old_num != 0:
            item["percent_change"] = (new_num - old_num) / abs(old_num) * 100.0
        else:
            item["percent_change"] = None
    else:
        item["direction"] = "CHANGED" if old != new else "UNCHANGED"

    return item


def diff_snapshots(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    *,
    identity_key: str = "instrument_id",
) -> dict[str, Any]:
    if not current or not current.get("snapshot_id"):
        raise ValueError("current snapshot is required")

    old_records = {
        str(_identity(r, identity_key)): r
        for r in (previous or {}).get("records", [])
        if _identity(r, identity_key) is not None
    }
    new_records = {
        str(_identity(r, identity_key)): r
        for r in current.get("records", [])
        if _identity(r, identity_key) is not None
    }

    changes = []
    for key in sorted(set(old_records) | set(new_records)):
        old, new = old_records.get(key), new_records.get(key)
        if old is None:
            changes.append({"identity": key, "status": "ADDED"})
            continue
        if new is None:
            changes.append({"identity": key, "status": "REMOVED"})
            continue

        changed = {}
        for field in sorted(set(old) | set(new)):
            if field == "snapshot_id":
                continue
            if _clean(old.get(field)) != _clean(new.get(field)):
                changed[field] = field_delta(old.get(field), new.get(field))

        changes.append({
            "identity": key,
            "status": "CHANGED" if changed else "UNCHANGED",
            "fields": changed,
        })

    summary = {
        "added": sum(x["status"] == "ADDED" for x in changes),
        "removed": sum(x["status"] == "REMOVED" for x in changes),
        "changed": sum(x["status"] == "CHANGED" for x in changes),
        "unchanged": sum(x["status"] == "UNCHANGED" for x in changes),
    }
    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "previous_snapshot_id": previous.get("snapshot_id") if previous else None,
        "current_snapshot_id": current.get("snapshot_id"),
        "identity_key": identity_key,
        "summary": summary,
        "changes": changes,
    }


def case_historical_context(
    cases: Iterable[dict[str, Any]],
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    *,
    identity_key: str = "نماد",
) -> dict[str, Any]:
    old_records = {
        str(_identity(r, identity_key)): r
        for r in (previous or {}).get("records", [])
        if _identity(r, identity_key) is not None
    }
    new_records = {
        str(_identity(r, identity_key)): r
        for r in current.get("records", [])
        if _identity(r, identity_key) is not None
    }

    contexts = []
    for case in cases:
        key = str(case.get("symbol") or case.get("instrument_id") or "").strip()
        old, new = old_records.get(key), new_records.get(key)

        if new is None:
            state = "NO_CURRENT_RECORD"
        elif old is None:
            state = "NEW_IN_CURRENT_SNAPSHOT"
        else:
            state = "PERSISTENT_IN_CURRENT_SEQUENCE"

        score = (
            field_delta(old.get("FinalScore"), new.get("FinalScore"))
            if old is not None and new is not None
            else None
        )
        confidence = (
            field_delta(old.get("DataConfidence"), new.get("DataConfidence"))
            if old is not None and new is not None
            else None
        )
        days = (
            field_delta(old.get("RemainingDays"), new.get("RemainingDays"))
            if old is not None and new is not None
            else None
        )

        contexts.append({
            "case_id": case.get("case_id"),
            "symbol": case.get("symbol"),
            "historical_state": state,
            "previous_snapshot_id": previous.get("snapshot_id") if previous else None,
            "current_snapshot_id": current.get("snapshot_id"),
            "final_score_change": score,
            "data_confidence_change": confidence,
            "remaining_days_change": days,
        })

    return {
        "engine_version": ENGINE_VERSION,
        "status": "SUCCESS",
        "previous_snapshot_id": previous.get("snapshot_id") if previous else None,
        "current_snapshot_id": current.get("snapshot_id"),
        "cases": contexts,
    }
