#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bale cards for ranked option-enabled underlying shares. TSETMC-only."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_REPORT = ROOT / "output" / "base_share" / "latest_plain_symbol_trend_report.json"
OPTION_SNAPSHOT = ROOT / "output" / "tsetmc_first" / "latest_universe_snapshot.json"
PAGE_SIZE = 5


def _load(path):
    if not path.exists():
        raise RuntimeError("REQUIRED_REPORT_NOT_FOUND: " + str(path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError("REQUIRED_REPORT_INVALID: " + path.name) from exc


def _fmt(value, suffix=""):
    if value is None or value == "":
        return "اطلاعات موجود نیست"
    if isinstance(value, (int, float)):
        return f"{value:.2f}{suffix}"
    return str(value)


def _score_reason(row):
    parts = row.get("components") or {}
    labels = (
        ("trend", "روند"),
        ("momentum", "مومنتوم"),
        ("technical", "تکنیکال"),
        ("volume_value", "حجم و ارزش"),
        ("early_move", "شروع حرکت"),
        ("board", "تابلو"),
        ("entry_quality", "کیفیت نقطه ورود"),
    )
    out = []
    for key, label in labels:
        item = parts.get(key) or {}
        score = item.get("score")
        if score is not None:
            out.append(f"{label} {_fmt(score)}/100")
    return " | ".join(out) if out else "جزئیات اجزای امتیاز در گزارش موجود نیست"


def _build_rows():
    base = _load(BASE_REPORT)
    snapshot = _load(OPTION_SNAPSHOT)
    if base.get("source_of_truth") != "TSETMC":
        raise RuntimeError("BASE_REPORT_SOURCE_NOT_TSETMC")
    if not isinstance(base.get("rows"), list):
        raise RuntimeError("BASE_REPORT_ROWS_INVALID")
    if not isinstance(snapshot.get("rows"), list):
        raise RuntimeError("OPTION_SNAPSHOT_ROWS_INVALID")

    option_symbols = set()
    for row in snapshot["rows"]:
        ident = row.get("identity") or {}
        symbol = str(ident.get("underlying_symbol") or "").strip()
        if symbol:
            option_symbols.add(symbol)

    rows = [row for row in base["rows"] if str(row.get("symbol") or "").strip() in option_symbols]
    rows.sort(key=lambda row: (
        row.get("final_score") is None,
        -(float(row.get("final_score") or 0)),
        str(row.get("symbol") or ""),
    ))
    return base, snapshot, rows


def render_page(page=0):
    base, snapshot, rows = _build_rows()
    total_pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(int(page), total_pages - 1))
    data_mode = snapshot.get("data_mode") or "اطلاعات موجود نیست"
    generated = snapshot.get("generated_at") or "اطلاعات موجود نیست"
    lines = [
        "📌 رتبه‌بندی سهم‌های پایه دارای آپشن",
        "مبنای ترتیب: امتیاز اصلی مدل سهم پایه؛ امتیازها بازنویسی نشده‌اند.",
        f"منبع: TSETMC | حالت داده: {data_mode}",
        f"زمان Snapshot: {generated}",
        f"تعداد سهم پایه دارای آپشن و رتبه‌بندی‌شده: {len(rows)}",
        f"صفحه {page + 1}/{total_pages} | نمایش {PAGE_SIZE} سهم در هر صفحه",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    subset = rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    for idx, row in enumerate(subset, page * PAGE_SIZE + 1):
        symbol = str(row.get("symbol") or "اطلاعات موجود نیست")
        score = _fmt(row.get("final_score"))
        classification = str(row.get("classification") or "اطلاعات موجود نیست")
        coverage = _fmt(row.get("evidence_coverage_pct"), "%")
        r5 = _fmt(row.get("return_5_sessions_pct"), "%")
        r20 = _fmt(row.get("return_20_sessions_pct"), "%")
        rsi = _fmt(row.get("rsi_14"))
        trend = str(row.get("trend_state") or "اطلاعات موجود نیست")
        warnings = "، ".join(str(x) for x in (row.get("warnings") or [])) or "هشدار ثبت نشده"
        lines.extend([
            f"🟦 کارت {idx} | {symbol}",
            f"امتیاز: {score}/100 | طبقه: {classification} | پوشش شواهد: {coverage}",
            f"دلایل امتیاز: {_score_reason(row)}",
            f"روند: {trend} | بازده ۵ جلسه: {r5} | بازده ۲۰ جلسه: {r20} | RSI14: {rsi}",
            f"محدودیت/هشدار: {warnings}",
            "━━━━━━━━━━━━━━━━━━━━",
        ])
    if not subset:
        lines.append("سهم پایه دارای آپشن در داده‌های فعلی پیدا نشد.")
    lines.extend([
        "رتبه‌بندی توصیفی است؛ سیگنال خرید/فروش نیست.",
        "تابلو/BestLimits تا عبور از دروازه شواهد در این امتیاز وارد نشده است.",
    ])
    markup = []
    if page > 0:
        markup.append({"text": "◀️ قبلی", "callback_data": f"option_base_cards:{page - 1}"})
    if page < total_pages - 1:
        markup.append({"text": "بعدی ▶️", "callback_data": f"option_base_cards:{page + 1}"})
    keyboard = [markup] if markup else []
    keyboard.append([{"text": "🏠 منوی اصلی", "callback_data": "main_menu"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}, len(rows), page, total_pages
