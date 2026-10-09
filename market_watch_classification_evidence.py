#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence audit of TSETMC identity fields before any common-equity classification.

Offline only. Does not classify instruments, score them, or create trading signals.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "output" / "base_share" / "market_watch_identity_catalog.json"
OUT = ROOT / "output" / "base_share" / "market_watch_classification_evidence.json"


def norm(value):
    if value is None:
        return "MISSING"
    text = str(value).strip()
    return text if text else "MISSING"


def digest_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not SOURCE.exists():
        raise SystemExit(f"CATALOG_NOT_FOUND: {SOURCE}")
    catalog = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = catalog.get("records")
    if not isinstance(records, list):
        raise SystemExit("INVALID_CATALOG: records must be a list")

    status_counts = Counter()
    sector_counts = Counter()
    subsector_counts = Counter()
    market_title_counts = Counter()
    market_code_counts = Counter()
    sector_market = Counter()
    subsector_market = Counter()
    examples = defaultdict(list)
    unknown_examples = []
    successful = 0

    for row in records:
        ident = row.get("identity") or {}
        status = norm(row.get("identity_status"))
        status_counts[status] += 1
        if status != "SUCCESS" or not ident:
            if len(unknown_examples) < 30:
                unknown_examples.append({
                    "instrument_id": row.get("instrument_id"),
                    "identity_status": status,
                    "error_type": row.get("error_type"),
                    "error_message": row.get("error_message"),
                })
            continue
        successful += 1
        sector = norm(ident.get("sector_code"))
        sector_name = norm(ident.get("sector_name"))
        sub = norm(ident.get("subsector_code"))
        sub_name = norm(ident.get("subsector_name"))
        market_code = norm(ident.get("cgrValCot"))
        market_title = norm(ident.get("cgrValCotTitle"))
        sector_counts[(sector, sector_name)] += 1
        subsector_counts[(sub, sub_name)] += 1
        market_code_counts[market_code] += 1
        market_title_counts[market_title] += 1
        sector_market[(sector, sector_name, market_code, market_title)] += 1
        subsector_market[(sub, sub_name, market_code, market_title)] += 1
        group_key = (sector, sector_name, market_code, market_title)
        if len(examples[group_key]) < 5:
            examples[group_key].append({
                "instrument_id": row.get("instrument_id"),
                "symbol": ident.get("symbol"),
                "name": ident.get("name"),
                "sector_code": sector,
                "sector_name": sector_name,
                "subsector_code": sub,
                "subsector_name": sub_name,
                "cgrValCot": market_code,
                "cgrValCotTitle": market_title,
                "cIsin": ident.get("cIsin"),
                "zTitad": ident.get("zTitad"),
            })

    def rows(counter, fields, limit=None):
        items = counter.most_common(limit)
        out = []
        for key, count in items:
            values = key if isinstance(key, tuple) else (key,)
            out.append({**dict(zip(fields, values)), "count": count})
        return out

    grouped = []
    for (sector, sector_name, market_code, market_title), count in sector_market.most_common():
        grouped.append({
            "sector_code": sector,
            "sector_name": sector_name,
            "cgrValCot": market_code,
            "cgrValCotTitle": market_title,
            "count": count,
            "examples": examples[(sector, sector_name, market_code, market_title)],
        })

    report = {
        "schema_version": "1.0",
        "status": "EVIDENCE_AUDIT_ONLY_NO_CLASSIFICATION_NO_SCORING",
        "source_file": str(SOURCE.relative_to(ROOT)),
        "source_file_sha256": digest_file(SOURCE),
        "source_snapshot_sha256": catalog.get("source_snapshot_sha256"),
        "catalog_record_count": len(records),
        "identity_success_count": successful,
        "identity_status_counts": dict(status_counts),
        "sector_distribution": rows(sector_counts, ("sector_code", "sector_name")),
        "subsector_distribution_top_150": rows(subsector_counts, ("subsector_code", "subsector_name"), 150),
        "cgrValCot_distribution": rows(market_code_counts, ("cgrValCot",)),
        "cgrValCotTitle_distribution": rows(market_title_counts, ("cgrValCotTitle",)),
        "sector_market_cross_tab": grouped,
        "identity_failure_examples": unknown_examples,
        "classification_decision": "NOT_MADE",
        "reason": "Inspect sector/market cross-tabs and instrument examples before defining an explicit allowlist; missing or conflicting fields must remain unclassified.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("STATUS = EVIDENCE_AUDIT_ONLY_NO_CLASSIFICATION_NO_SCORING")
    print("CATALOG_RECORDS =", len(records))
    print("IDENTITY_SUCCESS =", successful)
    print("IDENTITY_STATUS_COUNTS =", json.dumps(dict(status_counts), ensure_ascii=False))
    print("SECTOR_DISTRIBUTION =", json.dumps(report["sector_distribution"], ensure_ascii=False))
    print("SUBSECTOR_TOP_150 =", json.dumps(report["subsector_distribution_top_150"], ensure_ascii=False))
    print("CGRVALCOT_DISTRIBUTION =", json.dumps(report["cgrValCot_distribution"], ensure_ascii=False))
    print("CGRVALCOTTITLE_DISTRIBUTION =", json.dumps(report["cgrValCotTitle_distribution"], ensure_ascii=False))
    print("SECTOR_MARKET_CROSSTAB =", json.dumps(grouped, ensure_ascii=False))
    print("OUTPUT =", OUT)


if __name__ == "__main__":
    main()
