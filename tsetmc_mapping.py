#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-preserving TSETMC <-> OptionSchool24 mapping boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd


EXACT = "EXACT_INSTRUMENT_ID"
SYMBOL_ONLY = "SYMBOL_ONLY_CANDIDATE"
AMBIGUOUS = "AMBIGUOUS"
NO_MATCH = "NO_MATCH"


@dataclass(frozen=True)
class MappingResult:
    status: str
    option_row_index: Any
    instrument_id: str | None
    candidates: tuple[str, ...]
    reason: str


def _clean(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def _id_column(df: pd.DataFrame) -> str | None:
    aliases = ("insCode", "InsCode", "instrument_id", "InstrumentID", "کد نماد", "کد معاملاتی")
    for alias in aliases:
        if alias in df.columns:
            return alias
    return None


def _symbol_column(df: pd.DataFrame) -> str | None:
    aliases = ("نماد", "symbol", "Symbol", "lVal18AFC")
    for alias in aliases:
        if alias in df.columns:
            return alias
    return None


def map_option_rows(
    option_df: pd.DataFrame,
    tsetmc_records: Iterable[dict[str, Any]],
) -> list[MappingResult]:
    """Return explicit mapping states; never promote a symbol-only match to exact."""
    if not isinstance(option_df, pd.DataFrame):
        raise TypeError("option_df must be a pandas DataFrame")

    option_id_col = _id_column(option_df)
    option_symbol_col = _symbol_column(option_df)

    records = []
    for record in tsetmc_records:
        ins_id = _clean(record.get("instrument_id") or record.get("insCode"))
        symbol = _clean(record.get("symbol") or record.get("lVal18AFC"))
        if ins_id:
            records.append({
                "instrument_id": ins_id,
                "symbol": symbol,
                "contract_type": _clean(record.get("contract_type")),
                "underlying_id": _clean(record.get("underlying_id")),
                "underlying_symbol": _clean(record.get("underlying_symbol") or record.get("underlyingSymbol") or record.get("lval30_UA")),
                "strike": _clean(record.get("strike")),
                "expiry": _clean(record.get("expiry") or record.get("end_date")),
            })

    by_id: dict[str, list[dict[str, str | None]]] = {}
    by_symbol: dict[str, list[dict[str, str | None]]] = {}
    for record in records:
        by_id.setdefault(record["instrument_id"], []).append(record)
        if record["symbol"]:
            by_symbol.setdefault(record["symbol"], []).append(record)

    results: list[MappingResult] = []

    for idx, row in option_df.iterrows():
        option_id = _clean(row.get(option_id_col)) if option_id_col else None
        symbol = _clean(row.get(option_symbol_col)) if option_symbol_col else None

        if option_id:
            candidates = by_id.get(option_id, [])
            ids = tuple(sorted({r["instrument_id"] for r in candidates}))
            if len(candidates) == 1:
                results.append(MappingResult(
                    EXACT, idx, option_id, ids,
                    "explicit instrument identifier matched exactly",
                ))
                continue
            if len(candidates) > 1:
                results.append(MappingResult(
                    AMBIGUOUS, idx, None, ids,
                    "instrument identifier maps to multiple source records",
                ))
                continue

        if symbol:
            candidates = by_symbol.get(symbol, [])
            ids = tuple(sorted({r["instrument_id"] for r in candidates}))
            if len(candidates) == 1:
                results.append(MappingResult(
                    SYMBOL_ONLY, idx, None, ids,
                    "symbol match exists but no explicit option-side instrument identifier was verified",
                ))
            elif len(candidates) > 1:
                results.append(MappingResult(
                    AMBIGUOUS, idx, None, ids,
                    "symbol maps to multiple TSETMC instruments",
                ))
            else:
                results.append(MappingResult(
                    NO_MATCH, idx, None, (),
                    "no explicit identifier or symbol match",
                ))
        else:
            results.append(MappingResult(
                NO_MATCH, idx, None, (),
                "OptionSchool24 row has no usable explicit mapping key",
            ))

    return results


def exact_only(results: Iterable[MappingResult]) -> list[MappingResult]:
    """Promotion gate for the canonical merged snapshot."""
    return [r for r in results if r.status == EXACT]
