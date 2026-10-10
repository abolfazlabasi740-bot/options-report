#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compact Bale cards for ranked option-enabled underlying shares. TSETMC-only."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_REPORT = ROOT / "output" / "base_share" / "latest_opportunity_v2_report.json"
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
        return "نامشخص"
    if isinstance(value, (int, float)):
        return f"{value:.1f}{suffix}"
    return str(value)


def _component_score(components, *keys):
    """Return a score only when the source report explicitly provides one."""
    for key in keys:
        item = components.get(key)
        if isinstance(item, dict):
            value = item.get("score")
            if isinstance(value, (int, float)):
                return float(value)
        elif isinstance(item, (int, float)):
            return float(item)
    return None


def _analysis(row, scores):
    available = [(name, value) for name, value in scores.items() if value is not None]
    if not available:
        return "امتیازهای جزئی کافی نیست؛ نتیجه‌گیری معتبر ممکن نیست."
    strongest = max(available, key=lambda item: item[1])
    weakest = min(available, key=lambda item: item[1])
    trend = str(row.get("trend_state") or "").strip()
    warnings = row.get("warnings") or []
    notes = [f"قوی‌ترین بخش: {strongest[0]} ({strongest[1]:.1f})"]
    if len(available) > 1:
        notes.append(f"ضعیف‌ترین بخش: {weakest[0]} ({weakest[1]:.1f})")
    if trend:
        notes.append(f"وضعیت روند: {trend}")
    if warnings:
        notes.append("ریسک/هشدار: " + "، ".join(str(x) for x in warnings[:2]))
    else:
        notes.append("هشدار ثبت‌شده‌ای در گزارش نیست")
    notes.append("این جمع‌بندی توصیفی است و به‌تنهایی سیگنال خرید نیست.")
    return "؛ ".join(notes)


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
    data_mode = snapshot.get("data_mode") or "نامشخص"
    generated = snapshot.get("generated_at") or "نامشخص"
    lines = [
        "📌 سهم‌های پایه دارای آپشن",
        f"مرتب‌سازی: امتیاز اصلی مدل سهم پایه | تعداد: {len(rows)}",
        f"داده: {data_mode} | زمان Snapshot: {generated}",
        f"صفحه {page + 1}/{total_pages}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    subset = rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    for idx, row in enumerate(subset, page * PAGE_SIZE + 1):
        symbol = str(row.get("symbol") or "نامشخص")
        components = row.get("components") or {}
        scores = {
            "تابلوخوانی": _component_score(components, "board"),
            "پرایس‌اکشن": _component_score(components, "momentum", "early_move"),
            "تکنیکال": _component_score(components, "technical", "trend"),
            "کندل‌استیک": _component_score(components, "candlestick", "candle", "candles", "candlestick_pattern"),
        }
        lines.extend([
            f"🟦 {idx}. {symbol} | امتیاز کل: {_fmt(row.get('final_score'))}/100",
            f"۱) تابلوخوانی: {_fmt(scores['تابلوخوانی'])}/100",
            f"۲) پرایس‌اکشن: {_fmt(scores['پرایس‌اکشن'])}/100",
            f"۳) تکنیکال: {_fmt(scores['تکنیکال'])}/100",
            f"۴) کندل‌استیک: {_fmt(scores['کندل‌استیک'])}/100",
            "تحلیل: " + _analysis(row, scores),
            "━━━━━━━━━━━━━━━━━━━━",
        ])
    if not subset:
        lines.append("سهم پایه دارای آپشن در داده‌های فعلی پیدا نشد.")
    lines.append("امتیاز کندل‌استیک فقط در صورت وجود خروجی صریح در گزارش نمایش داده می‌شود؛ داده مفقود حدس زده نمی‌شود.")
    lines.append("رتبه‌بندی توصیفی است؛ سیگنال خرید/فروش نیست. شواهد BestLimits تا عبور از دروازه مربوطه وارد نشده‌اند.")
    markup = []
    if page > 0:
        markup.append({"text": "◀️ قبلی", "callback_data": f"option_base_cards:{page - 1}"})
    if page < total_pages - 1:
        markup.append({"text": "بعدی ▶️", "callback_data": f"option_base_cards:{page + 1}"})
    keyboard = [markup] if markup else []
    keyboard.append([{"text": "🏠 منوی اصلی", "callback_data": "main_menu"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}, len(rows), page, total_pages
