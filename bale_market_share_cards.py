#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paginated Bale cards for the whole-market base-share ranking."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "output" / "base_share" / "latest_whole_market_opportunity_report.json"
CATALOG_PATH = ROOT / "output" / "base_share" / "market_watch_identity_catalog.json"
PAGE_SIZE = 10
MAX_REPORT_AGE = timedelta(minutes=15)

TITLE = "\U0001F4CA \u0631\u062a\u0628\u0647\u200c\u0628\u0646\u062f\u06cc \u0633\u0647\u0645\u200c\u0647\u0627\u06cc \u0628\u0627\u0632\u0627\u0631"
HOME = "\U0001F3E0 \u0645\u0646\u0648\u06cc \u0627\u0635\u0644\u06cc"


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
    try:
        generated = datetime.fromisoformat(str(payload.get("generated_at")).replace("Z", "+00:00"))
        if generated.tzinfo is None:
            generated = generated.astimezone()
        return datetime.now(generated.tzinfo) - generated <= MAX_REPORT_AGE
    except (TypeError, ValueError, OverflowError):
        return False


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
        return "N/A"
    if isinstance(value, (int, float)):
        return f"{value:.2f}{suffix}"
    return str(value)


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
        f"\u0645\u0646\u0628\u0639: TSETMC | \u062a\u0639\u062f\u0627\u062f \u06a9\u0644: {len(rows)} \u0633\u0647\u0645",
        f"\u0635\u0641\u062d\u0647 {page + 1}/{total_pages} | \u0647\u0631 \u0635\u0641\u062d\u0647 {PAGE_SIZE} \u0633\u0647\u0645",
        f"\u0622\u062e\u0631\u06cc\u0646 \u062f\u0627\u062f\u0647: {payload.get('latest_history_date') or 'N/A'}",
        *extra_lines,
        "\u2501" * 24,
    ]
    for index, row in enumerate(subset, page * PAGE_SIZE + 1):
        warnings = ", ".join(row.get("warnings") or []) or "-"
        market_rank = f" | market_rank={row['market_rank']}" if "market_rank" in row else ""
        lines.extend([
            f"{index}. {row.get('symbol') or 'N/A'} | score={_fmt(row.get('final_score'))} | class={row.get('classification') or 'N/A'}{market_rank}",
            f"   trend={row.get('trend_state') or 'N/A'} | RSI={_fmt(row.get('rsi_14'))} | coverage={_fmt(row.get('evidence_coverage_pct'), '%')}",
            f"   return5/20={_fmt(row.get('return_5_sessions_pct'), '%')}/{_fmt(row.get('return_20_sessions_pct'), '%')} | volume5/20={_fmt(row.get('volume_ratio_5_to_20'))}",
            f"   warnings={warnings}",
            "\u2500" * 24,
        ])
    if not subset:
        lines.append("\u062f\u0627\u062f\u0647\u200c\u0627\u06cc \u0628\u0631\u0627\u06cc \u0646\u0645\u0627\u06cc\u0634 \u0648\u062c\u0648\u062f \u0646\u062f\u0627\u0631\u062f.")
    lines.append("\u0627\u06cc\u0646 \u0631\u062a\u0628\u0647\u200c\u0628\u0646\u062f\u06cc \u062a\u0648\u0635\u06cc\u0641\u06cc \u0627\u0633\u062a \u0648 \u0633\u06cc\u06af\u0646\u0627\u0644 \u062e\u0631\u06cc\u062f/\u0641\u0631\u0648\u0634 \u0646\u06cc\u0633\u062a.")
    navigation = []
    if page > 0:
        navigation.append({"text": "\u25c0\ufe0f \u0642\u0628\u0644\u06cc", "callback_data": f"{callback_prefix}:{page - 1}"})
    if page < total_pages - 1:
        navigation.append({"text": "\u0628\u0639\u062f\u06cc \u25b6\ufe0f", "callback_data": f"{callback_prefix}:{page + 1}"})
    keyboard = [navigation] if navigation else []
    keyboard.append([{"text": HOME, "callback_data": "main_menu"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}, len(rows), page, total_pages


def render_page(page=0):
    payload = ensure_report() if int(page) == 0 else (_load_report() or ensure_report())
    return render_ranked_rows(payload, ranked_rows(payload), page)
