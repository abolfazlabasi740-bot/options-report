#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a real TSETMC-only BestLimits evidence package.

This runner is deliberately fail-closed:
- discovers option/underlying identities from the live TSETMC option Market-Watch;
- captures BestLimits twice for each selected instrument;
- captures independent same-time Market-Watch BestLimits observations;
- verifies the six candidate field correspondences against both live sources;
- preserves raw payloads and hashes;
- never enables scoring or ranking.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from bestlimits_evidence_gate import validate_package
from live_capture_harness import capture
from tsetmc_first_source import build_tsetmc_snapshot


MARKET_WATCH_PATH = "/ClosingPrice/GetMarketWatch"
USER_AGENT = "OptimusAI-V4.1-BestLimits-LiveEvidence/1.0"

MARKET_WATCH_PARAMS = (
    "market=0"
    "&paperTypes%5B0%5D=1"
    "&paperTypes%5B1%5D=2"
    "&paperTypes%5B2%5D=3"
    "&paperTypes%5B3%5D=4"
    "&paperTypes%5B4%5D=5"
    "&paperTypes%5B5%5D=6"
    "&paperTypes%5B6%5D=7"
    "&paperTypes%5B7%5D=8"
    "&paperTypes%5B8%5D=9"
    "&showTraded=false"
    "&withBestLimits=true"
    "&hEven=0"
    "&RefID=0"
)

FIELD_PAIRS = {
    "pd": ("pmd", "pMeDem"),
    "po": ("pmo", "pMeOf"),
    "qd": ("qmd", "qTitMeDem"),
    "qo": ("qmo", "qTitMeOf"),
    "zd": ("zmd", "zOrdMeDem"),
    "zo": ("zmo", "zOrdMeOf"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def market_watch_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{MARKET_WATCH_PATH}?{MARKET_WATCH_PARAMS}"


def fetch_market_watch_rows(
    *,
    base_url: str,
    timeout: float,
) -> tuple[list[dict], str, str, str]:
    endpoint = market_watch_url(base_url)
    request = urllib.request.Request(
        endpoint,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.tsetmc.com/",
        },
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        status = getattr(response, "status", 200)

    retrieved_at = utc_now()

    if status < 200 or status >= 300:
        raise RuntimeError(f"MarketWatch HTTP status {status}")

    payload = json.loads(body.decode("utf-8", errors="replace"))
    rows = payload.get("marketwatch") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError("MarketWatch marketwatch list missing")

    import hashlib
    snapshot_sha256 = hashlib.sha256(body).hexdigest()
    return rows, endpoint, retrieved_at, snapshot_sha256


def fetch_market_watch_level(
    instrument_id: str,
    *,
    base_url: str,
    timeout: float,
) -> tuple[dict, str, str]:
    rows, endpoint, retrieved_at, _ = fetch_market_watch_rows(
        base_url=base_url,
        timeout=timeout,
    )

    row = next(
        (
            item for item in rows
            if str(item.get("insCode") or "").strip() == instrument_id
        ),
        None,
    )
    if row is None:
        raise RuntimeError(
            f"MarketWatch instrument {instrument_id} was not found"
        )

    levels = row.get("blDs")
    if not isinstance(levels, list) or not levels:
        raise RuntimeError(
            f"MarketWatch blDs missing for {instrument_id}"
        )

    return levels[0], endpoint, retrieved_at


def verify_semantic_correspondence(
    market_watch_level: dict,
    bestlimits_capture: dict,
    *,
    instrument_id: str,
) -> dict:
    raw_levels = bestlimits_capture.get("raw_levels")
    if not isinstance(raw_levels, list) or not raw_levels:
        raise RuntimeError(
            f"BestLimits level 1 missing for {instrument_id}"
        )

    best_level = raw_levels[0]
    mismatches = []

    for semantic_field, (market_field, raw_field) in FIELD_PAIRS.items():
        market_value = market_watch_level.get(market_field)
        raw_value = best_level.get(raw_field)

        if market_value != raw_value:
            mismatches.append({
                "field": semantic_field,
                "marketwatch_field": market_field,
                "bestlimits_field": raw_field,
                "marketwatch_value": market_value,
                "bestlimits_value": raw_value,
            })

    if mismatches:
        raise RuntimeError(
            "Independent same-time semantic evidence mismatch for "
            f"{instrument_id}: {json.dumps(mismatches, ensure_ascii=False)}"
        )

    return {
        "instrument_id": instrument_id,
        "capture_timestamp_utc": bestlimits_capture["retrieved_at_utc"],
        "evidence_source": "TSETMC",
        "evidence_location": market_watch_url(
            bestlimits_capture["endpoint"].rsplit("/BestLimits/", 1)[0]
        ),
        "evidence_type": "TSETMC_WEB_BOARD_OBSERVATION",
        "matched_fields": ["pd", "po", "qd", "qo", "zd", "zo"],
        "marketwatch_retrieved_at_utc": None,
        "bestlimits_retrieved_at_utc": bestlimits_capture["retrieved_at_utc"],
        "delta_seconds": None,
        "observed_marketwatch_level": market_watch_level,
        "bestlimits_level_1": best_level,
        "semantic_mapping": {
            "pd": "pmd/pMeDem",
            "po": "pmo/pMeOf",
            "qd": "qmd/qTitMeDem",
            "qo": "qmo/qTitMeOf",
            "zd": "zmd/zOrdMeDem",
            "zo": "zmo/zOrdMeOf",
        },
    }


def capture_with_independent_evidence(
    instrument_id: str,
    *,
    base_url: str,
    timeout: float,
) -> tuple[dict, dict]:
    market_level, market_endpoint, market_retrieved = fetch_market_watch_level(
        instrument_id,
        base_url=base_url,
        timeout=timeout,
    )

    bestlimits_capture = capture(instrument_id, base_url, timeout)

    evidence = verify_semantic_correspondence(
        market_level,
        bestlimits_capture,
        instrument_id=instrument_id,
    )
    evidence["evidence_location"] = market_endpoint
    evidence["marketwatch_retrieved_at_utc"] = market_retrieved
    evidence["delta_seconds"] = abs(
        (
            datetime.fromisoformat(
                bestlimits_capture["retrieved_at_utc"]
            )
            - datetime.fromisoformat(market_retrieved)
        ).total_seconds()
    )

    if evidence["delta_seconds"] > 2.0:
        raise RuntimeError(
            f"Semantic evidence timing exceeded 2 seconds for {instrument_id}: "
            f"{evidence['delta_seconds']}"
        )

    return bestlimits_capture, evidence


def build_package(
    *,
    option_count: int,
    pause_seconds: float,
    timeout: float,
    base_url: str,
) -> dict:
    snapshot = build_tsetmc_snapshot(
        flow=1,
        max_instruments=max(option_count * 3, option_count),
    )
    rows = snapshot.get("rows", [])

    live_market_rows, live_market_endpoint, live_market_retrieved, live_market_sha256 = (
        fetch_market_watch_rows(
            base_url=base_url,
            timeout=timeout,
        )
    )
    live_market_ids = {
        str(item.get("insCode") or "").strip()
        for item in live_market_rows
        if isinstance(item, dict)
    }

    selected = []
    seen = set()

    for row in rows:
        identity = row.get("identity", {})
        iid = str(identity.get("instrument_id") or "").strip()
        uid = str(identity.get("underlying_id") or "").strip()

        if not iid or not uid or iid in seen:
            continue

        # The option-universe endpoint and ClosingPrice/GetMarketWatch can
        # expose different cached universes. For live semantic evidence,
        # require the selected instrument to exist in the exact MarketWatch
        # payload that will be used for independent observation.
        if iid not in live_market_ids:
            continue

        seen.add(iid)
        selected.append((iid, uid))

        if len(selected) >= option_count:
            break

    if len(selected) < option_count:
        raise RuntimeError(
            "TSETMC did not provide enough explicit option/underlying identities"
        )

    roles = {}
    for option_id, underlying_id in selected:
        roles[option_id] = ["option"]
        roles[underlying_id] = ["underlying"]

    captures = []
    semantic_evidence = []

    for round_no in range(2):
        for option_id, underlying_id in selected:
            option_capture, option_evidence = (
                capture_with_independent_evidence(
                    option_id,
                    base_url=base_url,
                    timeout=timeout,
                )
            )
            captures.append(option_capture)
            semantic_evidence.append(option_evidence)

            underlying_capture, underlying_evidence = (
                capture_with_independent_evidence(
                    underlying_id,
                    base_url=base_url,
                    timeout=timeout,
                )
            )
            captures.append(underlying_capture)
            semantic_evidence.append(underlying_evidence)

        if round_no == 0 and pause_seconds > 0:
            time.sleep(pause_seconds)

    package = {
        "schema_version": "BESTLIMITS_LIVE_EVIDENCE_PACKAGE_V1",
        "source_of_truth": "TSETMC",
        "generated_from_snapshot_sha256": snapshot.get("snapshot_sha256"),
        "instrument_roles": roles,
        "live_market_watch_selection": {
            "endpoint": live_market_endpoint,
            "retrieved_at_utc": live_market_retrieved,
            "response_sha256": live_market_sha256,
            "selected_option_instruments": [item[0] for item in selected],
            "selection_rule": "snapshot_option_identity_must_exist_in_same_live_GetMarketWatch_payload",
        },
        "captures": captures,
        "independent_semantic_evidence": semantic_evidence,
        "semantic_mapping_status": "OPEN",
        "scoring_status": "BLOCKED",
        "governance": {
            "optionschool_dependency": False,
            "semantic_translation_performed": False,
            "production_scoring_enabled": False,
        },
    }

    return package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--option-count", type=int, default=3)
    parser.add_argument("--pause-seconds", type=float, default=3.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--base-url", default="https://cdn.tsetmc.com/api")
    args = parser.parse_args()

    if args.option_count < 3:
        raise ValueError("--option-count must be at least 3")

    package = build_package(
        option_count=args.option_count,
        pause_seconds=args.pause_seconds,
        timeout=args.timeout,
        base_url=args.base_url,
    )

    result = validate_package(package)
    package["gate_result"] = result

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            package,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print(json.dumps({
        "status": "SUCCESS",
        "gate_status": result["status"],
        "capture_count": result["capture_count"],
        "option_instruments": result["option_instruments"],
        "underlying_instruments": result["underlying_instruments"],
        "semantic_evidence_count": len(
            package["independent_semantic_evidence"]
        ),
        "errors": result.get("errors", []),
        "semantic_mapping_status": "OPEN",
        "scoring_status": "BLOCKED",
        "output": str(args.output),
    }, ensure_ascii=False))

    return 0 if result["status"] in {
        "READY_FOR_REVIEW",
        "INCOMPLETE",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
