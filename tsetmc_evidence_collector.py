#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-preserving TSETMC option -> underlying collector for OptimusAI V4.1."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Iterable

from tsetmc_adapter import TSETMCAdapter, TSETMCError

ENGINE_VERSION = "TSETMC-EVIDENCE-COLLECTOR-1.0"


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _finite_number(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _evidence_hash(record: dict[str, Any]) -> str:
    raw = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def collect_underlying_evidence(
    option_instrument_ids: Iterable[str],
    *,
    adapter: TSETMCAdapter | None = None,
) -> dict[str, Any]:
    """Collect explicit option identity and exact underlying quote evidence.

    Identity rule is strict: the option response must explicitly provide
    underlying_id/underlyingId. Symbol search and symbol-prefix inference are
    never used. Source failures are retained as evidence, not converted to
    missing numeric values.
    """
    if adapter is None:
        adapter = TSETMCAdapter()

    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    for raw_id in option_instrument_ids:
        option_id = _clean(raw_id)
        if option_id is None or str(option_id) in seen:
            continue
        option_id = str(option_id)
        seen.add(option_id)

        base_record: dict[str, Any] = {
            "option_instrument_id": option_id,
            "underlying_id": None,
            "status": "INSUFFICIENT_DATA",
            "identity_inference": "DISABLED",
        }

        try:
            option = adapter.canonical_instrument(option_id)
            underlying_id = _clean(option.get("underlying_id"))
            base_record["option_evidence"] = option.get("source_refs")
            base_record["underlying_id"] = str(underlying_id) if underlying_id else None

            if underlying_id is None:
                base_record["status"] = "NO_EXPLICIT_UNDERLYING_ID"
                base_record["evidence_sha256"] = _evidence_hash(base_record)
                records.append(base_record)
                continue

            quote = adapter.quote(str(underlying_id))
            data = quote.get("data") or {}
            last = _finite_number(data.get("pDrCotVal", data.get("pl")))
            close = _finite_number(data.get("pClosing", data.get("pc")))

            base_record["underlying_quote_evidence"] = quote
            if last is None or close is None or close == 0:
                base_record["status"] = "UNDERLYING_QUOTE_INSUFFICIENT"
            else:
                base_record["underlying_last_price"] = last
                base_record["underlying_close_price"] = close
                base_record["status"] = "EXACT_UNDERLYING_QUOTE"

        except (TSETMCError, ValueError, TypeError) as exc:
            base_record["status"] = "SOURCE_UNAVAILABLE"
            base_record["error_type"] = type(exc).__name__
            base_record["error"] = str(exc)

        base_record["evidence_sha256"] = _evidence_hash(base_record)
        records.append(base_record)

    counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("status"))
        counts[status] = counts.get(status, 0) + 1

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "identity_key": "underlying_id",
        "identity_inference": "DISABLED",
        "records": records,
        "summary": {
            "requested": len(records),
            "exact_underlying_quote": counts.get("EXACT_UNDERLYING_QUOTE", 0),
            "no_explicit_underlying_id": counts.get("NO_EXPLICIT_UNDERLYING_ID", 0),
            "underlying_quote_insufficient": counts.get("UNDERLYING_QUOTE_INSUFFICIENT", 0),
            "source_unavailable": counts.get("SOURCE_UNAVAILABLE", 0),
        },
    }
