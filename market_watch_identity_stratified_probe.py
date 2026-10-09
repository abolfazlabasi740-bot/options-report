#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostic, stratified TSETMC identity probe; never used for scoring."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsetmc_adapter import TSETMCAdapter

OUT = ROOT / "output" / "base_share" / "market_watch_identity_stratified_probe.json"


def sha256_json(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def evenly_spaced_indices(length, count):
    if length <= 0 or count <= 0:
        return []
    if count >= length:
        return list(range(length))
    if count == 1:
        return [length // 2]
    # Include both ends and spread observations across the complete source list.
    return sorted({round(i * (length - 1) / (count - 1)) for i in range(count)})


def sector_text(identity):
    sector = identity.get("sector")
    sub_sector = identity.get("subSector")
    return {
        "sector_code": sector.get("cSecVal") if isinstance(sector, dict) else None,
        "sector_name": sector.get("lSecVal") if isinstance(sector, dict) else None,
        "subsector_code": (
            sub_sector.get("cSoSecVal") if isinstance(sub_sector, dict) else None
        ),
        "subsector_name": (
            sub_sector.get("lSoSecVal") if isinstance(sub_sector, dict) else None
        ),
    }


def main():
    # Bounded diagnostic: 60 records distributed across the entire 3,000+ row list.
    adapter = TSETMCAdapter(timeout=3.0, retries=0)
    universe = adapter.market_watch_universe_raw(with_best_limits=False)
    records = universe.get("records") or []
    indices = evenly_spaced_indices(len(records), 60)
    results = []
    errors = Counter()
    sectors = Counter()
    flows = Counter()
    symbol_count = 0

    for index in indices:
        row = records[index]
        instrument_id = row.get("instrument_id")
        item = {
            "source_index": index,
            "instrument_id": instrument_id,
            "market_watch_symbol": row.get("symbol"),
            "market_watch_name": row.get("name"),
            "identity_status": "NOT_ATTEMPTED",
        }
        if not instrument_id:
            item["identity_status"] = "FAILED_NO_INSTRUMENT_ID"
            results.append(item)
            errors[item["identity_status"]] += 1
            continue
        try:
            wrapped = adapter.instrument_identity(str(instrument_id))
            identity = wrapped.get("data")
            if not isinstance(identity, dict):
                item["identity_status"] = "FAILED_NO_IDENTITY_DATA"
                item["identity_payload_type"] = type(identity).__name__
                errors[item["identity_status"]] += 1
            else:
                item["identity_status"] = "SUCCESS"
                item["identity_source"] = {
                    "endpoint": wrapped.get("endpoint"),
                    "snapshot_sha256": wrapped.get("snapshot_sha256"),
                    "retrieved_at": wrapped.get("retrieved_at"),
                }
                item["identity"] = {
                    "symbol": identity.get("lVal18AFC"),
                    "name": identity.get("lVal30"),
                    "flow": identity.get("flow"),
                    "flow_title": identity.get("flowTitle"),
                    **sector_text(identity),
                    "cIsin": identity.get("cIsin"),
                    "cgrValCot": identity.get("cgrValCot"),
                    "cgrValCotTitle": identity.get("cgrValCotTitle"),
                    "sourceID": identity.get("sourceID"),
                    "instrumentID": identity.get("instrumentID"),
                }
                ident = item["identity"]
                if ident.get("symbol"):
                    symbol_count += 1
                sectors[(str(ident.get("sector_code")), str(ident.get("sector_name")))] += 1
                flows[str(ident.get("flow"))] += 1
        except Exception as exc:
            item["identity_status"] = "FAILED"
            item["error_type"] = type(exc).__name__
            errors[type(exc).__name__] += 1
        results.append(item)

    report = {
        "schema_version": "1.0",
        "purpose": "DIAGNOSTIC_ONLY_NOT_USED_FOR_SCORING",
        "classification_status": "NOT_CLASSIFIED_UNTIL_SOURCE_FIELDS_ARE_VERIFIED",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "TSETMC",
        "source_endpoint": universe.get("endpoint"),
        "source_retrieved_at": universe.get("retrieved_at"),
        "source_snapshot_sha256": universe.get("snapshot_sha256"),
        "raw_record_count": universe.get("raw_record_count"),
        "normalized_record_count": len(records),
        "sample_design": "60 deterministic evenly spaced records across the full normalized source list",
        "sample_count": len(results),
        "identity_success_count": sum(x.get("identity_status") == "SUCCESS" for x in results),
        "identity_symbol_available_count": symbol_count,
        "identity_status_counts": dict(Counter(x["identity_status"] for x in results)),
        "identity_error_counts": dict(errors),
        "sector_distribution_in_sample": [
            {"sector_code": key[0], "sector_name": key[1], "count": count}
            for key, count in sectors.most_common()
        ],
        "flow_distribution_in_sample": dict(flows),
        "samples": results,
    }
    report["report_sha256"] = sha256_json(report)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("PROBE_STATUS = DIAGNOSTIC_ONLY")
    print("SOURCE_RECORDS =", report["normalized_record_count"])
    print("SAMPLE_COUNT =", report["sample_count"])
    print("IDENTITY_SUCCESS =", report["identity_success_count"])
    print("IDENTITY_SYMBOL_AVAILABLE =", report["identity_symbol_available_count"])
    print("IDENTITY_STATUS_COUNTS =", json.dumps(report["identity_status_counts"], ensure_ascii=False))
    print("SECTOR_DISTRIBUTION =", json.dumps(report["sector_distribution_in_sample"], ensure_ascii=False))
    print("FLOW_DISTRIBUTION =", json.dumps(report["flow_distribution_in_sample"], ensure_ascii=False))
    print("SOURCE_SNAPSHOT_SHA256 =", report["source_snapshot_sha256"])
    print("REPORT_SHA256 =", report["report_sha256"])
    print("OUTPUT =", OUT)


if __name__ == "__main__":
    main()
