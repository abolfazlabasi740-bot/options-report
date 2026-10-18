#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live market overlay for the whole-market base-share report.

Problem: TSETMC publishes the daily closing-price HISTORY with an evening
delay, so the EOD chain can lag the current trading session by hours.
The live MarketWatch feed, however, already carries today's session state
even after the close (last price, close price, volume, value, timestamps).

This module overlays ONLY today's live quote fields onto the EOD ranking —
it never touches scores, indicators, or history. If the live feed is
unavailable or stale, the overlay is skipped and every symbol shows its
EOD values (labeled as such). No field is ever imputed.

Usage by bale_market_share_cards / bale_base_share_option_cards:
    overlay = fetch_live_overlay()          # dict instrument_id -> live fields
    apply_live_overlay(rows, overlay)       # annotate rows in place
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, time as datetime_time
from pathlib import Path
from zoneinfo import ZoneInfo

from tsetmc_adapter import TSETMCAdapter

TEHRAN = ZoneInfo("Asia/Tehran")
ROOT = Path(__file__).resolve().parent
CACHE_PATH = ROOT / "output" / "base_share" / "latest_live_market_overlay.json"

# Tehran trading days: Sat(5) Sun(6) Mon(0) Tue(1) Wed(2)
TRADING_WEEKDAYS = (5, 6, 0, 1, 2)
SESSION_OPEN = datetime_time(9, 0)
SESSION_CLOSE = datetime_time(12, 30)

# Overlay is only meaningful while it can be newer than the EOD history —
# i.e. from the 12:30 close until the daily history lands in the evening.
MAX_OVERLAY_AGE_MINUTES = 12 * 60


def _is_trading_day(now=None):
    now = now or datetime.now(TEHRAN)
    return now.weekday() in TRADING_WEEKDAYS


def session_state(now=None):
    """('PRE_OPEN' | 'OPEN' | 'CLOSED_TODAY' | 'NON_TRADING_DAY')"""
    now = now or datetime.now(TEHRAN)
    if not _is_trading_day(now):
        return "NON_TRADING_DAY"
    if now.time() < SESSION_OPEN:
        return "PRE_OPEN"
    if SESSION_OPEN <= now.time() <= SESSION_CLOSE:
        return "OPEN"
    return "CLOSED_TODAY"


def _normalize_symbol(value):
    return str(value or "").strip().replace("ي", "ی").replace("ك", "ک")


def fetch_live_overlay(adapter=None, *, force=False):
    """Fetch the live MarketWatch feed and return an overlay dict:
    {instrument_id: {live_last_price, live_close_price, live_volume,
                     live_trade_count, live_value, live_time_label,
                     live_date}} — or None if the feed cannot be used.

    Cached: after a successful fetch the overlay file is reused while fresh
    (see MAX_OVERLAY_AGE_MINUTES) so paginated clicks don't re-hit TSETMC.
    """
    now = datetime.now(TEHRAN)
    state = session_state(now)
    if state in ("NON_TRADING_DAY", "PRE_OPEN"):
        return None

    if not force:
        cached = _load_cache()
        if cached is not None:
            fetched_at = cached.get("fetched_at_tehran")
            try:
                age = now - datetime.fromisoformat(fetched_at)
                if age.total_seconds() <= MAX_OVERLAY_AGE_MINUTES * 60:
                    return cached.get("overlay") or {}
            except (TypeError, ValueError):
                pass

    adapter = adapter or TSETMCAdapter()
    universe = adapter.market_watch_universe_raw(with_best_limits=False)
    records = universe.get("records") or []
    overlay = {}
    for rec in records:
        raw = rec.get("raw") or {}
        instrument_id = str(rec.get("instrument_id") or "").strip()
        if not instrument_id:
            continue
        # Field semantics on the live feed (observed, not invented):
        #   pdv  = current/last trade price (پایانی معامله جاری)
        #   pcl  = session closing price so far (قیمت پایانی)
        #   pmo  = last price of best bid side (used when pdv==0 pre-open)
        #   qtj  = session volume   | qtc = session value
        #   ztt  = trade count      | hEven = HHMMSS market timestamp
        last_price = raw.get("pdv") or raw.get("pDrCotVal")
        close_price = raw.get("pcl") or raw.get("pClosing")
        prev_close = raw.get("py")
        heven = str(raw.get("hEven") or "").strip()
        time_label = f"{heven[-6:-4]}:{heven[-4:-2]}:{heven[-2:]}" if len(heven) >= 6 and heven.isdigit() else None
        if not any(isinstance(v, (int, float)) and v for v in (last_price, close_price, raw.get("qtj"), raw.get("qtc"))):
            continue  # nothing live to overlay
        live = {
            "live_last_price": last_price if isinstance(last_price, (int, float)) and last_price else None,
            "live_close_price": close_price if isinstance(close_price, (int, float)) and close_price else None,
            "live_prev_close": prev_close if isinstance(prev_close, (int, float)) else None,
            "live_volume": raw.get("qtj") if isinstance(raw.get("qtj"), (int, float)) else None,
            "live_value": raw.get("qtc") if isinstance(raw.get("qtc"), (int, float)) else None,
            "live_trade_count": raw.get("ztt") if isinstance(raw.get("ztt"), (int, float)) else None,
            "live_time": time_label,
            "live_symbol": _normalize_symbol(raw.get("lva") or rec.get("symbol")),
        }
        # today's change vs previous close, when both are real numbers
        if isinstance(live["live_last_price"], (int, float)) and isinstance(prev_close, (int, float)) and prev_close:
            live["live_change_pct"] = round((live["live_last_price"] - prev_close) / prev_close * 100, 2)
        overlay[instrument_id] = live

    payload = {
        "source": "TSETMC",
        "source_endpoint": universe.get("endpoint"),
        "retrieved_at": universe.get("retrieved_at"),
        "snapshot_sha256": universe.get("snapshot_sha256"),
        "fetched_at_tehran": now.isoformat(),
        "session_state": state,
        "overlay_record_count": len(overlay),
        "overlay": overlay,
    }
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    except OSError:
        pass  # cache write failure must never break the overlay
    return overlay


def _load_cache():
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if payload.get("source") == "TSETMC" and isinstance(payload.get("overlay"), dict):
            return payload
    except (OSError, ValueError, TypeError):
        pass
    return None


def apply_live_overlay(rows, overlay):
    """Attach live_* fields to report rows by instrument_id (in place).
    Rows without a live match keep their EOD values and get
    live_status='EOD_ONLY'; matched rows get live_status='LIVE_TODAY'.
    Returns the same rows list for convenience."""
    if not overlay:
        return rows
    for row in rows:
        instrument_id = str(row.get("instrument_id") or "").strip()
        live = overlay.get(instrument_id)
        if live is None and row.get("symbol"):
            # symbol fallback only when the row lacks a usable id
            needle = _normalize_symbol(row.get("symbol"))
            for candidate in overlay.values():
                if candidate.get("live_symbol") == needle:
                    live = candidate
                    break
        if live is not None:
            row.update(live)
            row["live_status"] = "LIVE_TODAY"
        else:
            row["live_status"] = "EOD_ONLY"
    return rows
