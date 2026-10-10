#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filter the existing whole-market ranking, never rescore option underlyings."""
from __future__ import annotations

import json
from pathlib import Path

import bale_market_share_cards as market
from tsetmc_first_source import build_tsetmc_snapshot

ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "output" / "base_share" / "latest_option_enabled_market_report.json"
TITLE = "\U0001F4CC \u0633\u0647\u0645\u200c\u0647\u0627\u06cc \u062f\u0627\u0631\u0627\u06cc \u0622\u067e\u0634\u0646"


def _symbol(value):
    return str(value or "").strip().replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")


def filter_market_rows(base, snapshot):
    if snapshot.get("source_of_truth") != "TSETMC":
        raise RuntimeError("OPTION_SNAPSHOT_SOURCE_NOT_TSETMC")
    if not isinstance(snapshot.get("rows"), list):
        raise RuntimeError("OPTION_SNAPSHOT_ROWS_INVALID")
    ids, symbols, symbols_without_id = set(), set(), set()
    for row in snapshot["rows"]:
        identity = row.get("identity") or {}
        underlying_id = str(identity.get("underlying_id") or "").strip()
        symbol = _symbol(identity.get("underlying_symbol"))
        if underlying_id:
            ids.add(underlying_id)
        if symbol:
            symbols.add(symbol)
            if not underlying_id:
                symbols_without_id.add(symbol)
    rows = []
    for rank, row in enumerate(market.ranked_rows(base), 1):
        instrument_id = str(row.get("instrument_id") or "").strip()
        symbol = _symbol(row.get("symbol"))
        # Prefer explicit TSETMC identity, falling back to a normalized symbol
        # only when one side does not supply its instrument ID.
        if instrument_id:
            matches = instrument_id in ids or bool(symbol and symbol in symbols_without_id)
        else:
            matches = bool(symbol and symbol in symbols)
        if matches:
            rows.append({**row, "market_rank": rank})
    return rows


def _build_report():
    # Reuse the exact market report the user saw, even if it has aged. Only
    # the market button refreshes scores; this button filters that artifact.
    base = market.ensure_report()
    snapshot = build_tsetmc_snapshot()
    payload = {
        "source_of_truth": "TSETMC",
        "generated_at": base.get("generated_at"),
        "latest_history_date": base.get("latest_history_date"),
        "market_row_count": len(base["rows"]),
        "option_snapshot_generated_at": snapshot.get("generated_at"),
        "option_snapshot_sha256": snapshot.get("snapshot_sha256"),
        "data_mode": snapshot.get("data_mode"),
        "rows": filter_market_rows(base, snapshot),
    }
    # Freeze the filtered list so next-page clicks cannot switch source data.
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(REPORT_PATH)
    return payload


def _load_report():
    try:
        payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        if payload.get("source_of_truth") == "TSETMC" and isinstance(payload.get("rows"), list):
            return payload
    except (OSError, ValueError, TypeError):
        pass
    return None


def render_page(page=0, *, refresh=False):
    payload = _build_report() if refresh else (_load_report() or _build_report())
    return market.render_ranked_rows(
        payload, payload["rows"], page, title=TITLE, callback_prefix="option_shares_page",
        extra_lines=(
            "\u062a\u0631\u062a\u06cc\u0628 \u0648 \u0627\u0645\u062a\u06cc\u0627\u0632: \u0628\u062f\u0648\u0646 \u062a\u063a\u06cc\u06cc\u0631 \u0627\u0632 \u06af\u0632\u0627\u0631\u0634 \u06a9\u0644 \u0628\u0627\u0632\u0627\u0631",
            f"\u0632\u0645\u0627\u0646 \u06af\u0632\u0627\u0631\u0634 \u0628\u0627\u0632\u0627\u0631: {payload.get('generated_at') or 'N/A'}",
            f"\u0641\u0647\u0631\u0633\u062a \u0622\u067e\u0634\u0646: {payload.get('option_snapshot_generated_at') or 'N/A'} | {payload.get('data_mode') or 'N/A'}",
        ),
    )
