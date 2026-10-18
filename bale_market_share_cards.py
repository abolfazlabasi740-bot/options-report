#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paginated Bale cards for the whole-market base-share ranking."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, date, time as datetime_time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from persian_date_utils import gregorian_to_jalali
from live_market_overlay import apply_live_overlay, fetch_live_overlay, session_state

ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "output" / "base_share" / "latest_whole_market_opportunity_report.json"
CATALOG_PATH = ROOT / "output" / "base_share" / "market_watch_identity_catalog.json"
PAGE_SIZE = 10
TEHRAN = ZoneInfo("Asia/Tehran")
# EOD data changes once per trading day; rebuilding more often is wasted work.
MAX_REPORT_AGE = timedelta(hours=6)

TITLE = "\U0001F4CA رتبه‌بندی سهم‌های بازار"
HOME = "\U0001F3E0 منوی اصلی"


def _load_report():
    if not REPORT_PATH.exists():
        return None
    try:
        payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        if payload.get("source_of_truth") != "TSETMC" or not isinstance(payload.get("rows"), list):
            return None
        return payload
    except (OSError, ValueError, TypeError):
        return None


def _report_is_fresh(payload):
    """EOD freshness: latest_history_date must cover the most recent trading
    day whose session has closed, and the report must not be ancient."""
    now = datetime.now(TEHRAN)
    # After 13:30 Tehran the current day's EOD should be in; before that,
    # the previous trading day is the freshest possible data.
    cutoff_day = now.date() if now.time() >= datetime_time(13, 30) else now.date() - timedelta(days=1)
    last_trading = _previous_trading_day(cutoff_day)
    try:
        data_date = date(
            int(str(payload.get("latest_history_date"))[:4]),
            int(str(payload.get("latest_history_date"))[4:6]),
            int(str(payload.get("latest_history_date"))[6:8]),
        )
    except (TypeError, ValueError):
        return False
    if data_date < last_trading:
        return False
    try:
        generated = datetime.fromisoformat(str(payload.get("generated_at")).replace("Z", "+00:00"))
        if generated.tzinfo is None:
            generated = generated.astimezone()
        return datetime.now(generated.tzinfo) - generated <= MAX_REPORT_AGE
    except (TypeError, ValueError, OverflowError):
        return False


def _previous_trading_day(day):
    """Walk back to the last Sat–Wed (Tehran trading days) on or before `day`."""
    while day.weekday() not in (5, 6, 0, 1, 2):  # Sat=5, Sun=6, Mon=0, Tue=1, Wed=2
        day -= timedelta(days=1)
    return day


def _run_builder(script_name):
    completed = subprocess.run(
        [sys.executable, str(ROOT / script_name)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        check=False,
    )
    if completed.returncode != 0:
        tail = (completed.stdout or "").strip()[-1200:]
        raise RuntimeError(f"WHOLE_MARKET_REPORT_FAILED:{script_name}:{tail}")


def ensure_report():
    payload = _load_report()
    if payload is not None and _report_is_fresh(payload):
        return payload
    if not CATALOG_PATH.exists():
        _run_builder("market_watch_identity_catalog.py")
    _run_builder("base_share_whole_market_first_pass.py")
    payload = _load_report()
    if payload is None:
        raise RuntimeError("WHOLE_MARKET_REPORT_MISSING_AFTER_BUILD")
    return payload


def _fmt(value, suffix=""):
    if value is None or value == "":
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.2f}{suffix}"
    return str(value)


def _header_lines(payload):
    """Persian date + clock header per user spec: Jalali date of the data,
    generation time, and market-session status."""
    now = datetime.now(TEHRAN)
    hist = str(payload.get("latest_history_date") or "")
    hist_jalali = payload.get("latest_history_date_jalali") or gregorian_to_jalali(hist) or "—"
    try:
        generated = datetime.fromisoformat(str(payload.get("generated_at")).replace("Z", "+00:00"))
        generated = generated.astimezone(TEHRAN)
        generated_label = generated.strftime("%H:%M")
    except (TypeError, ValueError, OverflowError):
        generated_label = "—"
    state = session_state(now)
    if state == "OPEN":
        session_label = "🟢 در ساعت معاملات (۹:۰۰–۱۲:۳۰) — قیمت‌ها لحظه‌ای از فید زنده"
    elif state == "CLOSED_TODAY":
        session_label = "🟠 بستهٔ امروز — قیمت‌های امروز از فید پایانی ۱۲:۳۰ (تاریخچه EOD هنوز منتشر نشده)"
    elif state == "PRE_OPEN":
        session_label = "🕒 قبل از باز شدن بازار — داده پایان روز قبل (EOD)"
    else:
        session_label = "🔒 روز غیرمعاملاتی — داده پایان روز (EOD)"
    return [
        f"\U0001F4C5 تاریخ داده: {hist_jalali}",
        f"\U0001F552 زمان بازسازی گزارش: {generated_label}",
        f"{session_label}",
    ]


def _factor_bits(row):
    """Enriched per-symbol evidence: breakout, range position, ATR, value
    expansion. Missing values render as '—' (never invented)."""
    early = row.get("early_move") or {}
    bits = []
    if early.get("breakout_above_prior_20_high") is True:
        bits.append("شکست سقف ۲۰ج")
    rp = row.get("range_position_20")
    if isinstance(rp, (int, float)):
        bits.append(f"موقعیت کانال {rp * 100:.0f}%")
    atr = row.get("atr_14_pct")
    if isinstance(atr, (int, float)):
        bits.append(f"ATR {atr:.1f}%")
    valr = row.get("value_ratio_5_to_20")
    if isinstance(valr, (int, float)):
        bits.append(f"ارزش ۵/۲۰ {valr:.2f}×")
    prelock = (early.get("pre_lock_sequence") or {}).get("state")
    if prelock in ("EARLY", "DEVELOPING"):
        bits.append(f"پیش‌قفل:{prelock}")
    return " | ".join(bits) if bits else "—"


def ranked_rows(payload):
    """One canonical order shared by market and option-enabled reports."""
    rows = list(payload.get("rows") or [])
    rows.sort(key=lambda row: (
        row.get("final_score") is None,
        -(row.get("final_score") or 0.0),
        -(row.get("evidence_coverage_pct") or 0.0),
        str(row.get("symbol") or ""),
    ))
    return rows


def render_ranked_rows(payload, rows, page=0, *, title=TITLE,
                       callback_prefix="market_shares_page", extra_lines=()):
    total_pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(int(page), total_pages - 1))
    subset = rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    lines = [
        title,
        *_header_lines(payload),
        f"منبع: TSETMC | تعداد کل: {len(rows)} سهم",
        f"صفحه {page + 1}/{total_pages} | هر صفحه {PAGE_SIZE} سهم",
        *extra_lines,
        "━" * 24,
    ]
    for index, row in enumerate(subset, page * PAGE_SIZE + 1):
        warnings = ", ".join(row.get("warnings") or []) or "-"
        market_rank = f" | market_rank={row['market_rank']}" if "market_rank" in row else ""
        correction = row.get("correction_state") or "—"
        # Live overlay: today's price from the live feed when it is newer
        # than the EOD history; otherwise show the EOD price, labeled.
        if row.get("live_status") == "LIVE_TODAY":
            price = row.get("live_last_price") or row.get("live_close_price")
            live_parts = [f"قیمت امروز: {_fmt(price)}"]
            change = row.get("live_change_pct")
            if change is not None:
                arrow = "\U0001F7E2" if change >= 0 else "\U0001F534"
                live_parts.append(f"{arrow} {change:+.2f}%")
            if row.get("live_time"):
                live_parts.append(f"ساعت {str(row['live_time'])[:5]}")
            price_line = f"   {' | '.join(live_parts)} (زنده)"
        else:
            price_line = f"   قیمت EOD: {_fmt(row.get('last_price') or row.get('last_close'))}"
        lines.extend([
            f"{index}. {row.get('symbol') or 'N/A'} | score={_fmt(row.get('final_score'))} | class={row.get('classification') or 'N/A'}{market_rank}",
            price_line,
            f"   trend={row.get('trend_state') or '—'} | اصلاح={correction} | RSI={_fmt(row.get('rsi_14'))} | coverage={_fmt(row.get('evidence_coverage_pct'), '%')}",
            f"   return5/20={_fmt(row.get('return_5_sessions_pct'), '%')}/{_fmt(row.get('return_20_sessions_pct'), '%')} | حجم ۵/۲۰={_fmt(row.get('volume_ratio_5_to_20'))}× | MACD%={_fmt(row.get('macd_pct'), '%')}",
            f"   {_factor_bits(row)}",
            f"   warnings={warnings}",
            "─" * 24,
        ])
    if not subset:
        lines.append("داده‌ای برای نمایش وجود ندارد.")
    lines.append("این رتبه‌بندی توصیفی است و سیگنال خرید/فروش نییست.")
    navigation = []
    if page > 0:
        navigation.append({"text": "◀️ قبلی", "callback_data": f"{callback_prefix}:{page - 1}"})
    if page < total_pages - 1:
        navigation.append({"text": "بعدی ▶️", "callback_data": f"{callback_prefix}:{page + 1}"})
    keyboard = [navigation] if navigation else []
    keyboard.append([{"text": HOME, "callback_data": "main_menu"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}, len(rows), page, total_pages


def render_page(page=0):
    payload = ensure_report() if int(page) == 0 else (_load_report() or ensure_report())
    rows = ranked_rows(payload)
    # During the session (and until the evening EOD lands) overlay today's
    # live prices from the market-watch feed onto the EOD ranking.
    overlay = None
    try:
        overlay = fetch_live_overlay()
    except Exception:
        overlay = None  # live feed failure must never block the report
    if overlay:
        apply_live_overlay(rows, overlay)
    return render_ranked_rows(payload, rows, page)
