#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a real TSETMC-only BestLimits evidence package.

This runner is deliberately fail-closed:
- discovers option/underlying identities from the live TSETMC option Market-Watch;
- captures BestLimits twice for each unique selected instrument;
- captures independent same-time Market-Watch BestLimits observations;
- verifies the six candidate field correspondences against both live sources;
- preserves raw payloads and hashes;
- never enables scoring or ranking.

RCA-driven design:
- GetMarketWatch is fetched once per evidence round.
- All unique BestLimits requests for that round run concurrently.
- This keeps each direct BestLimits capture close to the same MarketWatch
  timestamp and avoids the previous sequential >2-second timing failure.
- Underlying IDs are deduplicated so the same instrument is not captured
  repeatedly just because multiple options share it.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from urllib.error import HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from bestlimits_evidence_gate import validate_package
from live_capture_harness import capture
from tsetmc_first_source import build_tsetmc_snapshot


MARKET_WATCH_PATH = "/ClosingPrice/GetMarketWatch"
USER_AGENT = "OptimusAI-V4.1-BestLimits-LiveEvidence/1.1"
RETRYABLE_HTTP_STATUS = {502, 503, 504}
MAX_TRANSIENT_RETRIES = 2

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

    last_error = None
    for attempt in range(MAX_TRANSIENT_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                status = getattr(response, "status", 200)
            break
        except HTTPError as exc:
            last_error = exc
            if exc.code not in RETRYABLE_HTTP_STATUS or attempt >= MAX_TRANSIENT_RETRIES:
                raise
            time.sleep(0.75 * (attempt + 1))
    else:
        raise RuntimeError(f"MarketWatch request failed: {last_error}") from last_error

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
        "evidence_location": "",
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
    market_level: dict,
    market_endpoint: str,
    market_retrieved: str,
    base_url: str,
    timeout: float,
) -> tuple[dict, dict]:
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


def capture_round_in_parallel(
    instrument_ids: list[str],
    market_by_id: dict[str, dict],
    *,
    market_endpoint: str,
    market_retrieved: str,
    base_url: str,
    timeout: float,
) -> tuple[list[dict], list[dict]]:
    missing = [instrument_id for instrument_id in instrument_ids
               if instrument_id not in market_by_id]
    if missing:
        raise RuntimeError(
            "Live MarketWatch instruments disappeared from round payload: "
            + ", ".join(missing)
        )

    missing_levels = [
        instrument_id
        for instrument_id in instrument_ids
        if not isinstance(market_by_id[instrument_id].get("blDs"), list)
        or not market_by_id[instrument_id].get("blDs")
    ]
    if missing_levels:
        raise RuntimeError(
            "MarketWatch blDs missing for: " + ", ".join(missing_levels)
        )

    max_workers = min(4, len(instrument_ids))
    captures_by_id = {}
    evidence_by_id = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                capture_with_independent_evidence,
                instrument_id,
                market_level=market_by_id[instrument_id]["blDs"][0],
                market_endpoint=market_endpoint,
                market_retrieved=market_retrieved,
                base_url=base_url,
                timeout=timeout,
            ): instrument_id
            for instrument_id in instrument_ids
        }

        for future in as_completed(futures):
            instrument_id = futures[future]
            instrument_capture, instrument_evidence = future.result()
            captures_by_id[instrument_id] = instrument_capture
            evidence_by_id[instrument_id] = instrument_evidence

    captures = [captures_by_id[instrument_id] for instrument_id in instrument_ids]
    evidence = [evidence_by_id[instrument_id] for instrument_id in instrument_ids]
    return captures, evidence


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
    # Persist the canonical TSETMC snapshot before BestLimits evidence checks.
    # A later semantic mismatch must never erase the captured snapshot.
    snapshot_output = Path("output/tsetmc_first/live_market_open_snapshot.json")
    snapshot_output.parent.mkdir(parents=True, exist_ok=True)
    snapshot_output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    rows = snapshot.get("rows", [])

    (
        live_market_rows,
        live_market_endpoint,
        live_market_retrieved,
        live_market_sha256,
    ) = fetch_market_watch_rows(
        base_url=base_url,
        timeout=timeout,
    )
    live_market_ids = {
        str(item.get("insCode") or "").strip()
        for item in live_market_rows
        if isinstance(item, dict)
    }

    selected = []
    seen_options = set()

    for row in rows:
        identity = row.get("identity", {})
        option_id = str(identity.get("instrument_id") or "").strip()
        underlying_id = str(identity.get("underlying_id") or "").strip()

        if (
            not option_id
            or not underlying_id
            or option_id in seen_options
        ):
            continue

        if option_id not in live_market_ids:
            continue

        seen_options.add(option_id)
        selected.append((option_id, underlying_id))

        if len(selected) >= option_count:
            break

    if len(selected) < option_count:
        raise RuntimeError(
            "TSETMC did not provide enough explicit option/underlying identities"
        )

    roles = {}
    for option_id, underlying_id in selected:
        roles.setdefault(option_id, [])
        if "option" not in roles[option_id]:
            roles[option_id].append("option")
        roles.setdefault(underlying_id, [])
        if "underlying" not in roles[underlying_id]:
            roles[underlying_id].append("underlying")

    # Preserve first-seen order while deduplicating shared underlyings.
    instrument_ids = list(roles.keys())

    captures = []
    semantic_evidence = []

    for round_no in range(2):
        (
            market_rows,
            market_endpoint,
            market_retrieved,
            market_sha256,
        ) = fetch_market_watch_rows(
            base_url=base_url,
            timeout=timeout,
        )
        market_by_id = {
            str(item.get("insCode") or "").strip(): item
            for item in market_rows
            if isinstance(item, dict)
        }

        round_captures, round_evidence = capture_round_in_parallel(
            instrument_ids,
            market_by_id,
            market_endpoint=market_endpoint,
            market_retrieved=market_retrieved,
            base_url=base_url,
            timeout=timeout,
        )
        captures.extend(round_captures)
        semantic_evidence.extend(round_evidence)

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
            "selection_rule": (
                "snapshot_option_identity_must_exist_in_same_live_"
                "GetMarketWatch_payload"
            ),
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

    try:
        package = build_package(
            option_count=args.option_count,
            pause_seconds=args.pause_seconds,
            timeout=args.timeout,
            base_url=args.base_url,
        )
        result = validate_package(package)
    except Exception as exc:
        snapshot_path = Path("output/tsetmc_first/live_market_open_snapshot.json")
        package = {
            "schema_version": "BESTLIMITS_LIVE_EVIDENCE_PACKAGE_V1",
            "source_of_truth": "TSETMC",
            "run_status": "FAILED_DURING_BESTLIMITS_EVIDENCE",
            "snapshot_persisted": snapshot_path.exists(),
            "snapshot_path": str(snapshot_path),
            "independent_semantic_evidence": [],
            "error_type": type(exc).__name__,
            "error": str(exc),
            "semantic_mapping_status": "FROZEN",
            "scoring_status": "BLOCKED",
            "governance": {
                "optionschool_dependency": False,
                "production_scoring_enabled": False,
            },
        }
        result = {
            "status": "INCOMPLETE",
            "capture_count": 0,
            "option_instruments": 0,
            "underlying_instruments": 0,
            "errors": [f"{type(exc).__name__}:{exc}"],
            "mapping_freeze": "BLOCKED",
            "scoring": "BLOCKED",
        }
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
            package.get("independent_semantic_evidence", [])
        ),
        "errors": result.get("errors", []),
        "semantic_mapping_status": package.get("semantic_mapping_status", "BLOCKED"),
        "scoring_status": "BLOCKED",
        "output": str(args.output),
    }, ensure_ascii=False))

    return 0 if result["status"] in {
        "READY_FOR_REVIEW",
        "INCOMPLETE",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
