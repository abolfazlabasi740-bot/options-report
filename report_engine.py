#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TSETMC-only production report boundary for OptimusAI V4.1.1.

Reporting remains available outside market hours by using the latest valid
TSETMC snapshot. Cached data is explicitly labelled and never presented as
live movement. Economic ranking is active only on TSETMC opportunity candidates; predictive signals remain fail-closed behind the validation/release boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from audit_integrity import verify_audit
from tsetmc_first_source import build_tsetmc_snapshot
from tsetmc_adapter import TSETMCAdapter
from underlying_trend_engine import fetch_underlying_context
from codal_export_engine import fetch_export_context, fetch_recent_events
from economic_scoring_engine import build_economic_ranking
from signal_engine_shadow import evaluate_shadow_candidates
from tsetmc_history import archive_universe_snapshot
from tsetmc_eligibility import (
    OPPORTUNITY_CANDIDATE,
    build_opportunity_candidates,
    classify_universe,
)

ROOT = Path(__file__).resolve().parent
TEHRAN = ZoneInfo("Asia/Tehran")
TOP_COUNT = 15


def _session_state(now=None):
    now = now or datetime.now(TEHRAN)
    if now.weekday() in {5, 6, 0, 1, 2} and time(9, 0) <= now.time() <= time(12, 30):
        return "SESSION_OPEN"
    return "OFFMARKET"


def _source_observation_state(snapshot):
    rows = snapshot.get("rows") or []
    timestamps = sorted({
        str(row.get("source_market_timestamp")).strip()
        for row in rows
        if row.get("source_market_timestamp")
    })
    if not timestamps:
        return {
            "status": "NO_SOURCE_MARKET_TIMESTAMP",
            "unique_timestamp_count": 0,
            "latest_source_market_timestamp": None,
        }
    if len(timestamps) == 1:
        return {
            "status": "SINGLE_SOURCE_OBSERVATION",
            "unique_timestamp_count": 1,
            "latest_source_market_timestamp": timestamps[0],
        }
    return {
        "status": "MULTIPLE_SOURCE_OBSERVATIONS",
        "unique_timestamp_count": len(timestamps),
        "latest_source_market_timestamp": timestamps[-1],
    }


def _market_state(snapshot):
    session = _session_state()
    observation = _source_observation_state(snapshot)
    data_mode = snapshot.get("data_mode")
    if data_mode == "LAST_KNOWN_TSETMC_SNAPSHOT":
        status = "OFFMARKET_USING_LAST_KNOWN_TSETMC" if session == "OFFMARKET" else "SESSION_OPEN_USING_LAST_KNOWN_TSETMC"
    elif session == "OFFMARKET":
        status = "OFFMARKET"
    elif observation["status"] == "SINGLE_SOURCE_OBSERVATION":
        status = "SESSION_OPEN_BUT_MOVEMENT_NOT_PROVEN"
    elif observation["status"] == "MULTIPLE_SOURCE_OBSERVATIONS":
        status = "SESSION_OPEN_WITH_MULTIPLE_SOURCE_TIMESTAMPS"
    else:
        status = "SESSION_OPEN_TIMESTAMP_UNAVAILABLE"
    return {
        "session_state": session,
        "observation_state": observation["status"],
        "status": status,
        "data_mode": data_mode,
        "live_refresh_status": snapshot.get("live_refresh_status"),
        "fallback_reason": snapshot.get("fallback_reason"),
        "unique_timestamp_count": observation["unique_timestamp_count"],
        "latest_source_market_timestamp": observation["latest_source_market_timestamp"],
    }


def _trading_rank_rows(rows):
    """Rank contracts by explicit TSETMC trading activity, not economic score."""
    def num(value):
        try:
            if value in (None, ""):
                return None
            value = float(value)
            return value if value == value and value not in (float("inf"), float("-inf")) else None
        except (TypeError, ValueError):
            return None

    ranked = []
    for row in rows:
        canonical = row.get("canonical") or {}
        value = num(canonical.get("ارزش معاملات"))
        volume = num(canonical.get("حجم معاملات"))
        count = num(canonical.get("تعداد معاملات"))
        instrument_id = str((row.get("identity") or {}).get("instrument_id") or "")
        ranked.append((
            1 if value is not None else 0,
            value if value is not None else float("-inf"),
            1 if volume is not None else 0,
            volume if volume is not None else float("-inf"),
            1 if count is not None else 0,
            count if count is not None else float("-inf"),
            instrument_id,
            row,
        ))
    ranked.sort(key=lambda item: item[:-1], reverse=True)
    return [item[-1] for item in ranked]


def _attach_canonical_quote_evidence(rows, *, adapter=None):
    """Attach exact TSETMC ClosingPriceInfo evidence to displayed rows only.

    MarketWatch remains the ranking/value source. ClosingPriceInfo is used only
    to bind a displayed instrument to an explicit TSETMC observation timestamp
    and to record quote consistency. Retrieval time is never used as market time.
    """
    adapter = adapter or TSETMCAdapter()
    for row in rows:
        identity = row.get("identity") or {}
        instrument_id = identity.get("instrument_id")
        evidence = {
            "status": "INSUFFICIENT_DATA",
            "source": "TSETMC",
            "endpoint": None,
            "instrument_id": instrument_id,
            "source_market_timestamp": None,
            "source_market_timestamp_status": "UNAVAILABLE",
            "retrieved_at": None,
            "last_price": None,
            "close_price": None,
            "market_watch_last_price": (row.get("canonical") or {}).get("آخرین قیمت"),
            "market_watch_close_price": (row.get("canonical") or {}).get("قیمت پایانی"),
            "quote_consistency": "NOT_EVALUATED",
        }
        if not instrument_id:
            row["canonical_quote_evidence"] = evidence
            row["source_market_timestamp"] = None
            row["source_market_timestamp_status"] = "UNAVAILABLE"
            continue
        try:
            quote = adapter.quote(str(instrument_id))
            data = quote.get("data") or {}
            evidence.update({
                "status": "SUCCESS",
                "endpoint": quote.get("endpoint"),
                "retrieved_at": quote.get("retrieved_at"),
                "last_price": data.get("pDrCotVal"),
                "close_price": data.get("pClosing"),
            })
            try:
                d_even = int(data.get("dEven"))
                h_even = int(data.get("hEven"))
                hh, mm, ss = h_even // 10000, (h_even // 100) % 100, h_even % 100
                if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
                    raise ValueError("invalid hEven")
                timestamp = datetime.strptime(
                    f"{d_even:08d} {hh:02d}:{mm:02d}:{ss:02d}",
                    "%Y%m%d %H:%M:%S",
                ).isoformat()
                evidence["source_market_timestamp"] = timestamp
                evidence["source_market_timestamp_status"] = "AVAILABLE"
            except (TypeError, ValueError):
                pass

            mw_last = evidence["market_watch_last_price"]
            mw_close = evidence["market_watch_close_price"]
            cq_last = evidence["last_price"]
            cq_close = evidence["close_price"]
            if mw_last is not None and cq_last is not None and float(mw_last) == float(cq_last) and mw_close is not None and cq_close is not None and float(mw_close) == float(cq_close):
                evidence["quote_consistency"] = "MATCH"
            elif mw_last is not None or mw_close is not None:
                evidence["quote_consistency"] = "DIFFERS"
            else:
                evidence["quote_consistency"] = "NOT_EVALUATED"
        except Exception as exc:
            evidence["status"] = "SOURCE_UNAVAILABLE"
            evidence["error_type"] = type(exc).__name__
            evidence["error"] = str(exc)

        row["canonical_quote_evidence"] = evidence
        row["source_market_timestamp"] = evidence["source_market_timestamp"]
        row["source_market_timestamp_status"] = evidence["source_market_timestamp_status"]
    return rows


def build_tsetmc_report(*, top_count=None, symbol_prefix=None, underlying_symbol=None, flow=None, report_mode="RANKED"):
    limit = TOP_COUNT if top_count is None else int(top_count)
    if isinstance(limit, bool) or limit <= 0:
        raise ValueError("تعداد قراردادها باید عدد صحیح مثبت باشد")

    adapter = TSETMCAdapter()
    snapshot = build_tsetmc_snapshot(
        adapter=adapter,
        flow=flow,
        max_instruments=None,
        symbol_prefix=symbol_prefix,
    )
    # Discovery must cover the full TSETMC option universe. The report display
    # limit is applied only after ranking so the ranking is not truncated by
    # discovery order.
    rows = list(snapshot.get("rows", []))
    if symbol_prefix:
        prefix = str(symbol_prefix).strip()
        rows = [
            row for row in rows
            if str(row.get("canonical", {}).get("نماد") or "").startswith(prefix)
        ]
    if underlying_symbol:
        requested = str(underlying_symbol).strip().replace("ي", "ی").replace("ك", "ک")
        rows = [
            row for row in rows
            if str((row.get("identity") or {}).get("underlying_symbol") or "").strip().replace("ي", "ی").replace("ك", "ک") == requested
        ]
        if not rows:
            raise ValueError(f"نماد پایه {requested} در Universe فعلی TSETMC پیدا نشد")
    # Preserve the complete TSETMC evidence universe separately. The report
    # display limit must never destroy the evidence needed for audit/analysis.
    snapshot["universe_rows"] = list(rows)
    snapshot["universe_row_count"] = len(rows)

    # TRADING_ACTIVITY is intentionally independent from the economic
    # eligibility/ranking/opportunity engines. It must not fail because an
    # economic scoring layer is unavailable.
    if report_mode == "TRADING_ACTIVITY":
        eligibility = {
            "status": "OFF",
            "rows_evaluated": len(rows),
            "counts": {OPPORTUNITY_CANDIDATE: 0},
            "candidate_instrument_ids": [],
        }
        ranking = {
            "mode": "OFF",
            "status": "OFF",
            "ranking_scope": "TRADING_ACTIVITY",
            "ranking_scope_row_count": 0,
            "ranking_rows": [],
        }
        opportunity = {
            "status": "OFF",
            "engine_version": "NOT_RUN",
            "candidate_count": 0,
        }
        snapshot["eligibility"] = eligibility
        snapshot["ranking"] = ranking
        snapshot["opportunity"] = opportunity
        rows = _trading_rank_rows(rows)[:limit]
        snapshot["report_mode"] = "TRADING_ACTIVITY"
        snapshot["report_ranking_basis"] = [
            "ارزش معاملات (نزولی)",
            "حجم معاملات (نزولی؛ tie-breaker)",
            "تعداد معاملات (نزولی؛ tie-breaker)",
            "شناسه ابزار (برای ترتیب قطعی)",
        ]
    else:
        # Economic ranking remains gated by opportunity-candidate evidence.
        eligibility = classify_universe(rows)
        snapshot["eligibility"] = eligibility
        candidate_ids = set(eligibility.get("candidate_instrument_ids") or [])
        candidate_rows = [
            row for row in rows
            if (row.get("identity") or {}).get("instrument_id") in candidate_ids
        ]

        ranking = build_economic_ranking(candidate_rows)
        ranking["ranking_scope"] = "OPPORTUNITY_CANDIDATES"
        ranking["ranking_scope_row_count"] = len(candidate_rows)
        snapshot["ranking"] = ranking

        shadow_candidates = []
        for item in ranking.get("ranking_rows", []):
            shadow_candidates.append({
                "instrument_id": item.get("instrument_id"),
                "symbol": item.get("symbol"),
                "contract_type": item.get("contract_type"),
                "rank": item.get("rank"),
                "economic_score": item.get("economic_score"),
                "evidence": {
                    "supported_blocks": item.get("supported_blocks") or [],
                    "features": item.get("features") or {},
                },
            })
        snapshot["signal_shadow"] = evaluate_shadow_candidates(shadow_candidates)

        opportunity = build_opportunity_candidates(rows, ranking, eligibility)
        snapshot["opportunity"] = opportunity

        ranked_order = {
            item.get("instrument_id"): item.get("rank")
            for item in ranking.get("ranking_rows", [])
        }
        candidate_rows.sort(
            key=lambda row: (
                ranked_order.get((row.get("identity") or {}).get("instrument_id")) is None,
                ranked_order.get((row.get("identity") or {}).get("instrument_id")) or 10**9,
            )
        )
        rows = candidate_rows[:limit]
        snapshot["report_mode"] = "RANKED"
    if report_mode == "TRADING_ACTIVITY":
        snapshot["signal_shadow"] = {
            "status": "OFF",
            "engine_version": "SIGNAL-SHADOW-1.1",
            "production_enabled": False,
            "signal_count": 0,
            "buy_sell_signal": "NOT_GENERATED",
            "items": [],
        }
    _attach_canonical_quote_evidence(rows, adapter=adapter)
    enrichment_rows = snapshot.get("universe_rows") or rows
    underlying_ids = sorted({
        str((row.get("identity") or {}).get("underlying_id") or "").strip()
        for row in enrichment_rows
        if str((row.get("identity") or {}).get("underlying_id") or "").strip()
    })
    snapshot["underlying_context"] = fetch_underlying_context(underlying_ids, adapter=adapter)
    underlying_symbols = sorted({
        str((row.get("identity") or {}).get("underlying_symbol") or "").strip()
        for row in enrichment_rows
        if str((row.get("identity") or {}).get("underlying_symbol") or "").strip()
    })
    snapshot["codal_export_context"] = fetch_export_context(underlying_symbols, root=ROOT)
    snapshot["codal_event_context"] = fetch_recent_events(underlying_symbols)
    snapshot["rows"] = rows
    snapshot["row_count"] = len(rows)

    # Recompute the observation state after canonical quote evidence is attached.
    market_state = _market_state(snapshot)
    snapshot["market_state"] = market_state

    def number(value):
        if value in (None, ""):
            return "داده موجود نیست"
        try:
            return f"{float(value):,.2f}".replace(".00", "")
        except (TypeError, ValueError):
            return str(value)

    def percent(value):
        return "داده موجود نیست" if value in (None, "") else f"{float(value):.2f}%"

    mw = snapshot.get("evidence", {}).get("market_watch", {})
    data_mode = snapshot.get("data_mode") or "UNKNOWN"
    basis_timestamp = market_state["latest_source_market_timestamp"] or "داده موجود نیست"

    lines = [
        "📊 گزارش اولیه بازار اختیار معامله — TSETMC-ONLY",
        "━━━━━━━━━━━━━━━━━━━━",
        "📥 منبع حقیقت: TSETMC",
        f"📌 حالت داده: {data_mode}",
        f"📌 وضعیت به‌روزرسانی زنده: {snapshot.get('live_refresh_status', 'داده موجود نیست')}",
        f"📌 وضعیت جلسه بازار: {market_state['session_state']}",
        f"📌 وضعیت گزارش: {market_state['status']}",
        f"📌 تعداد timestamp مشاهده‌شده از منبع: {market_state['unique_timestamp_count']}",
        f"📌 آخرین timestamp صریح منبع: {basis_timestamp}",
        f"📌 تعداد رکوردهای کشف‌شده TSETMC: {snapshot.get('universe_row_count', snapshot.get('row_count', 0))}",
        f"📌 تعداد Flowهای بررسی‌شده: {len(mw.get('flows') or [])}",
        f"📌 تعداد قراردادهای واجد وضعیت OPPORTUNITY_CANDIDATE: {eligibility.get('counts', {}).get(OPPORTUNITY_CANDIDATE, 0)}",
        f"📌 تعداد قراردادهای مبنای گزارش: {snapshot.get('row_count', 0)}",
        f"📌 وضعیت Eligibility: {eligibility.get('status')} | ارزیابی کل رکوردها: {eligibility.get('rows_evaluated', 0)}",
        f"📌 وضعیت Opportunity Engine: {opportunity.get('status')} | نسخه: {opportunity.get('engine_version')} | کاندیداها: {opportunity.get('candidate_count', 0)}",
        f"📌 Opportunity-Candidate: {eligibility.get('counts', {}).get(OPPORTUNITY_CANDIDATE, 0)} | Ranking-Evidence-Rows: {sum(1 for x in ranking.get('ranking_rows', []) if x.get('economic_score') is not None)}",
        f"⏱ زمان دریافت/تولید منبع: {mw.get('retrieved_at', 'داده موجود نیست')}",
        f"🔐 Snapshot SHA256: {snapshot.get('snapshot_sha256')}",
        f"📊 وضعیت امتیازدهی اقتصادی: {ranking.get('mode')} | وضعیت رتبه‌بندی: {ranking.get('status')}",
        "⚠️ این رتبه‌بندی فقط از شواهد TSETMC و مشتقات ریاضی همان داده‌ها استفاده می‌کند؛ داده مفقود صفر یا حدس نمی‌شود.",
        "⚠️ هر فیلد فاقد شواهد مستقیم TSETMC عمداً «داده موجود نیست» باقی می‌ماند.",
    ]

    if data_mode == "LAST_KNOWN_TSETMC_SNAPSHOT":
        lines.append(
            "ℹ️ بازار/endpoint در این اجرا refresh زنده نداده است؛ مبنای گزارش آخرین Snapshot معتبر TSETMC است و این خروجی حرکت زنده فعلی را ادعا نمی‌کند."
        )
        if snapshot.get("fallback_reason"):
            lines.append(f"ℹ️ علت استفاده از Snapshot قبلی: {snapshot['fallback_reason']}")
    elif market_state["session_state"] == "OFFMARKET":
        lines.append(
            "ℹ️ بازار خارج از جلسه معاملاتی است؛ داده TSETMC در این خروجی به‌عنوان آخرین وضعیت معتبر منبع گزارش می‌شود، نه حرکت زنده."
        )
    elif market_state["observation_state"] == "SINGLE_SOURCE_OBSERVATION":
        lines.append(
            "ℹ️ timestamp مشاهده‌شده یکتا است؛ حرکت لحظه‌ای بازار اثبات نشده و گزارش live-moving محسوب نمی‌شود."
        )

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("🧭 Eligibility / Opportunity Candidate Gate")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("INSUFFICIENT_ACTIVITY_EVIDENCE = عدم وجود شواهد فعالیت کافی")
    lines.append("Opportunity-Candidate = تعداد قراردادهایی که شواهد فعالیت صریح یا عمق دوطرفه TSETMC دارند.")
    lines.append("Ranking-Rows = تعداد ردیف‌هایی که Economic Scoring Engine برای آن‌ها امتیاز معتبر ساخته است.")
    lines.append("OPPORTUNITY_CANDIDATE = شواهد فعالیت صریح یا عمق دوطرفه TSETMC")
    lines.append("⚠️ Candidate و Economic Score به معنی سیگنال خرید/فروش، بازده مورد انتظار یا احتمال سود نیستند.")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("🏆 رتبه‌بندی اقتصادی TSETMC")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    if snapshot.get("report_mode") == "TRADING_ACTIVITY":
        lines.append("مبنای ترتیب: ارزش معاملات، سپس حجم معاملات و تعداد معاملات؛ بدون استفاده از امتیاز اقتصادی.")
        for idx, item in enumerate(rows, 1):
            canonical = item.get("canonical") or {}
            lines.append(
                f"#{idx} {canonical.get('نماد') or 'داده موجود نیست'} | ارزش {number(canonical.get('ارزش معاملات'))} | حجم {number(canonical.get('حجم معاملات'))} | تعداد معاملات {number(canonical.get('تعداد معاملات'))}"
            )
    else:
        rankable = [x for x in ranking.get("ranking_rows", []) if x.get("economic_score") is not None][:len(rows)]
        if rankable:
            lines.append("مبنای ترتیب: امتیاز اقتصادی شش‌بلوک؛ وزن‌ها: نقدشوندگی 20، ارزش‌گذاری 25، Payoff 18، زمان 15، Greeks 12، Market 10. امتیاز اقتصادی کارایی نسبی اقتصادی را نشان می‌دهد و بازده مورد انتظار یا احتمال سود را ادعا نمی‌کند.")
            lines.append("⚠️ بلوک یا عامل فاقد شواهد TSETMC در همان ردیف از امتیاز آن ردیف حذف و وزن بلوک‌های دارای شواهد نرمال می‌شود.")
            for x in rankable:
                blocks = " | ".join(
                    f"{block}={x['block_scores'].get(block) if x['block_scores'].get(block) is not None else 'داده موجود نیست'}"
                    for block in ("LIQUIDITY", "VALUATION", "PAYOFF", "TIME", "GREEKS", "MARKET")
                )
                lines.append(
                    f"#{x['rank']} {x.get('symbol') or 'داده موجود نیست'} | امتیاز کل {x['economic_score']:.2f}/100 | {blocks}"
                )
        else:
            lines.append("داده کافی برای رتبه‌بندی شش‌بلوک وجود ندارد.")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📈 روند تکنیکال سهم‌های پایه — داده روزانه TSETMC")
    lines.append("این شاخص‌ها توصیفی‌اند و به‌تنهایی سیگنال خرید، فروش یا پیش‌بینی صف خرید نیستند.")
    underlying_context = snapshot.get("underlying_context") or {}
    for underlying_id, trend in (underlying_context.get("instruments") or {}).items():
        underlying_symbol = next((
            (row.get("identity") or {}).get("underlying_symbol")
            for row in rows
            if str((row.get("identity") or {}).get("underlying_id") or "") == underlying_id
        ), None)
        lines.append(
            f"{underlying_symbol or underlying_id} | روند: {trend.get('trend_state', 'داده موجود نیست')} | "
            f"بازده ۵ جلسه: {percent(trend.get('return_5_sessions_pct'))} | "
            f"بازده ۲۰ جلسه: {percent(trend.get('return_20_sessions_pct'))} | "
            f"RSI14: {number(trend.get('rsi_14'))} | "
            f"SMA20: {number(trend.get('sma_20'))} | SMA50: {number(trend.get('sma_50'))} | "
            f"نسبت حجم ۵/۲۰: {number(trend.get('volume_ratio_5_to_20'))} | "
            f"عمق خرید/فروش ۵ سطح: {number(trend.get('bid_ask_volume_ratio_5'))} | "
            f"قدرت حقیقی خرید/فروش: {number(trend.get('individual_power_ratio'))} | "
            f"قدرت حقوقی خرید/فروش: {number(trend.get('legal_power_ratio'))} | "
            f"وضعیت حقیقی/حقوقی: {trend.get('client_type_status', 'داده موجود نیست')} | "
            f"دریافت سفارش‌ها: {trend.get('orderbook_retrieved_at', 'داده موجود نیست')} | "
            f"فاصله تا سقف مجاز روز: {percent(trend.get('upper_limit_headroom_pct'))}"
        )
    lines.append(
        f"وضعیت دریافت روند پایه‌ها: {underlying_context.get('status', 'داده موجود نیست')} | "
        f"تعداد پایه‌ها: {underlying_context.get('instrument_count', 0)}"
    )
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("🧾 شواهد فروش صادراتی از گزارش‌های ماهانه کدال")
    lines.append("این بخش فقط افشای صریح شرکت را گزارش می‌کند؛ نبود داده به معنی نبود صادرات نیست و ارز یورو به‌جای دلار تلقی نمی‌شود.")
    codal_context = snapshot.get("codal_export_context") or {}
    for symbol, evidence in (codal_context.get("symbols") or {}).items():
        status = evidence.get("status", "داده موجود نیست")
        period = evidence.get("period_end_jalali") or "داده موجود نیست"
        title = evidence.get("title") or "گزارش ماهانه در دسترس نیست"
        if status == "EXPORT_DISCLOSED":
            parsed = evidence.get("parsed_export_evidence") or {}
            product = parsed.get("product_sales") or {}
            currencies = (parsed.get("foreign_currency_sales") or {}).get("currencies") or []
            currency_text = "، ".join(
                f"{x.get('currency')}: {number(x.get('month_foreign_amount'))} | معادل ریالی {number(x.get('month_rial_amount_million_irr'))} میلیون ریال"
                for x in currencies
            ) or "تفکیک ارز در گزارش موجود نیست"
            lines.append(
                f"{symbol} | صادرات افشا شده | دوره {period} | "
                f"فروش صادراتی ماه: {number(product.get('month_total_million_irr'))} میلیون ریال | "
                f"تجمعی: {number(product.get('cumulative_total_million_irr'))} میلیون ریال"
            )
            lines.append(f"ارزهای افشاشده: {currency_text} | USD صریحاً افشا شده: {'بله' if evidence.get('usd_currency_disclosed') else 'خیر/در این گزارش موجود نیست'}")
        elif status == "NO_EXPORT_REVENUE_DISCLOSED":
            lines.append(f"{symbol} | در آخرین گزارش ماهانه، مبلغ فروش صادراتی مثبت افشا نشده | دوره {period}")
        else:
            lines.append(f"{symbol} | وضعیت صادرات: {status} | {title}")
        if evidence.get("tracing_no"):
            lines.append(f"کد رهگیری کدال: {evidence.get('tracing_no')} | انتشار: {evidence.get('publish_datetime_jalali') or 'داده موجود نیست'}")
        if evidence.get("report_url"):
            lines.append(f"منبع: {evidence.get('report_url')}")
    lines.append(
        f"وضعیت دریافت شواهد کدال: {codal_context.get('status', 'داده موجود نیست')} | "
        f"تعداد نمادها: {codal_context.get('symbol_count', 0)}"
    )
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📰 افشاهای رسمی اخیر شرکت‌ها در کدال")
    lines.append("فقط عنوان و زمان انتشار اطلاعیه گزارش می‌شود؛ جهت اثر یا مثبت/منفی بودن خبر حدس زده نمی‌شود.")
    event_context = snapshot.get("codal_event_context") or {}
    for symbol, event_data in (event_context.get("symbols") or {}).items():
        events = event_data.get("events") or []
        if not events:
            lines.append(f"{symbol} | اطلاعیه قابل بازیابی نیست | وضعیت: {event_data.get('status')}")
            continue
        for event in events[:2]:
            tags = "،".join(event.get("tags") or [])
            lines.append(
                f"{symbol} | {event.get('publish_datetime_jalali') or 'زمان ناموجود'} | "
                f"{tags} | {event.get('title')}"
            )
            lines.append(f"کد رهگیری: {event.get('tracing_no')} | منبع: {event.get('report_url')}")
    lines.append(
        f"وضعیت دریافت اطلاعیه‌های کدال: {event_context.get('status', 'داده موجود نیست')} | "
        f"تعداد نمادها: {event_context.get('symbol_count', 0)}"
    )
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    for idx, item in enumerate(rows, 1):
        canonical = item.get("canonical", {})
        identity = item.get("identity", {})
        lines.extend([
            f"🔹 {idx}. {canonical.get('نماد') or 'داده موجود نیست'}",
            f"نوع: {identity.get('contract_type') or 'داده موجود نیست'} | ID: {identity.get('instrument_id') or 'داده موجود نیست'}",
            f"پایه: {canonical.get('قیمت سهم پایه') if canonical.get('قیمت سهم پایه') is not None else 'داده موجود نیست'}",
            f"اعمال: {number(canonical.get('قیمت اعمال'))} | آخرین: {number(canonical.get('آخرین قیمت'))}",
            f"پایانی: {number(canonical.get('قیمت پایانی'))} | حجم: {number(canonical.get('حجم معاملات'))}",
            f"ارزش: {number(canonical.get('ارزش معاملات'))} | اندازه قرارداد: {number(canonical.get('اندازه قرارداد'))}",
            f"سررسید: {canonical.get('تاریخ سررسید') or 'داده موجود نیست'}",
            "━━━━━━━━━━━━━━━━━━━━",
        ])

    return "\n".join(lines), snapshot


def save_tsetmc_report(report, snapshot):
    output = ROOT / "output" / "tsetmc_first"
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "latest_report.txt"
    snapshot_path = output / "latest_snapshot.json"
    universe_snapshot_path = output / "latest_universe_snapshot.json"
    audit_path = output / "latest_source_audit.json"

    # Detailed TSETMC artifacts remain namespaced; Gate6 consumes these
    # canonical root-level production artifacts.
    root = ROOT
    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    canonical_report_path = output / "latest_report.txt"
    canonical_audit_path = output / "latest_audit.json"

    report_path.write_text(report, encoding="utf-8")
    canonical_report_path.write_text(report, encoding="utf-8")
    # latest_snapshot.json is the report snapshot (top-N), while
    # latest_universe_snapshot.json is the complete TSETMC evidence universe.
    report_snapshot = dict(snapshot)
    report_snapshot.pop("universe_rows", None)
    snapshot_path.write_text(
        json.dumps(report_snapshot, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    universe_snapshot = dict(snapshot)
    universe_snapshot["rows"] = universe_snapshot.pop("universe_rows", [])
    universe_snapshot["row_count"] = len(universe_snapshot["rows"])
    universe_snapshot_path.write_text(
        json.dumps(universe_snapshot, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    archive_universe_snapshot(snapshot, ROOT)

    report_sha256 = hashlib.sha256(report.encode("utf-8")).hexdigest()
    audit = {
        "audit_version": "AUDIT-INTEGRITY-1.3",
        "status": "PASS" if snapshot.get("status") == "SUCCESS" else "FAIL",
        "source_of_truth": snapshot.get("source_of_truth"),
        "external_comparison_source": None,
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "row_count": snapshot.get("row_count"),
        "generated_at": snapshot.get("generated_at"),
        "data_mode": snapshot.get("data_mode"),
        "live_refresh_status": snapshot.get("live_refresh_status"),
        "fallback_reason": snapshot.get("fallback_reason"),
        "basis_source_market_timestamp": snapshot.get("market_state", {}).get("latest_source_market_timestamp"),
        "last_known_snapshot": snapshot.get("data_mode") == "LAST_KNOWN_TSETMC_SNAPSHOT",
        "market_watch": snapshot.get("evidence", {}).get("market_watch", {}),
        "best_limits_evidence": {
            "contract": snapshot.get("evidence", {}).get("best_limits_contract", {}),
            "rows": snapshot.get("evidence", {}).get("orderbook_evidence", []),
        },
        "market_state": snapshot.get("market_state", {}),
        "scoring_status": "OFF_FIELD_EVIDENCE_GATE_OPEN" if snapshot.get("report_mode") == "TRADING_ACTIVITY" else "TSETMC_ECONOMIC_SCORING",
        "ranking_status": "OFF" if snapshot.get("report_mode") == "TRADING_ACTIVITY" else "TSETMC_EVIDENCE_RANKING",
        "ranking": snapshot.get("ranking", {}),
        "eligibility": snapshot.get("eligibility", {}),
        "opportunity": snapshot.get("opportunity", {}),
        "signal_shadow": snapshot.get("signal_shadow", {}),
        "live_movement_claim": "NOT_CLAIMED",
        "report_sha256": report_sha256,
    }
    integrity = verify_audit(audit)
    audit["audit_integrity"] = integrity
    if integrity.get("status") != "PASS":
        audit["status"] = "FAIL"
    audit_json = json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False)
    audit_path.write_text(audit_json, encoding="utf-8")
    canonical_audit_path.write_text(audit_json, encoding="utf-8")
    return canonical_report_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate the active V4.1.1 report from TSETMC only."
    )
    parser.add_argument("--symbol", help="Exact TSETMC option symbol prefix filter")
    parser.add_argument("--underlying", help="Exact TSETMC underlying symbol filter")
    parser.add_argument("--top", type=int, default=None)
    parser.add_argument("--flow", type=int, default=None)
    parser.add_argument("--trading-top", action="store_true", help="Rank by explicit TSETMC trading activity")
    args = parser.parse_args()

    report, snapshot = build_tsetmc_report(
        top_count=args.top,
        symbol_prefix=args.symbol,
        underlying_symbol=args.underlying,
        flow=args.flow,
        report_mode="TRADING_ACTIVITY" if args.trading_top else "RANKED",
    )
    report_path = save_tsetmc_report(report, snapshot)

    print(report)
    print("\nREPORT_FILE =", report_path)
    print("SOURCE_OF_TRUTH = TSETMC")
    print("EXTERNAL_COMPARISON_SOURCE = NONE")
    print("DATA_MODE =", snapshot.get("data_mode"))
    print("LIVE_REFRESH_STATUS =", snapshot.get("live_refresh_status"))
    print("SCORING_STATUS =", snapshot.get("ranking", {}).get("mode"))
    print("RANKING_STATUS =", snapshot.get("ranking", {}).get("status"))
    print("LIVE_MOVEMENT_CLAIM = NOT_CLAIMED")


if __name__ == "__main__":
    main()
