#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical multi-source snapshot builder for OptimusAI V4.1."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Iterable
import pandas as pd
from tsetmc_mapping import EXACT, map_option_rows

CANONICAL_COLUMNS = (
    "instrument_id","symbol","underlying_id","underlying_symbol","contract_type",
    "strike","expiry","market_timestamp","last_price","close_price","volume",
    "trade_value","trade_count","best_bid","best_ask","order_book_depth",
    "open_interest","iv","hv","delta","gamma","theta","vega","rho",
    "breakeven","black_scholes","client_type_flow","source_refs","snapshot_id",
    "mapping_status","underlying_source_status","underlying_quote_status",
)

def _clean(value: Any) -> Any:
    if value is None: return None
    try:
        if pd.isna(value): return None
    except (TypeError, ValueError): pass
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value

def _col(df: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    for name in aliases:
        if name in df.columns: return name
    return None

def _row_value(row: pd.Series, aliases: tuple[str, ...]) -> Any:
    col = _col(row.to_frame().T, aliases)
    return _clean(row[col]) if col else None

def _record_value(record: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for name in aliases:
        if name in record:
            value = _clean(record[name])
            if value is not None: return value
    return None

def _snapshot_hash(records: list[dict[str, Any]]) -> str:
    raw = json.dumps(records, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def build_canonical_snapshot(option_df: pd.DataFrame,
                             tsetmc_records: Iterable[dict[str, Any]],
                             *, source_option_file: str | Path | None = None):
    if not isinstance(option_df, pd.DataFrame):
        raise TypeError("option_df must be a pandas DataFrame")
    t_records = [dict(r) for r in tsetmc_records]
    mapping = map_option_rows(option_df, t_records)
    by_id = {}
    for r in t_records:
        ins_id = _record_value(r, ("instrument_id","insCode"))
        if ins_id: by_id[ins_id] = r

    exact = [m for m in mapping if m.status == EXACT]
    option_id_col = _col(option_df, ("insCode","InsCode","instrument_id","InstrumentID","کد نماد","کد معاملاتی"))
    rows = []

    for m in exact:
        if option_id_col is None or m.instrument_id not in by_id: continue
        option_row = option_df.loc[m.option_row_index]
        t = by_id[m.instrument_id]
        row = {
            "instrument_id": m.instrument_id,
            "symbol": _row_value(option_row, ("نماد","symbol","Symbol")) or _record_value(t, ("symbol","lVal18AFC")),
            "underlying_id": _record_value(t, ("underlying_id","underlyingId")),
            "underlying_symbol": _record_value(t, ("underlying_symbol","underlyingSymbol")),
            "contract_type": _record_value(t, ("contract_type","contractType")),
            "strike": _row_value(option_row, ("قیمت اعمال","strike","Strike")) or _record_value(t, ("strike",)),
            "expiry": _row_value(option_row, ("تاریخ سررسید","expiry","Expiry")) or _record_value(t, ("expiry",)),
            "market_timestamp": _record_value(t, ("market_timestamp","timestamp","marketTimestamp")),
            "last_price": _record_value(t, ("last_price","pDrCotVal","pl")) or _row_value(option_row, ("آخرین قیمت","آخرین","Last")),
            "close_price": _record_value(t, ("close_price","pClosing","pc")) or _row_value(option_row, ("قیمت پایانی","پایانی","Close")),
            "volume": _record_value(t, ("volume","qTotTran5J","zTotTran")) or _row_value(option_row, ("حجم معاملات","حجم کل","Volume")),
            "trade_value": _record_value(t, ("trade_value","qTotCap")) or _row_value(option_row, ("ارزش معاملات","ارزش کل","TradeValue")),
            "trade_count": _record_value(t, ("trade_count","zTotTran")),
            "best_bid": _record_value(t, ("best_bid","bid")),
            "best_ask": _record_value(t, ("best_ask","ask")),
            "order_book_depth": _record_value(t, ("order_book_depth","depth")),
            "open_interest": _row_value(option_row, ("موقعیت باز","Open Interest","OI")),
            "iv": _row_value(option_row, ("نوسان ضمنی","IV")),
            "hv": _row_value(option_row, ("نوسان تاریخی","HV")),
            "delta": _row_value(option_row, ("دلتا","Delta")),
            "gamma": _row_value(option_row, ("گاما","Gamma")),
            "theta": _row_value(option_row, ("تتا","Theta")),
            "vega": _row_value(option_row, ("وگا","Vega")),
            "rho": _row_value(option_row, ("رو","Rho")),
            "breakeven": _row_value(option_row, ("سر به سر","سر‌به‌سر","Breakeven")),
            "black_scholes": _row_value(option_row, ("بلک شولز","Black-Scholes","BlackScholes")),
            "client_type_flow": _record_value(t, ("client_type_flow","clientType")),
            "source_refs": {"tsetmc": _record_value(t, ("source_refs",)) or t,
                            "optionschool_row_index": m.option_row_index},
            "mapping_status": m.status,
            "underlying_source_status": ("EXPLICIT_ID_AVAILABLE" if _record_value(t, ("underlying_id","underlyingId")) else "INSUFFICIENT_DATA"),
            "underlying_quote_status": _record_value(t, ("underlying_quote_status", "underlyingContextStatus")) or "NOT_ATTACHED",
        }
        rows.append(row)

    normalized = [{k: _clean(v) for k,v in row.items() if k != "snapshot_id"} for row in rows]
    snapshot_id = _snapshot_hash(normalized)
    for row in rows: row["snapshot_id"] = snapshot_id
    canonical = pd.DataFrame(rows, columns=CANONICAL_COLUMNS)
    metadata = {
        "status":"SUCCESS","snapshot_id":snapshot_id,
        "source_option_file": str(source_option_file) if source_option_file is not None else None,
        "option_rows":int(len(option_df)),"tsetmc_records":int(len(t_records)),
        "exact_promoted":int(sum(m.status == EXACT for m in mapping)),
        "symbol_only_candidates":int(sum(m.status == "SYMBOL_ONLY_CANDIDATE" for m in mapping)),
        "ambiguous":int(sum(m.status == "AMBIGUOUS" for m in mapping)),
        "no_match":int(sum(m.status == "NO_MATCH" for m in mapping)),
        "canonical_rows":int(len(canonical)),
        "identity_inference":"DISABLED",
    }
    return canonical, metadata
