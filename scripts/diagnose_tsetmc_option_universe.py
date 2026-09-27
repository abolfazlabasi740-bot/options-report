#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose validated TSETMC option IDs absent from the public MarketWatch snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tsetmc_adapter import TSETMCAdapter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "history" / "universe_reconciliation_details.json"


def _market_watch_ids(adapter: TSETMCAdapter) -> tuple[set[str], dict[str, Any]]:
    path = (
        "ClosingPrice/GetMarketWatch"
        "?market=0&industrialGroup="
        "&paperTypes%5B0%5D=1&paperTypes%5B1%5D=2&paperTypes%5B2%5D=3"
        "&paperTypes%5B3%5D=4&paperTypes%5B4%5D=5&paperTypes%5B5%5D=6"
        "&paperTypes%5B6%5D=7&paperTypes%5B7%5D=8&paperTypes%5B8%5D=9"
        "&showTraded=false&withBestLimits=false&hEven=0&RefID=0"
    )
    raw = adapter._request(path)
    rows = raw.payload.get("marketwatch", []) if isinstance(raw.payload, dict) else []
    ids = {
        str(row.get("insCode"))
        for row in rows
        if isinstance(row, dict) and row.get("insCode") not in (None, "")
    }
    return ids, {
        "endpoint": raw.endpoint,
        "snapshot_sha256": raw.sha256,
        "retrieved_at": raw.retrieved_at,
        "record_count": len(rows) if isinstance(rows, list) else 0,
        "instrument_id_count": len(ids),
    }


def run() -> dict[str, Any]:
    adapter = TSETMCAdapter()
    universe = adapter.option_market_watch_universe()
    validated = {
        str(row["instrument_id"])
        for row in universe.get("records", [])
        if row.get("instrument_id") not in (None, "")
    }
    market_ids, market_meta = _market_watch_ids(adapter)
    missing_ids = sorted(validated - market_ids)

    details = []
    for instrument_id in missing_ids:
        item: dict[str, Any] = {
            "instrument_id": instrument_id,
            "status": "INSPECTED",
            "identity": None,
            "info": None,
            "quote": None,
            "errors": [],
        }
        try:
            item["identity"] = adapter.instrument_identity(instrument_id)
        except Exception as exc:
            item["errors"].append({
                "endpoint": "Instrument/GetInstrumentIdentity",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        try:
            item["info"] = adapter.instrument_info(instrument_id)
        except Exception as exc:
            item["errors"].append({
                "endpoint": "Instrument/GetInstrumentInfo",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        try:
            item["quote"] = adapter.quote(instrument_id)
        except Exception as exc:
            item["errors"].append({
                "endpoint": "ClosingPrice/GetClosingPriceInfo",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        details.append(item)

    result = {
        "status": "PASS",
        "engine_version": "TSETMC-UNIVERSE-RECONCILIATION-DETAILS-1.0",
        "source_of_truth": "TSETMC",
        "validated_option_universe": {
            "record_count": universe.get("record_count"),
            "snapshot_sha256": universe.get("snapshot_sha256"),
            "retrieved_at": universe.get("retrieved_at"),
            "flow_evidence": universe.get("flow_evidence"),
        },
        "public_market_watch": market_meta,
        "reconciliation": {
            "validated_ids": len(validated),
            "market_watch_ids": len(market_ids),
            "exact_intersection": len(validated & market_ids),
            "missing_from_market_watch": len(missing_ids),
            "missing_ids": missing_ids,
        },
        "instrument_details": details,
        "interpretation": {
            "production_universe_changed": False,
            "classification": "EVIDENCE_ONLY_PENDING_REVIEW",
            "no_missing_id_is_dropped_from_production_universe_by_this_diagnostic": True,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    result = run()
    print("STATUS =", result["status"])
    print("VALIDATED_OPTION_UNIVERSE =", result["reconciliation"]["validated_ids"])
    print("PUBLIC_MARKET_WATCH_IDS =", result["reconciliation"]["market_watch_ids"])
    print("EXACT_INTERSECTION =", result["reconciliation"]["exact_intersection"])
    print("MISSING_FROM_MARKET_WATCH =", result["reconciliation"]["missing_from_market_watch"])
    for item in result["instrument_details"]:
        identity = (item.get("identity") or {}).get("data") or {}
        info = (item.get("info") or {}).get("data") or {}
        quote = (item.get("quote") or {}).get("data") or {}
        print(
            item["instrument_id"],
            "| symbol=", identity.get("lVal18AFC") or info.get("lVal18AFC"),
            "| errors=", len(item.get("errors", [])),
            "| quote=", quote.get("pDrCotVal"),
            "| dEven=", quote.get("dEven"),
            "| hEven=", quote.get("hEven"),
        )
    print("OUTPUT_FILE =", OUT)
