#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional Shadow integration for explicit TSETMC option/underlying evidence."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

from tsetmc_evidence_collector import collect_underlying_evidence, ENGINE_VERSION as COLLECTOR_VERSION

ENGINE_VERSION = "TSETMC-SHADOW-INTEGRATION-1.0"


def _find_option_id_column(df: pd.DataFrame) -> str | None:
    aliases = ("insCode", "InsCode", "instrument_id", "InstrumentID", "کد نماد", "کد معاملاتی")
    for name in aliases:
        if name in df.columns:
            return name
    return None


def enrich_shadow_with_tsetmc(
    shadow: pd.DataFrame,
    source_df: pd.DataFrame,
    *,
    enabled: bool | None = None,
    adapter: Any = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Attach exact TSETMC underlying evidence to Shadow rows only.

    Disabled by default so the existing production report remains network-independent.
    Activation requires TSETMC_EVIDENCE_ENABLED=1 or enabled=True and an explicit
    option instrument identifier in the source workbook.
    """
    if enabled is None:
        enabled = os.getenv("TSETMC_EVIDENCE_ENABLED", "").strip().lower() in {"1", "true", "yes"}

    out = shadow.copy()
    out["underlying_last_price"] = pd.NA
    out["underlying_close_price"] = pd.NA
    out["underlying_context_status"] = "INSUFFICIENT_DATA"
    out["underlying_source_ref"] = pd.NA

    meta = {
        "status": "DISABLED" if not enabled else "INSUFFICIENT_DATA",
        "engine_version": ENGINE_VERSION,
        "collector_engine_version": COLLECTOR_VERSION,
        "enabled": bool(enabled),
        "option_identity_key": None,
        "records": [],
        "summary": {},
        "production_scoring_changed": False,
    }
    if not enabled:
        return out, meta

    id_col = _find_option_id_column(source_df)
    if id_col is None:
        meta["status"] = "NO_EXPLICIT_OPTION_ID"
        return out, meta

    meta["option_identity_key"] = id_col
    option_ids = [v for v in source_df[id_col].tolist() if v is not None and not pd.isna(v)]
    evidence = collect_underlying_evidence(option_ids, adapter=adapter)
    by_option = {str(r["option_instrument_id"]): r for r in evidence["records"]}

    for idx in out.index:
        raw_id = source_df.at[idx, id_col] if idx in source_df.index else None
        if raw_id is None or pd.isna(raw_id):
            continue
        record = by_option.get(str(raw_id).strip())
        if not record:
            continue
        out.at[idx, "underlying_context_status"] = record.get("status", "INSUFFICIENT_DATA")
        out.at[idx, "underlying_source_ref"] = {
            "option_instrument_id": record.get("option_instrument_id"),
            "underlying_id": record.get("underlying_id"),
            "option_evidence": record.get("option_evidence"),
            "underlying_quote_evidence": record.get("underlying_quote_evidence"),
            "evidence_sha256": record.get("evidence_sha256"),
        }
        if "underlying_last_price" in record:
            out.at[idx, "underlying_last_price"] = record["underlying_last_price"]
        if "underlying_close_price" in record:
            out.at[idx, "underlying_close_price"] = record["underlying_close_price"]

    meta["status"] = "SUCCESS"
    meta["records"] = evidence["records"]
    meta["summary"] = evidence["summary"]
    return out, meta
