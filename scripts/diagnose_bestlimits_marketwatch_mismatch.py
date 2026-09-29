#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Non-production RCA diagnostic for TSETMC MarketWatch vs BestLimits.

Purpose:
- measure whether qmd/qmo and qTitMeDem/qTitMeOf differ persistently or only
  because the two endpoints are sampled at different moments;
- record exact timestamps, payload hashes, first-level six fields, and deltas;
- never assert or change semantic mapping;
- never enable scoring/ranking.

This diagnostic is evidence collection only and is not a Gate 7 close.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError

MARKET_WATCH_PATH = "/ClosingPrice/GetMarketWatch"
MARKET_WATCH_PARAMS = (
    "market=0"
    "&paperTypes%5B0%5D=1&paperTypes%5B1%5D=2&paperTypes%5B2%5D=3"
    "&paperTypes%5B3%5D=4&paperTypes%5B4%5D=5&paperTypes%5B5%5D=6"
    "&paperTypes%5B6%5D=7&paperTypes%5B7%5D=8&paperTypes%5B8%5D=9"
    "&showTraded=false&withBestLimits=true&hEven=0&RefID=0"
)
RETRYABLE_HTTP_STATUS = {502, 503, 504}
MAX_TRANSIENT_RETRIES = 2
USER_AGENT = "OptimusAI-V4.1-BestLimits-RCA-Diagnostic/1.0"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()

def fetch_json(endpoint: str, timeout: float) -> tuple[dict, str, str, int, int]:
    request = urllib.request.Request(
        endpoint,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.tsetmc.com/",
        },
    )
    last_error = None
    retry_count = 0
    for attempt in range(MAX_TRANSIENT_RETRIES + 1):
        started = utc_now()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                body = response.read()
            retrieved = utc_now()
            payload = json.loads(body.decode("utf-8", errors="replace"))
            return payload, started, retrieved, status, retry_count
        except HTTPError as exc:
            last_error = exc
            if exc.code not in RETRYABLE_HTTP_STATUS or attempt >= MAX_TRANSIENT_RETRIES:
                raise
            retry_count += 1
            time.sleep(0.75 * (attempt + 1))
    raise RuntimeError(f"request failed: {last_error}") from last_error

def iso_delta(a: str, b: str) -> float:
    return abs((datetime.fromisoformat(a) - datetime.fromisoformat(b)).total_seconds())

def extract_market_level(payload: dict, instrument_id: str) -> dict:
    rows = payload.get("marketwatch") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError("MarketWatch marketwatch list missing")
    for row in rows:
        if isinstance(row, dict) and str(row.get("insCode") or "").strip() == instrument_id:
            levels = row.get("blDs")
            if not isinstance(levels, list) or not levels:
                raise RuntimeError(f"MarketWatch blDs missing for {instrument_id}")
            return levels[0]
    raise RuntimeError(f"instrument {instrument_id} missing from MarketWatch")

def extract_best_level(payload: dict, instrument_id: str) -> dict:
    levels = payload.get("bestLimits") if isinstance(payload, dict) else None
    if not isinstance(levels, list) or not levels:
        raise RuntimeError(f"BestLimits bestLimits missing for {instrument_id}")
    return levels[0]

def compact(level: dict, source: str) -> dict:
    keys = (
        ("pmd", "pmd"), ("pmo", "pmo"), ("qmd", "qmd"),
        ("qmo", "qmo"), ("zmd", "zmd"), ("zmo", "zmo")
    ) if source == "marketwatch" else (
        ("pMeDem", "pMeDem"), ("pMeOf", "pMeOf"),
        ("qTitMeDem", "qTitMeDem"), ("qTitMeOf", "qTitMeOf"),
        ("zOrdMeDem", "zOrdMeDem"), ("zOrdMeOf", "zOrdMeOf")
    )
    return {name: level.get(raw) for name, raw in keys}

def compare(mw: dict, bl: dict) -> dict:
    pairs = {
        "pd": ("pmd", "pMeDem"),
        "po": ("pmo", "pMeOf"),
        "qd": ("qmd", "qTitMeDem"),
        "qo": ("qmo", "qTitMeOf"),
        "zd": ("zmd", "zOrdMeDem"),
        "zo": ("zmo", "zOrdMeOf"),
    }
    result = {}
    for field, (a, b) in pairs.items():
        result[field] = {
            "marketwatch": mw.get(a),
            "bestlimits": bl.get(b),
            "match": mw.get(a) == bl.get(b),
        }
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument-id", required=True)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--pause-seconds", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="https://cdn.tsetmc.com/api")
    args = parser.parse_args()

    if args.rounds < 3:
        raise ValueError("--rounds must be at least 3")

    mw_endpoint = (
        f"{args.base_url.rstrip('/')}{MARKET_WATCH_PATH}?{MARKET_WATCH_PARAMS}"
    )
    bl_endpoint = f"{args.base_url.rstrip('/')}/BestLimits/{args.instrument_id}"

    observations = []
    for round_no in range(1, args.rounds + 1):
        mw_payload, mw_started, mw_retrieved, mw_status, mw_retries = fetch_json(
            mw_endpoint, args.timeout
        )
        mw_level = extract_market_level(mw_payload, args.instrument_id)
        mw_body_hash = sha256_bytes(
            json.dumps(mw_payload, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
        )

        bl_payload, bl_started, bl_retrieved, bl_status, bl_retries = fetch_json(
            bl_endpoint, args.timeout
        )
        bl_level = extract_best_level(bl_payload, args.instrument_id)
        bl_body_hash = sha256_bytes(
            json.dumps(bl_payload, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
        )

        mw_compact = compact(mw_level, "marketwatch")
        bl_compact = compact(bl_level, "bestlimits")
        observations.append({
            "round": round_no,
            "marketwatch": {
                "started_at_utc": mw_started,
                "retrieved_at_utc": mw_retrieved,
                "http_status": mw_status,
                "retry_count": mw_retries,
                "payload_sha256": mw_body_hash,
                "level_1": mw_compact,
            },
            "bestlimits": {
                "started_at_utc": bl_started,
                "retrieved_at_utc": bl_retrieved,
                "http_status": bl_status,
                "retry_count": bl_retries,
                "payload_sha256": bl_body_hash,
                "level_1": bl_compact,
            },
            "delta_seconds": iso_delta(mw_retrieved, bl_retrieved),
            "comparison": compare(mw_compact, bl_compact),
        })
        if round_no < args.rounds and args.pause_seconds > 0:
            time.sleep(args.pause_seconds)

    summary = {}
    for field in ("pd", "po", "qd", "qo", "zd", "zo"):
        matches = sum(
            1 for obs in observations if obs["comparison"][field]["match"]
        )
        summary[field] = {
            "match_count": matches,
            "mismatch_count": len(observations) - matches,
        }

    package = {
        "schema_version": "BESTLIMITS_MARKETWATCH_RCA_DIAGNOSTIC_V1",
        "status": "DIAGNOSTIC_ONLY",
        "source_of_truth": "TSETMC",
        "instrument_id": args.instrument_id,
        "round_count": len(observations),
        "field_summary": summary,
        "observations": observations,
        "semantic_mapping_status": "FROZEN",
        "scoring_status": "BLOCKED",
        "gate_7_status": "NOT_CLOSED",
        "interpretation": (
            "Raw timing diagnostic only. No conclusion about semantic mapping "
            "is encoded in this artifact."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(package, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    print(json.dumps({
        "status": "SUCCESS",
        "diagnostic_only": True,
        "instrument_id": args.instrument_id,
        "rounds": len(observations),
        "field_summary": summary,
        "output": str(args.output),
    }, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
