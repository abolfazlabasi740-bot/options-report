#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostic-only discovery of TSETMC market-watch instrument universe.

This script does not change the production scoring universe. It saves the raw
source evidence and a compact field/count summary so instrument classification
can be designed from observed fields rather than guessed symbol patterns.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsetmc_adapter import TSETMCAdapter
OUT = ROOT / "output" / "base_share"
TEHRAN = ZoneInfo("Asia/Tehran")


def counter_for(rows, key):
    counts = Counter()
    for row in rows:
        value = row.get(key)
        counts[str(value) if value not in (None, "") else "UNAVAILABLE"] += 1
    return dict(counts.most_common(40))


def main():
    result = TSETMCAdapter(timeout=5.0, retries=1).market_watch_universe_raw()
    rows = result.get("records") or []
    raw_fields = Counter()
    for row in rows:
        raw = row.get("raw")
        if isinstance(raw, dict):
            raw_fields.update(raw.keys())

    # Enrich a tiny, deterministic sample through the explicit identity endpoint.
    # This is diagnostic only; it does not classify the entire universe or score it.
    identity_samples = []
    adapter = TSETMCAdapter(timeout=3.0, retries=0)
    for row in rows[:5]:
        instrument_id = row.get("instrument_id")
        item = {"market_watch_record": row, "identity_status": "NOT_ATTEMPTED"}
        if instrument_id:
            try:
                identity = adapter.instrument_identity(str(instrument_id))
                item["identity_status"] = "SUCCESS"
                item["identity_endpoint"] = identity.get("endpoint")
                item["identity_payload"] = identity.get("data")
                payload = identity.get("data")
                item["identity_payload_keys"] = sorted(payload.keys()) if isinstance(payload, dict) else None
            except Exception as exc:
                item["identity_status"] = "FAILED"
                item["identity_error_type"] = type(exc).__name__
                item["identity_error"] = str(exc)[:300]
        identity_samples.append(item)

    evidence = {
        "generated_at": datetime.now(TEHRAN).isoformat(),
        "source_of_truth": "TSETMC",
        "purpose": "DIAGNOSTIC_ONLY_NOT_USED_FOR_SCORING",
        "endpoint": result.get("endpoint"),
        "retrieved_at": result.get("retrieved_at"),
        "snapshot_sha256": result.get("snapshot_sha256"),
        "raw_record_count": result.get("raw_record_count"),
        "normalized_unique_record_count": len(rows),
        "raw_payload_keys": result.get("raw_payload_keys"),
        "field_presence_count": dict(raw_fields.most_common()),
        "flow_distribution": counter_for(rows, "flow"),
        "paper_type_distribution": counter_for(rows, "paper_type"),
        "market_status_distribution": counter_for(rows, "market_status"),
        "sample_records": rows[:12],
        "identity_enrichment_sample_count": len(identity_samples),
        "identity_enrichment_samples": identity_samples,
        "records": rows,
        "classification_status": "NOT_CLASSIFIED_UNTIL_SOURCE_FIELDS_ARE_VERIFIED",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    json_path = OUT / "market_watch_universe_probe.json"
    txt_path = OUT / "market_watch_universe_probe.txt"
    json_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    lines = [
        "TSETMC MARKET-WATCH UNIVERSE PROBE — DIAGNOSTIC ONLY",
        "=" * 60,
        "زمان تولید: " + evidence["generated_at"],
        "Endpoint: " + str(evidence["endpoint"]),
        "زمان دریافت منبع: " + str(evidence["retrieved_at"]),
        "هش snapshot: " + str(evidence["snapshot_sha256"]),
        "تعداد خام منبع: " + str(evidence["raw_record_count"]),
        "تعداد رکورد یکتای نرمال‌شده: " + str(evidence["normalized_unique_record_count"]),
        "توزیع flow: " + json.dumps(evidence["flow_distribution"], ensure_ascii=False),
        "توزیع paper_type: " + json.dumps(evidence["paper_type_distribution"], ensure_ascii=False),
        "توزیع وضعیت بازار: " + json.dumps(evidence["market_status_distribution"], ensure_ascii=False),
        "فیلدهای مشاهده‌شده: " + ", ".join(evidence["field_presence_count"]),
        "نمونه‌های هویت‌سنجی: " + json.dumps([{"id": x.get("market_watch_record", {}).get("instrument_id"), "status": x.get("identity_status"), "keys": x.get("identity_payload_keys"), "error": x.get("identity_error_type")} for x in identity_samples], ensure_ascii=False),
        "وضعیت طبقه‌بندی: هنوز تأیید نشده؛ در امتیازدهی استفاده نمی‌شود.",
        "فایل شواهد JSON: " + str(json_path),
    ]
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("PROBE_JSON =", json_path)
    print("PROBE_TEXT =", txt_path)
    print("PROBE_STATUS = DIAGNOSTIC_ONLY")


if __name__ == "__main__":
    main()
