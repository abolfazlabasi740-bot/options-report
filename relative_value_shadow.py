#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shadow relative-value evidence for explicit option chains.

This layer is evidence-only. It never infers contract type and never declares
call/put parity mispricing without the required economic inputs.
"""

import math
import pandas as pd

ENGINE_VERSION = "RELATIVE-VALUE-SHADOW-1.0"

def _num(row, key):
    try:
        v = row.get(key)
        if v is None or pd.isna(v):
            return None
        v = float(v)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None

def _e(name, value, source):
    return {"name": name, "value": value, "source": source}

def _pair(call_row, put_row, strike):
    fields = [
        ("last_price", "آخرین قیمت"),
        ("breakeven_distance_pct", "BreakevenDistancePct"),
        ("implied_volatility", "نوسان ضمنی"),
        ("liquidity_block", "BlockScore_Liquidity"),
        ("data_confidence", "DataConfidence"),
    ]
    evidence = [_e("strike", strike, "chain_identity_shadow")]
    available = 0
    for name, col in fields:
        c, p = _num(call_row, col), _num(put_row, col)
        if c is not None and p is not None:
            evidence.append(_e("call_"+name, c, col))
            evidence.append(_e("put_"+name, p, col))
            evidence.append(_e("absolute_difference_"+name, abs(c-p), col))
            available += 1
        else:
            evidence.append(_e("call_"+name, c, col))
            evidence.append(_e("put_"+name, p, col))
    return evidence, available

def analyze_chain(scored, chain_result, snapshot_id):
    if chain_result.get("status") != "SUCCESS":
        return []
    rows = {
        str(r.get("symbol", "")).strip(): r
        for r in chain_result.get("rows", [])
        if r.get("status") == "VALID"
    }
    by_symbol = {
        str(r.get("نماد", "")).strip(): r
        for _, r in scored.iterrows()
    }
    cases = []
    for key, chain in chain_result.get("chains", {}).items():
        if chain.get("duplicate_identities"):
            continue
        calls, puts = {}, {}
        for symbol in chain.get("members", []):
            ident = rows.get(symbol)
            row = by_symbol.get(symbol)
            if not ident or row is None:
                continue
            if ident.get("contract_type") == "CALL":
                calls[ident["strike"]] = row
            elif ident.get("contract_type") == "PUT":
                puts[ident["strike"]] = row
        for strike in sorted(set(calls) & set(puts)):
            evidence, available = _pair(calls[strike], puts[strike], strike)
            if available < 2:
                status = "INSUFFICIENT_DATA"
                reason = "Common CALL/PUT strike exists, but fewer than two paired observable fields are available."
            else:
                status = "WATCH"
                reason = (
                    "Explicit CALL/PUT pair has observable relative differences. "
                    "Economic parity mispricing is not asserted because rate/dividend inputs "
                    "and full contract specifications have not been validated."
                )
            cases.append({
                "snapshot_id": str(snapshot_id),
                "engine_version": ENGINE_VERSION,
                "case_id": f"{snapshot_id}:RELATIVE-PAIR:{key}:{strike:g}",
                "type": "RELATIVE_PAIR_STRUCTURE",
                "status": status,
                "symbol": key,
                "final_score": None,
                "confidence": None,
                "reason": reason,
                "evidence": evidence,
            })
    return cases
