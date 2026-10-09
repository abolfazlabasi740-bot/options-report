#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize a saved TSETMC identity catalog without network calls or classification."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "output" / "base_share" / "market_watch_identity_catalog.json"
OUT = ROOT / "output" / "base_share" / "market_watch_identity_catalog_analysis.json"


def main():
    if not SOURCE.exists():
        raise SystemExit(f"CATALOG_NOT_FOUND: {SOURCE}")
    report = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = report.get("records")
    if not isinstance(records, list):
        raise SystemExit("INVALID_CATALOG: records must be a list")

    statuses = Counter()
    sectors = Counter()
    subsectors = Counter()
    cgr_codes = Counter()
    cgr_titles = Counter()
    sources = Counter()
    flow_values = Counter()
    identity_symbols = 0
    missing_identity = 0
    missing_sector = 0
    examples_by_sector = {}

    for row in records:
        status = row.get("identity_status", "UNKNOWN")
        statuses[status] += 1
        ident = row.get("identity") or {}
        if not ident:
            missing_identity += 1
        symbol = ident.get("symbol")
        if symbol:
            identity_symbols += 1
        sector_code = ident.get("sector_code")
        sector_name = ident.get("sector_name")
        if sector_code in (None, "") or sector_name in (None, ""):
            missing_sector += 1
        sector_key = (str(sector_code), str(sector_name))
        sectors[sector_key] += 1
        sub_key = (str(ident.get("subsector_code")), str(ident.get("subsector_name")))
        subsectors[sub_key] += 1
        cgr_codes[str(ident.get("cgrValCot"))] += 1
        cgr_titles[str(ident.get("cgrValCotTitle"))] += 1
        sources[str(ident.get("sourceID"))] += 1
        flow_values[str(ident.get("flow"))] += 1
        if sector_key not in examples_by_sector and ident:
            examples_by_sector[sector_key] = []
        if ident and len(examples_by_sector.get(sector_key, [])) < 3:
            examples_by_sector[sector_key].append({
                "instrument_id": row.get("instrument_id"),
                "symbol": symbol,
                "name": ident.get("name"),
                "subsector_code": ident.get("subsector_code"),
                "subsector_name": ident.get("subsector_name"),
                "cIsin": ident.get("cIsin"),
                "cgrValCot": ident.get("cgrValCot"),
                "cgrValCotTitle": ident.get("cgrValCotTitle"),
                "sourceID": ident.get("sourceID"),
            })

    def counter_rows(counter, keys, limit=None):
        pairs = counter.most_common(limit)
        return [{**dict(zip(keys, key if isinstance(key, tuple) else (key,))), "count": count}
                for key, count in pairs]

    analysis = {
        "schema_version": "1.0",
        "purpose": "DIAGNOSTIC_ONLY_NO_CLASSIFICATION_NO_SCORING",
        "input_file": str(SOURCE.relative_to(ROOT)),
        "source_snapshot_sha256": report.get("source_snapshot_sha256"),
        "source_raw_record_count": report.get("source_raw_record_count"),
        "catalog_record_count": len(records),
        "identity_status_counts": dict(statuses),
        "identity_symbol_available_count": identity_symbols,
        "missing_identity_count": missing_identity,
        "missing_sector_count": missing_sector,
        "sector_distribution": counter_rows(sectors, ("sector_code", "sector_name")),
        "subsector_distribution_top_100": counter_rows(subsectors, ("subsector_code", "subsector_name"), 100),
        "cgrValCot_distribution": dict(cgr_codes),
        "cgrValCotTitle_distribution": dict(cgr_titles),
        "sourceID_distribution": dict(sources),
        "flow_distribution": dict(flow_values),
        "examples_by_sector_first_three": [
            {
                "sector_code": code,
                "sector_name": name,
                "count": count,
                "examples": examples_by_sector.get((code, name), []),
            }
            for (code, name), count in sectors.most_common()
        ],
        "classification_status": "NOT_CLASSIFIED; review source-field semantics before setting any class",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("ANALYSIS_STATUS = DIAGNOSTIC_ONLY")
    print("CATALOG_RECORDS =", len(records))
    print("IDENTITY_STATUS_COUNTS =", json.dumps(dict(statuses), ensure_ascii=False))
    print("SYMBOL_AVAILABLE =", identity_symbols)
    print("MISSING_IDENTITY =", missing_identity)
    print("MISSING_SECTOR =", missing_sector)
    print("SECTOR_DISTRIBUTION =", json.dumps(analysis["sector_distribution"], ensure_ascii=False))
    print("SUBSECTOR_TOP_100 =", json.dumps(analysis["subsector_distribution_top_100"], ensure_ascii=False))
    print("CGRVALCOT_DISTRIBUTION =", json.dumps(dict(cgr_codes), ensure_ascii=False))
    print("CGRVALCOTTITLE_DISTRIBUTION =", json.dumps(dict(cgr_titles), ensure_ascii=False))
    print("SOURCEID_DISTRIBUTION =", json.dumps(dict(sources), ensure_ascii=False))
    print("OUTPUT =", OUT)


if __name__ == "__main__":
    main()
