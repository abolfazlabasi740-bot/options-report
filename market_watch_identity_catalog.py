#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resumable, evidence-preserving identity catalog for the TSETMC market-watch universe.

This is a diagnostic catalog only. It does not score, recommend, or classify instruments.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsetmc_adapter import TSETMCAdapter

OUT = ROOT / "output" / "base_share" / "market_watch_identity_catalog.json"
LOCK = Lock()


def sha256_json(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sector_fields(identity):
    sector = identity.get("sector")
    sub = identity.get("subSector")
    return {
        "sector_code": sector.get("cSecVal") if isinstance(sector, dict) else None,
        "sector_name": sector.get("lSecVal") if isinstance(sector, dict) else None,
        "subsector_code": sub.get("cSoSecVal") if isinstance(sub, dict) else None,
        "subsector_name": sub.get("lSoSecVal") if isinstance(sub, dict) else None,
    }


def load_checkpoint():
    if not OUT.exists():
        return {}
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
        return {
            str(item["instrument_id"]): item
            for item in data.get("records", [])
            if item.get("instrument_id") not in (None, "")
        }
    except Exception:
        # Do not silently overwrite a corrupt checkpoint.
        raise RuntimeError(f"Existing checkpoint is unreadable; preserve and inspect it: {OUT}")


def fetch_identity(instrument_id):
    adapter = TSETMCAdapter(timeout=3.0, retries=0)
    try:
        wrapped = adapter.instrument_identity(str(instrument_id))
        identity = wrapped.get("data")
        if not isinstance(identity, dict):
            return {
                "instrument_id": str(instrument_id),
                "identity_status": "FAILED_NO_IDENTITY_DATA",
                "identity_payload_type": type(identity).__name__,
                "identity_endpoint": wrapped.get("endpoint"),
                "identity_snapshot_sha256": wrapped.get("snapshot_sha256"),
                "identity_retrieved_at": wrapped.get("retrieved_at"),
            }
        return {
            "instrument_id": str(instrument_id),
            "identity_status": "SUCCESS",
            "identity_endpoint": wrapped.get("endpoint"),
            "identity_snapshot_sha256": wrapped.get("snapshot_sha256"),
            "identity_retrieved_at": wrapped.get("retrieved_at"),
            "identity": {
                "symbol": identity.get("lVal18AFC"),
                "name": identity.get("lVal30"),
                "flow": identity.get("flow"),
                "flow_title": identity.get("flowTitle"),
                **sector_fields(identity),
                "cIsin": identity.get("cIsin"),
                "cgrValCot": identity.get("cgrValCot"),
                "cgrValCotTitle": identity.get("cgrValCotTitle"),
                "sourceID": identity.get("sourceID"),
                "instrumentID": identity.get("instrumentID"),
                "baseVol": identity.get("baseVol"),
                "yMarNSC": identity.get("yMarNSC"),
                "yVal": identity.get("yVal"),
                "zTitad": identity.get("zTitad"),
            },
        }
    except Exception as exc:
        return {
            "instrument_id": str(instrument_id),
            "identity_status": "FAILED",
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:300],
        }


def main():
    adapter = TSETMCAdapter(timeout=5.0, retries=1)
    universe = adapter.market_watch_universe_raw(with_best_limits=False)
    source_records = universe.get("records") or []
    existing = load_checkpoint()

    # Preserve market-watch identity and observation fields alongside identity endpoint evidence.
    by_id = {}
    for row in source_records:
        iid = row.get("instrument_id")
        if iid in (None, ""):
            continue
        by_id[str(iid)] = {
            "instrument_id": str(iid),
            "market_watch_symbol": row.get("symbol"),
            "market_watch_name": row.get("name"),
            "source_market_date": row.get("source_market_date"),
            "source_market_time": row.get("source_market_time"),
        }

    # Reuse successful identity responses only when their IDs remain in this fresh universe.
    results = {}
    for iid, item in existing.items():
        if iid in by_id and item.get("identity_status") == "SUCCESS":
            results[iid] = item

    pending = [iid for iid in by_id if iid not in results]
    print("SOURCE_RECORDS =", len(source_records), flush=True)
    print("UNIQUE_IDS =", len(by_id), flush=True)
    print("REUSED_SUCCESSFUL_IDENTITIES =", len(results), flush=True)
    print("PENDING_IDENTITIES =", len(pending), flush=True)
    print("WORKERS = 6", flush=True)
    print("MODE = DIAGNOSTIC_ONLY_NO_CLASSIFICATION_NO_SCORING", flush=True)

    completed = 0
    last_checkpoint = time.monotonic()
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch_identity, iid): iid for iid in pending}
        for future in as_completed(futures):
            iid = futures[future]
            try:
                results[iid] = future.result()
            except Exception as exc:
                results[iid] = {
                    "instrument_id": iid,
                    "identity_status": "FAILED",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)[:300],
                }
            completed += 1
            if completed % 25 == 0:
                print(f"PROGRESS = {completed}/{len(pending)}", flush=True)
            if completed % 50 == 0 or time.monotonic() - last_checkpoint >= 30:
                write_report(universe, by_id, results, partial=True)
                last_checkpoint = time.monotonic()

    write_report(universe, by_id, results, partial=False)
    print("CATALOG_STATUS = COMPLETE_WITH_EXPLICIT_FAILURES", flush=True)
    print("IDENTITY_SUCCESS =", sum(x.get("identity_status") == "SUCCESS" for x in results.values()), flush=True)
    print("IDENTITY_FAILED =", sum(x.get("identity_status") != "SUCCESS" for x in results.values()), flush=True)
    print("OUTPUT =", OUT, flush=True)


def write_report(universe, by_id, results, partial):
    records = []
    for iid, base in by_id.items():
        identity = results.get(iid)
        if identity is None:
            identity = {"instrument_id": iid, "identity_status": "PENDING"}
        records.append({**base, **identity})
    records.sort(key=lambda x: x["instrument_id"])
    status_counts = Counter(x.get("identity_status", "UNKNOWN") for x in records)
    sectors = Counter()
    flows = Counter()
    symbol_count = 0
    for item in records:
        ident = item.get("identity") or {}
        sectors[(str(ident.get("sector_code")), str(ident.get("sector_name")))] += 1
        flows[str(ident.get("flow"))] += 1
        if ident.get("symbol"):
            symbol_count += 1
    report = {
        "schema_version": "1.0",
        "purpose": "DIAGNOSTIC_ONLY_NOT_USED_FOR_SCORING",
        "classification_status": "NOT_CLASSIFIED",
        "partial": partial,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "TSETMC",
        "source_endpoint": universe.get("endpoint"),
        "source_retrieved_at": universe.get("retrieved_at"),
        "source_snapshot_sha256": universe.get("snapshot_sha256"),
        "source_raw_record_count": universe.get("raw_record_count"),
        "source_unique_record_count": len(by_id),
        "catalog_record_count": len(records),
        "identity_symbol_available_count": symbol_count,
        "identity_status_counts": dict(status_counts),
        "sector_distribution_including_failures": [
            {"sector_code": code, "sector_name": name, "count": count}
            for (code, name), count in sectors.most_common()
        ],
        "flow_distribution_including_failures": dict(flows),
        "records": records,
    }
    report["report_sha256"] = sha256_json(report)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(OUT)
    if partial:
        print("CHECKPOINT_STATUS = PARTIAL", flush=True)
        print("CHECKPOINT_STATUS_COUNTS =", json.dumps(dict(status_counts), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
