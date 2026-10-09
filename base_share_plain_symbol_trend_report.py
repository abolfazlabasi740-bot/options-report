#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a trend-only shortlist from the existing TSETMC whole-market report.

Only symbols whose displayed symbol does NOT end in an ASCII, Persian, or
Arabic-Indic digit are included. This is a reporting filter only: no source
data, history, score, or option-contract ranking is changed.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from persian_date_utils import gregorian_to_jalali

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "base_share"
SOURCE = OUT / "latest_whole_market_opportunity_report.json"
DIGIT_AT_END = re.compile(r"[0-9\u0660-\u0669\u06F0-\u06F9]$")


def sha256_json(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main():
    if not SOURCE.exists():
        raise SystemExit("SOURCE_REPORT_NOT_FOUND: " + str(SOURCE) + "\nRun base_share_whole_market_first_pass.py first.")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    if source.get("source_of_truth") != "TSETMC" or not isinstance(source.get("rows"), list):
        raise SystemExit("INVALID_SOURCE_REPORT_OR_NON_TSETMC_SOURCE")

    all_rows = source["rows"]
    eligible = [
        row for row in all_rows
        if str(row.get("symbol") or "").strip()
        and not DIGIT_AT_END.search(str(row.get("symbol") or "").strip())
    ]
    eligible.sort(key=lambda row: (
        row.get("final_score") is None,
        -(float(row.get("final_score") or 0.0)),
        str(row.get("symbol") or "")
    ))
    now = datetime.now(ZoneInfo("Asia/Tehran"))
    payload = {
        "report_version": "PLAIN_SYMBOL_TREND_SHORTLIST-1.0",
        "generated_at": now.isoformat(),
        "source_of_truth": "TSETMC",
        "source_report": str(SOURCE),
        "source_report_sha256": source.get("report_sha256"),
        "latest_history_date": source.get("latest_history_date"),
        "latest_history_date_jalali": gregorian_to_jalali(source.get("latest_history_date")),
        "source_row_count": len(all_rows),
        "eligible_plain_symbol_count": len(eligible),
        "filter": "SYMBOL_MUST_NOT_END_WITH_ASCII_PERSIAN_OR_ARABIC_INDIC_DIGIT",
        "ranked_symbol_count": len(eligible),
        "displayed_top_n": 15,
        "rows": eligible,
        "buy_sell_signal": "NOT_GENERATED",
        "limitations": [
            "This is a preliminary historical-trend shortlist, not a buy/sell signal.",
            "Only the existing TSETMC history report is reused; no data is imputed.",
            "Board/BestLimits and fundamental/news evidence are not included in this report."
        ]
    }
    payload["report_sha256"] = sha256_json(payload)
    json_path = OUT / "latest_plain_symbol_trend_report.json"
    txt_path = OUT / "latest_plain_symbol_trend_report.txt"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    lines = [
        "گزارش اولیه روند سهام — فقط نمادهای بدون عدد در انتهای نماد",
        "=" * 92,
        "منبع: TSETMC | مبنا: گزارش تاریخی موجود، بدون دریافت مجدد تاریخچه",
        "آخرین تاریخ داده تاریخی (میلادی): " + str(source.get("latest_history_date") or "اطلاعات موجود نیست"),
        "آخرین تاریخ داده تاریخی (شمسیِ محاسبه‌شده): " + str(gregorian_to_jalali(source.get("latest_history_date")) or "اطلاعات موجود نیست"),
        f"تعداد ردیف‌های گزارش مبنا: {len(all_rows)} | نمادهای واجد فیلتر: {len(eligible)}",
        "فیلتر: نمادهایی که آخرین نویسه آن‌ها عدد انگلیسی، فارسی یا عربی باشد حذف شده‌اند.",
        "امتیازها همان امتیازهای گزارش مبنا هستند؛ هیچ داده‌ای جایگزین یا ساخته نشده است.",
        "این رتبه‌بندی سیگنال خرید/فروش نیست؛ داده تابلو، بنیادی و خبر در این خروجی لحاظ نشده است.",
        "-" * 92,
        "رتبه | نماد | امتیاز | کلاس | پوشش شواهد | تاریخ داده | بازده ۵ جلسه (%) | بازده ۲۰ جلسه (%) | RSI14 | هشدار",
        "-" * 92,
    ]
    for i, row in enumerate(eligible, 1):
        lines.append(
            f"{i} | {row.get('symbol') or 'اطلاعات موجود نیست'}"
            f" | {row.get('final_score') if row.get('final_score') is not None else 'اطلاعات موجود نیست'}"
            f" | {row.get('classification') or 'اطلاعات موجود نیست'}"
            f" | {row.get('evidence_coverage_pct') if row.get('evidence_coverage_pct') is not None else 'اطلاعات موجود نیست'}%"
            f" | {row.get('latest_market_date') or 'اطلاعات موجود نیست'} / {gregorian_to_jalali(row.get('latest_market_date')) or 'اطلاعات موجود نیست'}"
            f" | {row.get('return_5_sessions_pct') if row.get('return_5_sessions_pct') is not None else 'اطلاعات موجود نیست'}"
            f" | {row.get('return_20_sessions_pct') if row.get('return_20_sessions_pct') is not None else 'اطلاعات موجود نیست'}"
            f" | {row.get('rsi_14') if row.get('rsi_14') is not None else 'اطلاعات موجود نیست'}"
            f" | {','.join(row.get('warnings') or []) or 'ندارد'}"
        )
    lines.extend(["-" * 92, "گزارش JSON: " + str(json_path), "گزارش TXT: " + str(txt_path)])
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("STATUS = PLAIN_SYMBOL_TREND_REPORT_COMPLETE")
    print("SOURCE_REPORT_ROWS =", len(all_rows))
    print("ELIGIBLE_PLAIN_SYMBOLS =", len(eligible))
    print("LATEST_HISTORY_DATE_GREGORIAN =", source.get("latest_history_date") or "UNAVAILABLE")
    print("LATEST_HISTORY_DATE_JALALI =", gregorian_to_jalali(source.get("latest_history_date")) or "UNAVAILABLE")
    print("TEXT_REPORT =", txt_path)
    print("JSON_REPORT =", json_path)
    print("RANKED_SYMBOL_COUNT =", len(eligible))
    print("TOP_15 =")
    for i, row in enumerate(eligible[:15], 1):
        print(
            f"{i}|{row.get('symbol')}|score={row.get('final_score')}|class={row.get('classification')}"
            f"|coverage={row.get('evidence_coverage_pct')}%|date={row.get('latest_market_date')}"
            f"|R5={row.get('return_5_sessions_pct')}|R20={row.get('return_20_sessions_pct')}"
            f"|RSI14={row.get('rsi_14')}|warnings={','.join(row.get('warnings') or []) or 'NONE'}"
        )
    print("BUY_SELL_SIGNAL = OFF")


if __name__ == "__main__":
    main()
