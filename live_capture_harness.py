#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Isolated TSETMC BestLimits capture harness.

Governance:
- BestLimits is captured directly from TSETMC.
- No TSETMCAdapter, canonical snapshot, feature engine, scoring engine, or
  OptionSchool dependency is used.
- This tool captures evidence; it does NOT interpret zo/zd/pd/po/qd/qo.
- It must not be used as proof that the candidate semantic mapping is correct.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BASE_URL = "https://cdn.tsetmc.com/api"
USER_AGENT = "OptimusAI-V4.1-BestLimits-LiveCapture/1.0"


def sha256_json(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def capture(instrument_id: str, base_url: str, timeout: float) -> dict:
    if not instrument_id.strip():
        raise ValueError("instrument_id is required")

    endpoint = f"{base_url.rstrip('/')}/BestLimits/{instrument_id}"
    started_at = utc_now()
    request = urllib.request.Request(
        endpoint,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        http_status = getattr(response, "status", 200)
        body = response.read()

    retrieved_at = utc_now()
    if http_status < 200 or http_status >= 300:
        raise RuntimeError(f"HTTP status {http_status}")

    text = body.decode("utf-8", errors="replace")
    payload = json.loads(text)
    raw_levels = payload.get("bestLimits") if isinstance(payload, dict) else None
    if not isinstance(raw_levels, list):
        raise RuntimeError("bestLimits list is missing from TSETMC payload")

    return {
        "schema_version": "LIVE_TIME_LOCKED_BESTLIMITS_CAPTURE_V1",
        "source": "TSETMC",
        "instrument_id": str(instrument_id),
        "endpoint": endpoint,
        "capture_started_at_utc": started_at,
        "retrieved_at_utc": retrieved_at,
        "http_status": http_status,
        "payload_sha256": sha256_json(payload),
        "level_count": len(raw_levels),
        "raw_levels": raw_levels,
        "semantic_mapping_status": "OPEN",
        "scoring_status": "BLOCKED",
        "interpretation_note": (
            "Raw evidence only. No semantic translation of zo/zd/pd/po/qd/qo "
            "is asserted by this capture."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    evidence = capture(args.instrument_id, args.base_url, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "SUCCESS",
        "instrument_id": evidence["instrument_id"],
        "endpoint": evidence["endpoint"],
        "retrieved_at_utc": evidence["retrieved_at_utc"],
        "payload_sha256": evidence["payload_sha256"],
        "level_count": evidence["level_count"],
        "output": str(args.output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
