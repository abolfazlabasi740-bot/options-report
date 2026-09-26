from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


ENGINE_VERSION = "OBSERVED-OUTCOME-1.0"
SOURCE_OF_TRUTH = "TSETMC"


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _row_timestamp(row: dict[str, Any], snapshot: dict[str, Any]) -> str | None:
    value = row.get("source_market_timestamp")
    if isinstance(value, str) and value.strip():
        return value
    value = snapshot.get("generated_at")
    return value if isinstance(value, str) and value.strip() else None


def _identity_id(row: dict[str, Any]) -> str | None:
    identity = row.get("identity") or {}
    value = identity.get("instrument_id")
    return str(value).strip() if value not in (None, "") else None


def _canonical(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("canonical") or {}


def _observed_row(row: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any] | None:
    instrument_id = _identity_id(row)
    if not instrument_id:
        return None
    canonical = _canonical(row)
    return {
        "instrument_id": instrument_id,
        "symbol": canonical.get("نماد"),
        "contract_type": (row.get("identity") or {}).get("contract_type"),
        "underlying_symbol": (row.get("identity") or {}).get("underlying_symbol"),
        "option_last": _number(canonical.get("آخرین قیمت")),
        "option_close": _number(canonical.get("قیمت پایانی")),
        "underlying_price": _number(canonical.get("قیمت سهم پایه")),
        "strike": _number(canonical.get("قیمت اعمال")),
        "expiry": canonical.get("تاریخ سررسید"),
        "source_market_timestamp": _row_timestamp(row, snapshot),
    }


def _change(entry: float | None, forward: float | None) -> tuple[float | None, float | None]:
    if entry is None or forward is None:
        return None, None
    absolute = forward - entry
    percentage = absolute / abs(entry) if entry != 0 else None
    return absolute, percentage


def _load_archives(root: Path) -> list[dict[str, Any]]:
    paths = sorted((root / "output" / "history" / "tsetmc").glob("*.json"))
    snapshots: list[dict[str, Any]] = []
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
    snapshots.sort(key=lambda x: (_timestamp(x.get("generated_at")) or datetime.min, str(x.get("snapshot_sha256"))))
    return snapshots


def build_observed_outcomes(root: Path) -> dict[str, Any]:
    snapshots = _load_archives(root)
    transitions: list[dict[str, Any]] = []

    for entry_snapshot, forward_snapshot in zip(snapshots, snapshots[1:]):
        entry_rows = {
            observed["instrument_id"]: observed
            for row in entry_snapshot.get("rows", [])
            if (observed := _observed_row(row, entry_snapshot)) is not None
        }
        forward_rows = {
            observed["instrument_id"]: observed
            for row in forward_snapshot.get("rows", [])
            if (observed := _observed_row(row, forward_snapshot)) is not None
        }

        entry_time = _timestamp(entry_snapshot.get("generated_at"))
        forward_time = _timestamp(forward_snapshot.get("generated_at"))
        elapsed_days = (
            (forward_time - entry_time).total_seconds() / 86400.0
            if entry_time is not None and forward_time is not None
            else None
        )

        for instrument_id in sorted(set(entry_rows) & set(forward_rows)):
            entry = entry_rows[instrument_id]
            forward = forward_rows[instrument_id]
            option_change, option_change_pct = _change(entry["option_last"], forward["option_last"])
            underlying_change, underlying_change_pct = _change(
                entry["underlying_price"], forward["underlying_price"]
            )
            transitions.append({
                "instrument_id": instrument_id,
                "symbol": entry["symbol"],
                "contract_type": entry["contract_type"],
                "underlying_symbol": entry["underlying_symbol"],
                "entry_snapshot_sha256": entry_snapshot["snapshot_sha256"],
                "forward_snapshot_sha256": forward_snapshot["snapshot_sha256"],
                "entry_source_market_timestamp": entry["source_market_timestamp"],
                "forward_source_market_timestamp": forward["source_market_timestamp"],
                "entry_last": entry["option_last"],
                "forward_last": forward["option_last"],
                "option_change": option_change,
                "option_change_pct": option_change_pct,
                "entry_underlying_price": entry["underlying_price"],
                "forward_underlying_price": forward["underlying_price"],
                "underlying_change": underlying_change,
                "underlying_change_pct": underlying_change_pct,
                "strike": entry["strike"],
                "expiry": entry["expiry"],
                "elapsed_days": elapsed_days,
                "outcome_type": "OBSERVED_STATE_CHANGE",
                "signal_generation": "FORBIDDEN",
                "labels": "NOT_INFERRED",
                "external_sources": "FORBIDDEN",
            })

    return {
        "status": "PASS",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": SOURCE_OF_TRUTH,
        "snapshot_count": len(snapshots),
        "transition_count": len(transitions),
        "transitions": transitions,
        "rules": {
            "matching": "EXACT_INSTRUMENT_ID_ONLY",
            "outcome_type": "OBSERVED_STATE_CHANGE",
            "signal_generation": "FORBIDDEN",
            "labels": "NOT_INFERRED",
            "transaction_costs": "NOT_ASSUMED",
            "slippage": "NOT_ASSUMED",
            "external_sources": "FORBIDDEN",
        },
    }
