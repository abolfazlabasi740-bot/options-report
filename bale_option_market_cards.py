#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paginated TSETMC option-market cards using the project's six-block ranker."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from tsetmc_first_source import build_tsetmc_snapshot
from tsetmc_scoring_engine import BLOCK_WEIGHTS, build_evidence_ranking

ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "output" / "tsetmc_first" / "latest_option_market_ranking.json"
PAGE_SIZE = 10
TITLE = "\U0001F4C8 \u0628\u0627\u0632\u0627\u0631 \u0622\u067E\u0634\u0646"
HOME = "\U0001F3E0 \u0645\u0646\u0648\u06cc \u0627\u0635\u0644\u06cc"

# Stable user-facing order. The score is the sixth-block TSETMC score; no
# Excel/OptionSchool value is used to recalculate or reorder these rows.
OPTION_COLUMNS = (
    "\u0646\u0645\u0627\u062f",
    "\u0646\u0648\u0639 \u0642\u0631\u0627\u0631\u062f\u0627\u062f",
    "\u0633\u0647\u0645 \u067e\u0627\u06cc\u0647",
    "\u0627\u0639\u0645\u0627\u0644",
    "\u0622\u062e\u0631\u06cc\u0646 \u0642\u06cc\u0645\u062a",
    "\u0642\u06cc\u0645\u062a \u0633\u0647\u0645 \u067e\u0627\u06cc\u0647",
    "\u0633\u0631\u0628\u0647\u200c\u0633\u0631",
    "\u0641\u0627\u0635\u0644\u0647 \u0633\u0631\u0628\u0647\u200c\u0633\u0631",
    "\u062a\u0627\u0631\u06cc\u062e \u0633\u0631\u0631\u0633\u06cc\u062f",
    "\u0631\u0648\u0632\u0647\u0627\u06cc \u0628\u0627\u0642\u06cc\u0645\u0627\u0646\u062f\u0647",
    "\u0627\u0645\u062a\u06cc\u0627\u0632 \u0634\u0634\u200c\u0628\u0644\u0648\u06a9",
)

CANONICAL = {
    "symbol": "\u0646\u0645\u0627\u062f",
    "strike": "\u0642\u06cc\u0645\u062a \u0627\u0639\u0645\u0627\u0644",
    "underlying": "\u0642\u06cc\u0645\u062a \u0633\u0647\u0645 \u067e\u0627\u06cc\u0647",
    "expiry": "\u062a\u0627\u0631\u06cc\u062e \u0633\u0631\u0631\u0633\u06cc\u062f",
    "days": "\u0631\u0648\u0632\u0647\u0627\u06cc \u062a\u0642\u0648\u06cc\u0645\u06cc",
    "last": "\u0622\u062e\u0631\u06cc\u0646 \u0642\u06cc\u0645\u062a",
    "close": "\u0642\u06cc\u0645\u062a \u067e\u0627\u06cc\u0627\u0646\u06cc",
}


def _num(value):
    try:
        if value in (None, ""):
            return None
        value = float(value)
        return value if value == value and abs(value) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _text(value):
    return str(value).strip() if value not in (None, "") else "داده موجود نیست"


def _fmt(value, suffix=""):
    value = _num(value)
    if value is None:
        return "داده موجود نیست"
    return f"{value:.2f}{suffix}".replace(".00", "")


def _expiry_distance(expiry, snapshot_generated_at):
    if not expiry:
        return None
    try:
        expiry_date = datetime.strptime(str(expiry)[:8], "%Y%m%d").date()
        basis = datetime.fromisoformat(str(snapshot_generated_at).replace("Z", "+00:00")).date()
        return max(0, (expiry_date - basis).days)
    except (TypeError, ValueError):
        return None


def _row_to_display(source, ranked):
    canonical = source.get("canonical") or {}
    identity = source.get("identity") or {}
    features = ranked.get("features") or {}
    contract_type = str(identity.get("contract_type") or "").upper() or "داده موجود نیست"
    strike = _num(canonical.get(CANONICAL["strike"]))
    underlying = _num(canonical.get(CANONICAL["underlying"]))
    premium = _num(canonical.get(CANONICAL["last"]))
    if contract_type == "CALL" and strike is not None and premium is not None:
        breakeven = strike + premium
    elif contract_type == "PUT" and strike is not None and premium is not None:
        breakeven = strike - premium
    else:
        breakeven = None
    distance = features.get("breakeven_distance")
    return {
        "نماد": _text(canonical.get(CANONICAL["symbol"])),
        "نوع قرارداد": contract_type,
        "سهم پایه": _text(identity.get("underlying_symbol")),
        "اعمال": strike,
        "آخرین قیمت": premium,
        "قیمت سهم پایه": underlying,
        "سربه‌سر": breakeven,
        "فاصله سربه‌سر": _num(distance) * 100 if _num(distance) is not None else None,
        "تاریخ سررسید": _text(canonical.get(CANONICAL["expiry"])),
        "روزهای باقی‌مانده": _expiry_distance(canonical.get(CANONICAL["expiry"]), source.get("snapshot_generated_at")),
        "امتیاز شش‌بلوک": ranked.get("score"),
        "block_scores": ranked.get("block_scores") or {},
        "market_volume": canonical.get("حجم معاملات"),
        "market_value": canonical.get("ارزش معاملات"),
        "rank": ranked.get("rank"),
    }


def rank_snapshot(snapshot):
    if snapshot.get("source_of_truth") != "TSETMC":
        raise RuntimeError("OPTION_MARKET_SOURCE_NOT_TSETMC")
    raw_rows = [
        row for row in (snapshot.get("rows") or [])
        if isinstance(row, dict)
        and str((row.get("identity") or {}).get("contract_type") or "").upper() in {"CALL", "PUT"}
    ]
    ranking = build_evidence_ranking(raw_rows)
    by_id = {
        str((row.get("identity") or {}).get("instrument_id") or ""): row
        for row in raw_rows
    }
    display = []
    for item in ranking.get("ranking_rows") or []:
        source = by_id.get(str(item.get("instrument_id") or ""))
        if source is None:
            continue
        source = dict(source)
        source["snapshot_generated_at"] = snapshot.get("generated_at")
        display.append(_row_to_display(source, item))
    return {
        "status": ranking.get("status"),
        "mode": ranking.get("mode"),
        "source_of_truth": "TSETMC",
        "generated_at": snapshot.get("generated_at"),
        "data_mode": snapshot.get("data_mode"),
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "supported_blocks": ranking.get("supported_blocks") or [],
        "block_weights": BLOCK_WEIGHTS,
        "columns": list(OPTION_COLUMNS),
        "rows": display,
    }


def _load_report():
    try:
        payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        if payload.get("source_of_truth") == "TSETMC" and isinstance(payload.get("rows"), list):
            return payload
    except (OSError, ValueError, TypeError):
        pass
    return None


def _build_report():
    payload = rank_snapshot(build_tsetmc_snapshot())
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(REPORT_PATH)
    return payload


def _norm_symbol(value):
    """Normalize Arabic ي/ك to Persian ی/ک so underlying matching is stable."""
    return str(value or "").strip().replace("ي", "ی").replace("ك", "ک")


def render_symbol_options(symbol, page=0, *, refresh=False):
    """Six-block-ranked option contracts for a single underlying symbol.

    Reuses the option-market six-block ranking artifact and filters it to the
    selected underlying, preserving the global rank order. No Excel/OptionSchool
    value is used to recalculate or reorder these rows. This is the drill-down
    reached from the "نمادها" glass button: tap a symbol -> its options ranked
    by the same six-block TSETMC evidence ranker as the option-market button.
    """
    payload = _build_report() if refresh else (_load_report() or _build_report())
    target = _norm_symbol(symbol)
    rows = [
        row for row in (payload.get("rows") or [])
        if _norm_symbol(row.get("سهم پایه")) == target
    ]
    total_pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(int(page), total_pages - 1))
    subset = rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    block_order = " | ".join(f"{name}={weight:g}%" for name, weight in BLOCK_WEIGHTS.items())
    lines = [
        f"\U0001F50E آپشن‌های {symbol or target or 'نامشخص'}",
        "مبنای رتبه‌بندی: TSETMC six-block",
        f"ترتیب بلوک‌ها: {block_order}",
        f"تعداد: {len(rows)} قرارداد | صفحه {page + 1}/{total_pages} | هر صفحه {PAGE_SIZE}",
        "━" * 24,
    ]
    for index, row in enumerate(subset, page * PAGE_SIZE + 1):
        values = [
            row.get("نماد"), row.get("نوع قرارداد"), row.get("سهم پایه"),
            _fmt(row.get("اعمال")), _fmt(row.get("آخرین قیمت")), _fmt(row.get("قیمت سهم پایه")),
            _fmt(row.get("سربه‌سر")), _fmt(row.get("فاصله سربه‌سر"), "%"),
            row.get("تاریخ سررسید"), _fmt(row.get("روزهای باقی‌مانده")), _fmt(row.get("امتیاز شش‌بلوک")),
        ]
        block_scores = row.get("block_scores") or {}
        block_text = " | ".join(
            f"{name}={_fmt(block_scores.get(name))}" for name in BLOCK_WEIGHTS
        )
        lines.extend([
            f"{index}. " + " | ".join(str(value) for value in values),
            f"   شش‌بلوک: {block_text}",
            "─" * 24,
        ])
    if not subset:
        lines.append("قرارداد آپشن قابل رتبه‌بندی برای این نماد در Snapshot فعلی پیدا نشد.")
    lines.append("این خروجی رتبه‌بندی توصیفی است و سیگنال خرید/فروش نیست.")
    navigation = []
    if page > 0:
        navigation.append({"text": "◀️ قبلی", "callback_data": f"symbolopt:{target}:{page - 1}"})
    if page < total_pages - 1:
        navigation.append({"text": "بعدی ▶️", "callback_data": f"symbolopt:{target}:{page + 1}"})
    keyboard = [navigation] if navigation else []
    keyboard.append([{"text": "📊 اکسل این نماد", "callback_data": f"option_excel:{target}"}])
    keyboard.append([{"text": "🔙 نمادها", "callback_data": "symbols"}])
    keyboard.append([{"text": HOME, "callback_data": "main_menu"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}, len(rows), page, total_pages


def render_page(page=0, *, refresh=False):
    payload = _build_report() if refresh else (_load_report() or _build_report())
    rows = payload.get("rows") or []
    total_pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(int(page), total_pages - 1))
    subset = rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    block_order = " | ".join(f"{name}={weight:g}%" for name, weight in BLOCK_WEIGHTS.items())
    lines = [
        TITLE,
        "\u0645\u0628\u0646\u0627\u06cc \u0631\u062a\u0628\u0647\u200c\u0628\u0646\u062f\u06cc: TSETMC six-block",
        f"\u062a\u0631\u062a\u06cc\u0628 \u0628\u0644\u0648\u06a9\u200c\u0647\u0627: {block_order}",
        f"\u062a\u0639\u062f\u0627\u062f: {len(rows)} \u0642\u0631\u0627\u0631\u062f\u0627\u062f | \u0635\u0641\u062d\u0647 {page + 1}/{total_pages} | \u0647\u0631 \u0635\u0641\u062d\u0647 {PAGE_SIZE}",
        f"\u0633\u062a\u0648\u0646\u200c\u0647\u0627: {' | '.join(payload.get('columns') or OPTION_COLUMNS)}",
        "\u2501" * 24,
    ]
    for index, row in enumerate(subset, page * PAGE_SIZE + 1):
        values = [
            row.get("نماد"), row.get("نوع قرارداد"), row.get("سهم پایه"),
            _fmt(row.get("اعمال")), _fmt(row.get("آخرین قیمت")), _fmt(row.get("قیمت سهم پایه")),
            _fmt(row.get("سربه‌سر")), _fmt(row.get("فاصله سربه‌سر"), "%"),
            row.get("تاریخ سررسید"), _fmt(row.get("روزهای باقی‌مانده")), _fmt(row.get("امتیاز شش‌بلوک")),
        ]
        block_scores = row.get("block_scores") or {}
        block_text = " | ".join(
            f"{name}={_fmt(block_scores.get(name))}" for name in BLOCK_WEIGHTS
        )
        lines.extend([
            f"{index}. " + " | ".join(str(value) for value in values),
            f"   شش‌بلوک: {block_text}",
            "─" * 24,
        ])
    if not subset:
        lines.append("قرارداد آپشن قابل رتبه‌بندی در Snapshot فعلی پیدا نشد.")
    lines.append("این خروجی رتبه‌بندی توصیفی است و سیگنال خرید/فروش نیست.")
    navigation = []
    if page > 0:
        navigation.append({"text": "◀️ قبلی", "callback_data": f"option_market_page:{page - 1}"})
    if page < total_pages - 1:
        navigation.append({"text": "بعدی ▶️", "callback_data": f"option_market_page:{page + 1}"})
    keyboard = [navigation] if navigation else []
    keyboard.append([{"text": HOME, "callback_data": "main_menu"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}, len(rows), page, total_pages
