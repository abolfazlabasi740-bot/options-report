#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V4.1 Shadow Chain Identity / Clustering.

Only explicit source fields are used. Contract type or underlying is never
guessed from an option symbol. A chain is analytical only when its identity
components are explicit and valid in the same snapshot.
"""

import re
import pandas as pd

ENGINE_VERSION = "CHAIN-SHADOW-1.0"

ALIASES = {
    "underlying": [
        "نماد سهم پایه", "نماد پایه", "سهم پایه", "دارایی پایه",
        "نام دارایی پایه", "شناسه دارایی پایه", "Underlying", "UnderlyingSymbol"
    ],
    "contract_type": [
        "نوع قرارداد", "نوع اختیار", "نوع آپشن", "نوع", "ContractType", "OptionType"
    ],
    "expiry": ["تاریخ سررسید", "سررسید", "Expiry", "Expiration"],
    "strike": ["قیمت اعمال", "Strike", "StrikePrice"],
}


def _norm(v):
    return re.sub(r"[\s_]", "", str(v).strip().replace("ي", "ی").replace("ك", "ک").replace("‌", "")).lower()


def _find_column(df, aliases):
    by_norm = {_norm(c): c for c in df.columns}
    for alias in aliases:
        if _norm(alias) in by_norm:
            return by_norm[_norm(alias)]
    return None


def _clean_text(v):
    if pd.isna(v):
        return None
    s = str(v).strip().replace("ي", "ی").replace("ك", "ک").replace("‌", "")
    return s or None


def _clean_type(v):
    s = _clean_text(v)
    if not s:
        return None
    # Mapping is permitted only for explicit type fields, never for symbols.
    n = s.lower()
    if n in {"call", "c", "خرید", "اختیار خرید"}:
        return "CALL"
    if n in {"put", "p", "فروش", "اختیار فروش"}:
        return "PUT"
    return s


def build_chain_identity(df):
    required = ["نماد"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {
            "status": "INSUFFICIENT_DATA",
            "engine_version": ENGINE_VERSION,
            "missing_columns": missing,
            "rows": [],
            "summary": {},
        }

    cols = {k: _find_column(df, v) for k, v in ALIASES.items()}
    rows = []
    for idx, row in df.iterrows():
        symbol = _clean_text(row.get("نماد"))
        underlying = _clean_text(row.get(cols["underlying"])) if cols["underlying"] else None
        expiry = _clean_text(row.get(cols["expiry"])) if cols["expiry"] else None
        strike = row.get(cols["strike"]) if cols["strike"] else None
        contract_type = _clean_type(row.get(cols["contract_type"])) if cols["contract_type"] else None

        if strike is not None and not pd.isna(strike):
            try:
                strike = float(strike)
            except (TypeError, ValueError):
                strike = None

        reasons = []
        if not underlying:
            reasons.append("MISSING_EXPLICIT_UNDERLYING")
        if not expiry:
            reasons.append("MISSING_EXPLICIT_EXPIRY")
        if strike is None:
            reasons.append("MISSING_EXPLICIT_STRIKE")

        valid = not reasons
        chain_key = None
        if valid:
            chain_key = f"{underlying}::{expiry}::{strike:g}"

        rows.append({
            "row_index": int(idx),
            "symbol": symbol,
            "underlying": underlying,
            "expiry": expiry,
            "strike": strike,
            "contract_type": contract_type,
            "chain_key": chain_key,
            "status": "VALID" if valid else "INSUFFICIENT_DATA",
            "reasons": reasons,
        })

    valid_rows = [r for r in rows if r["status"] == "VALID"]
    groups = {}
    for r in valid_rows:
        groups.setdefault(r["chain_key"], []).append(r)

    ambiguous = []
    for key, members in groups.items():
        types = {m["contract_type"] for m in members if m["contract_type"]}
        if len(types) > 2:
            ambiguous.append(key)
        # Duplicate identity with conflicting explicit contract types is retained
        # as a warning, never silently collapsed.
        if len(types) == 2 and len(members) < 2:
            ambiguous.append(key)

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "columns_used": cols,
        "summary": {
            "rows_scanned": len(rows),
            "valid_identity_rows": len(valid_rows),
            "insufficient_identity_rows": len(rows) - len(valid_rows),
            "chain_count": len(groups),
            "ambiguous_chain_count": len(set(ambiguous)),
        },
        "rows": rows,
        "chains": {
            key: {
                "chain_key": key,
                "members": [m["symbol"] for m in members],
                "member_count": len(members),
                "contract_types": sorted({m["contract_type"] for m in members if m["contract_type"]}),
            }
            for key, members in groups.items()
            if key not in set(ambiguous)
        },
    }
