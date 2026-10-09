#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""First-pass whole-market common-share opportunity scan; TSETMC only.

Uses the completed identity catalog, conservatively excludes known non-equity
market groups, and applies the existing V2.1 score to retained daily histories.
This is exploratory ranking only, not a buy/sell signal.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsetmc_adapter import TSETMCAdapter
from underlying_trend_engine import analyze_history
from base_share_opportunity_engine_v2 import score_opportunity, ENGINE_VERSION
from persian_date_utils import gregorian_to_jalali

TEHRAN = ZoneInfo("Asia/Tehran")
CATALOG = ROOT / "output" / "base_share" / "market_watch_identity_catalog.json"
OUT = ROOT / "output" / "base_share"
EXCLUDED_SECTORS = {"68", "69", "67"}
EXCLUDED_MARKET_TERMS = ("ابزارهای مشتقه", "اوراق بدهی", "صندوق های قابل معامله", "صندوق‌های قابل معامله")
WORKERS = 10


def norm(value):
    return str(value or "").strip()


def sha256_json(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_candidate(row):
    ident = row.get("identity") or {}
    if row.get("identity_status") != "SUCCESS" or not ident:
        return False, "IDENTITY_UNAVAILABLE"
    symbol = norm(ident.get("symbol"))
    instrument_id = norm(row.get("instrument_id"))
    if not symbol or not instrument_id:
        return False, "IDENTITY_INCOMPLETE"
    sector = norm(ident.get("sector_code"))
    market_title = norm(ident.get("cgrValCotTitle"))
    if sector in EXCLUDED_SECTORS:
        return False, "NON_EQUITY_SECTOR_" + sector
    if any(term in market_title for term in EXCLUDED_MARKET_TERMS):
        return False, "NON_EQUITY_MARKET_TITLE"
    # Conservative text guard for known debt/fund/derivative instruments.
    name = norm(ident.get("name"))
    text = symbol + " " + name
    if any(term in text for term in ("اختیار خرید", "اختیار فروش", "اوراق مشارکت", "اسناد خزانه", "صندوق سرمایه گذاری", "صندوق سرمایه‌گذاری")):
        return False, "NON_COMMON_EQUITY_TEXT_GUARD"
    return True, "CANDIDATE_BY_TSETMC_IDENTITY_HEURISTIC"


def fetch_one(instrument_id, include_board):
    adapter = TSETMCAdapter(timeout=5.0, retries=0)
    try:
        history = adapter.daily_history(instrument_id, top=100)
        info = adapter.instrument_info(instrument_id) if include_board else {"source": "TSETMC", "data": {}}
        result = analyze_history(instrument_id, history, info)
        if include_board:
            # Current board is not used in this first pass; it remains excluded
            # until the separate BestLimits semantic gate passes.
            result["board_refresh"] = "NOT_USED_IN_FIRST_PASS"
        else:
            result["board_refresh"] = "CLOSED_MARKET_NO_REFRESH"
        return instrument_id, result
    except Exception as exc:
        return instrument_id, {
            "status": "UNAVAILABLE",
            "instrument_id": instrument_id,
            "source": "TSETMC",
            "reason": type(exc).__name__ + ": " + str(exc)[:180],
            "history_count": None,
            "latest_market_date": None,
        }


def main():
    if not CATALOG.exists():
        raise SystemExit("IDENTITY_CATALOG_NOT_FOUND: " + str(CATALOG) + "\nRun market_watch_identity_catalog.py first.")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    if catalog.get("source") != "TSETMC" or not isinstance(catalog.get("records"), list):
        raise SystemExit("INVALID_TSETMC_IDENTITY_CATALOG")
    now = datetime.now(TEHRAN)
    market_day = now.weekday() in {5, 6, 0, 1, 2}
    live_window = market_day and time(9, 0) <= now.time() <= time(12, 30)
    # Whole-market first pass intentionally uses daily history only. This avoids
    # thousands of live order-book/client-type calls and keeps BestLimits gated.
    include_board = False

    candidates = []
    excluded = Counter()
    for row in catalog["records"]:
        accepted, reason = is_candidate(row)
        if accepted:
            candidates.append(row)
        else:
            excluded[reason] += 1

    # Deduplicate by instrument ID without inventing replacements.
    unique = {}
    for row in candidates:
        unique.setdefault(norm(row.get("instrument_id")), row)
    candidates = [row for iid, row in unique.items() if iid]
    candidates.sort(key=lambda x: (norm((x.get("identity") or {}).get("symbol")), norm(x.get("instrument_id"))))

    print("STATUS = WHOLE_MARKET_FIRST_PASS_RUNNING", flush=True)
    print("CATALOG_RECORDS =", len(catalog["records"]), flush=True)
    print("CANDIDATE_COUNT =", len(candidates), flush=True)
    print("EXCLUDED_COUNTS =", json.dumps(dict(excluded), ensure_ascii=False), flush=True)
    print("HISTORY_MODE = TSETMC_DAILY_HISTORY_ONLY", flush=True)
    print("BOARD_REFRESH =", "LIVE_WINDOW_BUT_NOT_USED_IN_FIRST_PASS" if live_window else "CLOSED_MARKET_NO_REFRESH", flush=True)

    results = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_one, norm(row["instrument_id"]), include_board): row for row in candidates}
        done = 0
        for future in as_completed(futures):
            iid, ctx = future.result()
            results[iid] = ctx
            done += 1
            if done % 100 == 0 or done == len(candidates):
                print(f"PROGRESS = {done}/{len(candidates)}", flush=True)

    ranked = []
    for row in candidates:
        ident = row.get("identity") or {}
        iid = norm(row.get("instrument_id"))
        ctx = results.get(iid) or {}
        scored = score_opportunity(ctx)
        ranked.append({
            "instrument_id": iid,
            "symbol": norm(ident.get("symbol")),
            "name": norm(ident.get("name")),
            "sector_code": norm(ident.get("sector_code")),
            "sector_name": norm(ident.get("sector_name")),
            "subsector_code": norm(ident.get("subsector_code")),
            "subsector_name": norm(ident.get("subsector_name")),
            "market_title": norm(ident.get("cgrValCotTitle")),
            **scored,
            "instrument_classification": "COMMON_SHARE_CANDIDATE_HEURISTIC_NOT_VERIFIED",
            "history_status": ctx.get("status"),
            "history_count": ctx.get("history_count"),
            "latest_market_date": ctx.get("latest_market_date"),
            "latest_market_date_jalali": gregorian_to_jalali(ctx.get("latest_market_date")),
            "last_price": ctx.get("last_price"),
            "last_close": ctx.get("last_close"),
            "sma_5": ctx.get("sma_5"),
            "sma_10": ctx.get("sma_10"),
            "sma_20": ctx.get("sma_20"),
            "sma_50": ctx.get("sma_50"),
            "return_5_sessions_pct": ctx.get("return_5_sessions_pct"),
            "return_20_sessions_pct": ctx.get("return_20_sessions_pct"),
            "rsi_14": ctx.get("rsi_14"),
            "macd_12_26": ctx.get("macd_12_26"),
            "volume_ratio_5_to_20": ctx.get("volume_ratio_5_to_20"),
            "value_ratio_5_to_20": ctx.get("value_ratio_5_to_20"),
            "early_move": ctx.get("early_move"),
            "history_reason": ctx.get("reason"),
            "source": "TSETMC",
        })

    ranked.sort(key=lambda x: (x.get("final_score") is None, -(x.get("final_score") or 0.0), x["symbol"]))
    dates = sorted({str(x["latest_market_date"]) for x in ranked if x.get("latest_market_date")})
    statuses = Counter(str(x.get("history_status") or "UNKNOWN") for x in ranked)
    payload = {
        "report_version": "WHOLE-MARKET-COMMON-SHARE-FIRST-PASS-1.0",
        "generated_at": now.isoformat(),
        "source_of_truth": "TSETMC",
        "catalog_snapshot_sha256": catalog.get("source_snapshot_sha256"),
        "catalog_report_sha256": catalog.get("report_sha256"),
        "catalog_record_count": len(catalog["records"]),
        "candidate_count": len(candidates),
        "excluded_counts": dict(excluded),
        "history_status_counts": dict(statuses),
        "latest_history_date": dates[-1] if dates else None,
        "latest_history_date_jalali": gregorian_to_jalali(dates[-1]) if dates else None,
        "score_engine": ENGINE_VERSION,
        "classification_policy": "CONSERVATIVE_HEURISTIC; UNKNOWN_OR_CONFLICTING_IDENTITY_EXCLUDED; MANUAL_REVIEW_REQUIRED",
        "data_mode": "TSETMC_DAILY_HISTORY_ONLY; NO_IMPUTATION",
        "board_and_bestlimits": "NOT_USED; SEMANTIC_GATE_UNCHANGED",
        "buy_sell_signal": "NOT_GENERATED",
        "rows": ranked,
    }
    payload["report_sha256"] = sha256_json(payload)
    OUT.mkdir(parents=True, exist_ok=True)
    json_path = OUT / "latest_whole_market_opportunity_report.json"
    txt_path = OUT / "latest_whole_market_opportunity_report.txt"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    lines = [
        "گزارش فرصت‌یابی اولیه کل بازار سهام — نسخه آزمایشی",
        "=" * 78,
        "منبع: TSETMC | موتور امتیازدهی: " + ENGINE_VERSION,
        "زمان تولید: " + now.isoformat(),
        "آخرین تاریخ داده تاریخی (میلادی): " + (dates[-1] if dates else "اطلاعات موجود نیست"),
        "آخرین تاریخ داده تاریخی (شمسیِ محاسبه‌شده): " + (gregorian_to_jalali(dates[-1]) if dates else "اطلاعات موجود نیست"),
        f"کل کاتالوگ: {len(catalog['records'])} | نامزدهای بررسی: {len(candidates)}",
        "وضعیت تاریخچه: " + json.dumps(dict(statuses), ensure_ascii=False),
        "حذف‌ها: " + json.dumps(dict(excluded), ensure_ascii=False),
        "طبقه‌بندی سهم عادی در این مرحله قاعده‌محور و مقدماتی است؛ بازبینی موارد مرزی لازم است.",
        "داده مفقود جایگزین نشده است. تابلوی زنده/BestLimits در این گزارش امتیازدهی نشده است.",
        "امتیاز صرفاً رتبه‌بندی توصیفی است؛ سیگنال خرید/فروش یا پیش‌بینی قطعی صف نیست.",
        "-" * 78,
        "رتبه | نماد | امتیاز | کلاس | پوشش شواهد | تاریخ آخرین داده | بازده 5/20 جلسه | RSI14 | هشدار",
        "-" * 78,
    ]
    for i, item in enumerate(ranked[:100], 1):
        warnings = ",".join(item.get("warnings") or []) or "ندارد"
        lines.append(
            f"{i} | {item['symbol']} | {item.get('final_score') if item.get('final_score') is not None else 'اطلاعات موجود نیست'}"
            f" | {item.get('classification')} | {item.get('evidence_coverage_pct')}%"
            f" | {item.get('latest_market_date') or 'اطلاعات موجود نیست'}"
            f" | {item.get('return_5_sessions_pct')}/{item.get('return_20_sessions_pct')}"
            f" | {item.get('rsi_14')} | {warnings}"
        )
    lines.extend(["-" * 78, "گزارش کامل JSON: " + str(json_path), "REPORT_SHA256 = " + hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()])
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("STATUS = WHOLE_MARKET_FIRST_PASS_COMPLETE", flush=True)
    print("HISTORY_STATUS_COUNTS =", json.dumps(dict(statuses), ensure_ascii=False), flush=True)
    print("LATEST_HISTORY_DATE_GREGORIAN =", dates[-1] if dates else "UNAVAILABLE", flush=True)
    print("LATEST_HISTORY_DATE_JALALI =", gregorian_to_jalali(dates[-1]) if dates else "UNAVAILABLE", flush=True)
    print("TEXT_REPORT =", txt_path, flush=True)
    print("JSON_REPORT =", json_path, flush=True)
    print("TOP_15 =", json.dumps([
        {"rank": i + 1, "symbol": x["symbol"], "score": x.get("final_score"), "class": x.get("classification"), "instrument_classification": x.get("instrument_classification"),
         "coverage": x.get("evidence_coverage_pct"), "date": x.get("latest_market_date"), "warnings": x.get("warnings")}
        for i, x in enumerate(ranked[:15])
    ], ensure_ascii=False), flush=True)
    print("BUY_SELL_SIGNAL = OFF", flush=True)


if __name__ == "__main__":
    main()
