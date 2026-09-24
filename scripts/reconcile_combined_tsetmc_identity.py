#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only combined TSETMC identity reconciliation.

Combines two independent, exact-symbol evidence sources:
1) retained Option Market Watch reconciliation;
2) direct InstrumentSearch evidence for symbols absent from that snapshot.

No similarity, prefix, strike, expiry, or contract-type inference is allowed.
Conflicting explicit IDs are blocked. Production scoring/ranking is untouched.
"""

from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

SYMBOL_COLUMN = "نماد"
ID_FIELDS = ("insCode", "InsCode", "instrument_id", "InstrumentID")
SEARCH_SYMBOL_FIELDS = ("lVal18AFC", "symbol", "lVal18")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def extract_id(item):
    for field in ID_FIELDS:
        value = norm(item.get(field))
        if value is not None:
            return value
    return None


def extract_search_symbol(item):
    for field in SEARCH_SYMBOL_FIELDS:
        value = norm(item.get(field))
        if value is not None:
            return value
    return None


def load_market_watch(reconciliation_path):
    obj = json.loads(Path(reconciliation_path).read_text(encoding="utf-8"))
    mappings = {}
    for row in obj.get("row_mappings", []):
        symbol = norm(row.get("symbol"))
        if not symbol:
            continue
        if row.get("mapping_status") != "EXACT_UNIQUE_SYMBOL_MATCH":
            continue
        instrument_id = norm(row.get("tsetmc_instrument_id"))
        if instrument_id is None:
            continue
        mappings.setdefault(symbol, []).append({
            "instrument_id": instrument_id,
            "contract_type": norm(row.get("tsetmc_contract_type")),
            "underlying_id": norm(row.get("tsetmc_underlying_id")),
            "underlying_symbol": norm(row.get("tsetmc_underlying_symbol")),
            "strike": row.get("tsetmc_strike"),
            "begin_date": row.get("tsetmc_begin_date"),
            "end_date": row.get("tsetmc_end_date"),
            "remaining_days": row.get("tsetmc_remaining_days"),
            "source": "OPTION_MARKET_WATCH",
        })
    return obj, mappings


def load_search(search_path):
    obj = json.loads(Path(search_path).read_text(encoding="utf-8"))
    mappings = {}
    for evidence in obj.get("evidence", []):
        symbol = norm(evidence.get("symbol"))
        if not symbol:
            continue
        if evidence.get("status") != "EXACT_SYMBOL_MATCH":
            continue
        matches = evidence.get("exact_matches", [])
        if len(matches) != 1:
            continue
        item = matches[0]
        returned_symbol = extract_search_symbol(item)
        if returned_symbol != symbol:
            continue
        instrument_id = extract_id(item)
        if instrument_id is None:
            continue
        mappings.setdefault(symbol, []).append({
            "instrument_id": instrument_id,
            "contract_type": norm(item.get("contractType")) or norm(item.get("contract_type")),
            "underlying_id": norm(item.get("uaInsCode")),
            "underlying_symbol": norm(item.get("lval30_UA")) or norm(item.get("underlyingSymbol")),
            "strike": item.get("strikePrice"),
            "begin_date": item.get("beginDate"),
            "end_date": item.get("endDate"),
            "remaining_days": item.get("remainedDay"),
            "source": "INSTRUMENT_SEARCH",
            "retrieved_at": evidence.get("retrieved_at"),
            "endpoint": evidence.get("endpoint"),
            "response_sha256": evidence.get("snapshot_sha256"),
        })
    return obj, mappings


def reconcile(workbook, market_watch, search):
    df = pd.read_excel(workbook)
    if SYMBOL_COLUMN not in df.columns:
        raise ValueError("OptionSchool workbook has no نماد column")

    symbols = [norm(x) for x in df[SYMBOL_COLUMN].tolist()]
    if any(x is None for x in symbols):
        raise ValueError("OptionSchool contains blank نماد values")
    if len(symbols) != len(set(symbols)):
        raise ValueError("OptionSchool نماد values are not unique")

    mw_obj, mw = load_market_watch(market_watch)
    search_obj, srch = load_search(search)

    rows = []
    conflicts = []
    for row_no, symbol in enumerate(symbols, start=1):
        m = mw.get(symbol, [])
        s = srch.get(symbol, [])
        m_ids = sorted({x["instrument_id"] for x in m})
        s_ids = sorted({x["instrument_id"] for x in s})
        all_ids = sorted(set(m_ids + s_ids))

        if len(all_ids) > 1:
            status = "IDENTITY_CONFLICT"
            chosen = None
            conflicts.append({
                "optionschool_row": row_no,
                "symbol": symbol,
                "market_watch_ids": m_ids,
                "instrument_search_ids": s_ids,
            })
        elif len(all_ids) == 1:
            chosen = (m + s)[0]
            sources = []
            if m:
                sources.append("OPTION_MARKET_WATCH")
            if s:
                sources.append("INSTRUMENT_SEARCH")
            status = "EXACT_SYMBOL_MATCH"
            chosen = dict(chosen)
            chosen["identity_source"] = "+".join(sources)
        else:
            chosen = {}
            status = "UNRESOLVED"

        row = {
            "optionschool_row": row_no,
            "symbol": symbol,
            "identity_status": status,
            "identity_inference": "DISABLED",
            "tsetmc_instrument_id": chosen.get("instrument_id"),
            "identity_source": chosen.get("identity_source"),
            "tsetmc_contract_type": chosen.get("contract_type"),
            "tsetmc_underlying_id": chosen.get("underlying_id"),
            "tsetmc_underlying_symbol": chosen.get("underlying_symbol"),
            "tsetmc_strike": chosen.get("strike"),
            "tsetmc_begin_date": chosen.get("begin_date"),
            "tsetmc_end_date": chosen.get("end_date"),
            "tsetmc_remaining_days": chosen.get("remaining_days"),
        }
        rows.append(row)

    mw_symbols = set(mw)
    search_symbols = set(srch)
    overlap = mw_symbols & search_symbols
    combined = {r["symbol"] for r in rows if r["identity_status"] == "EXACT_SYMBOL_MATCH"}
    unresolved = {r["symbol"] for r in rows if r["identity_status"] == "UNRESOLVED"}

    return {
        "status": "SUCCESS",
        "workbook_sha256": sha256_file(workbook),
        "workbook_rows": int(len(df)),
        "workbook_columns": int(len(df.columns)),
        "market_watch_reconciliation_sha256": sha256_file(market_watch),
        "instrument_search_evidence_sha256": sha256_file(search),
        "market_watch_exact_symbols": len(mw_symbols),
        "instrument_search_exact_symbols": len(search_symbols),
        "source_overlap_symbols": len(overlap),
        "source_overlap_symbol_list": sorted(overlap),
        "combined_exact_unique_symbols": len(combined),
        "combined_match_rate": len(combined) / len(symbols) if symbols else None,
        "unresolved_symbols": len(unresolved),
        "identity_conflicts": len(conflicts),
        "promotion_ready": bool(len(combined) == len(symbols) and not conflicts),
        "identity_method": "COMBINED_EXACT_SYMBOL_EVIDENCE",
        "identity_inference": "DISABLED",
        "production_changed": False,
        "production_activation": "BLOCKED",
        "row_mapping_count": len(rows),
        "row_mappings": rows,
        "conflicts": conflicts,
        "market_watch_snapshot_sha256": mw_obj.get("tsetmc_snapshot_sha256"),
        "market_watch_endpoint": mw_obj.get("tsetmc_endpoint"),
        "market_watch_retrieved_at": mw_obj.get("tsetmc_retrieved_at"),
        "instrument_search_note": search_obj.get("note"),
        "note": (
            "Combined identity is accepted only from exact symbol equality with "
            "explicit TSETMC instrument IDs. InstrumentSearch and Option Market "
            "Watch are retained as separate evidence sources. Overlap is counted "
            "once; conflicting IDs block promotion. No inference is performed."
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--optionschool", required=True)
    ap.add_argument("--market-watch-reconciliation", required=True)
    ap.add_argument("--instrument-search", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    out = reconcile(a.optionschool, a.market_watch_reconciliation, a.instrument_search)
    Path(a.output).write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": out["status"],
        "workbook_rows": out["workbook_rows"],
        "market_watch_exact_symbols": out["market_watch_exact_symbols"],
        "instrument_search_exact_symbols": out["instrument_search_exact_symbols"],
        "source_overlap_symbols": out["source_overlap_symbols"],
        "combined_exact_unique_symbols": out["combined_exact_unique_symbols"],
        "unresolved_symbols": out["unresolved_symbols"],
        "identity_conflicts": out["identity_conflicts"],
        "promotion_ready": out["promotion_ready"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
