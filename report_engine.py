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
from underlying_intelligence_engine import build_underlying_intelligence
from economic_scoring_engine import build_economic_ranking
from option_model import attach_option_model_metrics
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


def _attach_canonical_quote_evidence(rows, *, adapter=None, allow_refresh=True):
    """Attach exact TSETMC ClosingPriceInfo evidence to displayed rows only.

    MarketWatch remains the ranking/value source. ClosingPriceInfo is used only
    to bind a displayed instrument to an explicit TSETMC observation timestamp
    and to record quote consistency. Retrieval time is never used as market time.
    """
    if not allow_refresh:
        for row in rows:
            if not isinstance(row.get("canonical_quote_evidence"), dict):
                row["canonical_quote_evidence"] = {"status":"CLOSED_SNAPSHOT_NO_REFRESH","source":"TSETMC","instrument_id":(row.get("identity") or {}).get("instrument_id"),"source_market_timestamp":row.get("source_market_timestamp"),"source_market_timestamp_status":row.get("source_market_timestamp_status","UNAVAILABLE"),"quote_consistency":"NOT_REEVALUATED"}
        return rows
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


def _tradability_gate(row):
    """Hard Stage-1 quality gate for tradability and contract structure."""
    canonical = row.get("canonical") or {}
    identity = row.get("identity") or {}
    try:
        underlying = float(canonical.get("قیمت سهم پایه"))
        premium = float(canonical.get("آخرین قیمت"))
        strike = float(canonical.get("قیمت اعمال"))
    except (TypeError, ValueError):
        return False, "MISSING_PRICE_EVIDENCE"
    if underlying <= 0 or premium <= 0 or strike <= 0:
        return False, "INVALID_PRICE_EVIDENCE"
    activity_values = []
    for key in ("حجم معاملات", "ارزش معاملات", "تعداد معاملات"):
        try:
            value = float(canonical.get(key))
            activity_values.append(value > 0)
        except (TypeError, ValueError):
            activity_values.append(False)
    if not any(activity_values):
        return False, "NO_TRADE_ACTIVITY_EVIDENCE"
    contract_type = str(identity.get("contract_type") or "").upper()
    if contract_type == "CALL" and underlying < strike:
        return False, "OTM_CONTRACT"
    if contract_type == "PUT" and underlying > strike:
        return False, "OTM_CONTRACT"
    if premium < 10:
        return False, "LAST_PRICE_LT_10_IRR"
    if underlying / premium > 20:
        return False, "LEVERAGE_GT_20X"
    premium_ratio = premium / underlying
    if premium_ratio < 0.0005:
        return False, "EXTREME_PREMIUM_TO_UNDERLYING"
    return True, "PASS"


def _directional_eligibility(row, intelligence_map):
    """Bullish->CALL only; Bearish->PUT only; all other states are unconfirmed."""
    identity = row.get("identity") or {}
    underlying_id = str(identity.get("underlying_id") or "").strip()
    contract_type = str(identity.get("contract_type") or "").upper()
    context = intelligence_map.get(underlying_id)
    if not context:
        return False, "UNDERLYING_INTELLIGENCE_UNAVAILABLE"
    bias = str(context.get("bias") or "").upper()
    confidence = str(context.get("confidence") or "").upper()
    if bias == "BULLISH" and confidence in {"HIGH", "MEDIUM"}:
        return (contract_type == "CALL"), "BULLISH_CALL_ONLY" if contract_type == "CALL" else "OPPOSING_DIRECTION_BEARISH_REQUIRED"
    if bias == "BEARISH" and confidence in {"HIGH", "MEDIUM"}:
        return (contract_type == "PUT"), "BEARISH_PUT_ONLY" if contract_type == "PUT" else "OPPOSING_DIRECTION_BULLISH_REQUIRED"
    if bias in {"NEUTRAL", "CONFLICTED", "INSUFFICIENT_DATA", ""}:
        return False, "DIRECTION_UNCONFIRMED"
    return False, "DIRECTION_UNAVAILABLE"


def build_tsetmc_report(*, top_count=None, symbol_prefix=None, underlying_symbol=None, flow=None, report_mode="RANKED"):
    limit = TOP_COUNT if top_count is None else int(top_count)
    if isinstance(limit, bool) or limit <= 0:
        raise ValueError("تعداد قراردادها باید عدد صحیح مثبت باشد")

    adapter = TSETMCAdapter()
    snapshot = build_tsetmc_snapshot(
        adapter=adapter,
        flow=flow,
        max_instruments=None,
        # The canonical/cache snapshot must always be the full TSETMC universe.
        # Any symbol/underlying filter is applied only after the snapshot is built.
        symbol_prefix=None,
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
        # Stage-1 flow:
        #   1) tradability quality gate
        #   2) discovery scoring only to keep underlying-network work bounded
        #   3) underlying intelligence from TSETMC
        #   4) directional eligibility
        #   5) final six-block economic scoring/ranking
        eligibility = classify_universe(rows)
        snapshot["eligibility"] = eligibility

        quality_rows = []
        quality_rejections = {}
        quality_rejection_counts = {}
        for row in rows:
            ok, reason = _tradability_gate(row)
            if ok:
                quality_rows.append(row)
            else:
                instrument_id = str((row.get("identity") or {}).get("instrument_id") or "")
                quality_rejections[instrument_id] = reason
                quality_rejection_counts[reason] = quality_rejection_counts.get(reason, 0) + 1

        discovery = build_economic_ranking(quality_rows)
        discovery_rows = [
            item for item in (discovery.get("ranking_rows") or [])
            if item.get("economic_score") is not None
        ][:75]
        discovery_ids = {str(item.get("instrument_id")) for item in discovery_rows if item.get("instrument_id") is not None}
        discovery_source_rows = [
            row for row in quality_rows
            if str((row.get("identity") or {}).get("instrument_id") or "") in discovery_ids
        ]
        underlying_ids = sorted({
            str((row.get("identity") or {}).get("underlying_id") or "").strip()
            for row in discovery_source_rows
            if str((row.get("identity") or {}).get("underlying_id") or "").strip()
        })
        live_enrichment = snapshot.get("data_mode") == "LIVE_TSETMC_REFRESH"
        snapshot["underlying_context"] = fetch_underlying_context(
            underlying_ids,
            adapter=adapter,
            include_board=live_enrichment,
        ) if underlying_ids else {
            "status": "UNAVAILABLE",
            "source_of_truth": "TSETMC",
            "instrument_count": 0,
            "instruments": {},
        }
        underlying_map = (snapshot.get("underlying_context") or {}).get("instruments") or {}
        snapshot["underlying_intelligence"] = build_underlying_intelligence(underlying_map) if underlying_map else {
            "status": "UNAVAILABLE",
            "engine_version": "TSETMC-UNDERLYING-INTELLIGENCE-1.0",
            "source_of_truth": "TSETMC",
            "instrument_count": 0,
            "instruments": {},
            "production_signal": "OFF",
            "stage": "STAGE_1",
        }
        intelligence_map = snapshot["underlying_intelligence"].get("instruments") or {}

        directional_rows = []
        direction_rejections = {}
        for row in quality_rows:
            instrument_id = str((row.get("identity") or {}).get("instrument_id") or "")
            if instrument_id not in discovery_ids:
                direction_rejections[instrument_id] = "OUTSIDE_DISCOVERY_POOL"
                continue
            ok, reason = _directional_eligibility(row, intelligence_map)
            if ok:
                directional_rows.append(row)
            else:
                direction_rejections[instrument_id] = reason

        ranking_input = directional_rows
        ranking = build_economic_ranking(ranking_input)
        ranking["ranking_scope"] = "DIRECTIONALLY_ELIGIBLE_CANDIDATES"
        ranking["ranking_scope_row_count"] = len(ranking_input)
        ranking["discovery_pool_row_count"] = len(discovery_source_rows)
        ranking["quality_gate_row_count"] = len(quality_rows)
        ranking["quality_gate_rejections"] = len(quality_rejections)
        ranking["quality_gate_rejection_counts"] = quality_rejection_counts
        ranking["direction_gate_rejections"] = len(direction_rejections)
        ranking["eligibility_fallback_used"] = False
        ranking["economic_scoring_enabled"] = True
        ranking["economic_scoring_target_count"] = limit
        ranking["direction_gate"] = {
            "status": "PASS" if directional_rows else "NO_DIRECTIONALLY_ELIGIBLE_CANDIDATES",
            "rule": "BULLISH_CALL_ONLY | BEARISH_PUT_ONLY | NEUTRAL_CONFLICTED_UNCONFIRMED",
            "opposing_direction_excluded_before_final_six_block_scoring": True,
            "eligible_count": len(directional_rows),
            "rejected_count": len(direction_rejections),
        }
        ranking["tradability_gate"] = {
            "status": "PASS" if quality_rows else "NO_QUALITY_CANDIDATES",
            "minimum_last_price_irr": 10,
            "maximum_leverage_x": 20,
            "otm_rule": "CALL: underlying < strike => rejected | PUT: underlying > strike => rejected | ATM retained",
            "minimum_premium_to_underlying": 0.0005,
            "minimum_premium_to_underlying_pct": 0.05,
            "extreme_premium_rule": "premium/underlying < 0.05% => rejected",
            "activity_rule": "at least one of volume/value/trade_count must be positive",
            "eligible_count": len(quality_rows),
            "rejected_count": len(quality_rejections),
            "rejection_counts": quality_rejection_counts,
        }
        snapshot["economic_scoring_enabled"] = True
        snapshot["economic_scoring_target_count"] = limit
        snapshot["ranking"] = ranking
        snapshot["direction_gate"] = ranking["direction_gate"]
        snapshot["tradability_gate"] = ranking["tradability_gate"]

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

        opportunity = build_opportunity_candidates(ranking_input, ranking, eligibility)
        snapshot["opportunity"] = opportunity

        ranked_order = {
            item.get("instrument_id"): item.get("rank")
            for item in ranking.get("ranking_rows", [])
        }
        ranked_source_rows = list(ranking_input)
        ranked_source_rows.sort(
            key=lambda row: (
                ranked_order.get((row.get("identity") or {}).get("instrument_id")) is None,
                ranked_order.get((row.get("identity") or {}).get("instrument_id")) or 10**9,
            )
        )
        rows = ranked_source_rows[:limit]
        score_by_id = {
            str(item.get("instrument_id")): item.get("economic_score")
            for item in ranking.get("ranking_rows", [])
            if item.get("instrument_id") is not None
        }
        for row in rows:
            rid = str((row.get("identity") or {}).get("instrument_id") or "")
            row["_economic_score"] = score_by_id.get(rid)
            if row["_economic_score"] is None:
                raise RuntimeError(f"RANKED_REPORT_BLOCKED: missing_score_for_instrument={rid}")
        snapshot["report_mode"] = "RANKED"

        _attach_canonical_quote_evidence(rows, adapter=adapter, allow_refresh=live_enrichment)
        if live_enrichment:
            attach_option_model_metrics(rows, adapter)
        else:
            for row in rows:
                row["option_model"] = {
                    "status": "CLOSED_SNAPSHOT_NO_REFRESH",
                    "source_of_market_inputs": "TSETMC_CLOSED_SNAPSHOT",
                }
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
    basis_timestamp = (
        market_state["latest_source_market_timestamp"]
        or mw.get("retrieved_at")
        or snapshot.get("closed_capture_at")
        or snapshot.get("generated_at")
        or "داده موجود نیست"
    )
    basis_date = None
    for _ts in (
        market_state.get("latest_source_market_timestamp"),
        mw.get("retrieved_at"),
        snapshot.get("closed_capture_at"),
        snapshot.get("generated_at"),
    ):
        if _ts:
            try:
                basis_date = datetime.fromisoformat(str(_ts).replace("Z", "+00:00")).astimezone(TEHRAN).date()
                break
            except (TypeError, ValueError):
                pass
    if basis_date is None:
        basis_date = datetime.now(TEHRAN).date()

    ranking_rows = ranking.get("ranking_rows") or []
    ranking_by_id = {str(x.get("instrument_id")): x for x in ranking_rows if x.get("instrument_id") is not None}

    def days_to_expiry(value):
        if not value: return "داده موجود نیست"
        try:
            expiry=datetime.strptime(str(value)[:8],"%Y%m%d").date()
            return str(max(0,(expiry-basis_date).days))
        except (TypeError,ValueError): return "داده موجود نیست"

    def leverage(row):
        c0=row.get("canonical") or {}
        try:
            s0,p0=float(c0.get("قیمت سهم پایه")),float(c0.get("آخرین قیمت"))
            return f"{s0/p0:.2f}x" if s0>0 and p0>0 else "داده موجود نیست"
        except (TypeError,ValueError): return "داده موجود نیست"

    def breakeven_distance(row):
        c0 = row.get("canonical") or {}
        ident = row.get("identity") or {}
        try:
            s = float(c0.get("قیمت سهم پایه"))
            k = float(c0.get("قیمت اعمال"))
            p = float(c0.get("آخرین قیمت"))
            if s <= 0 or k <= 0 or p <= 0:
                return "داده موجود نیست"
            typ = str(ident.get("contract_type") or "").upper()
            breakeven = k + p if typ == "CALL" else k - p if typ == "PUT" else None
            if breakeven is None:
                return "داده موجود نیست"
            return f"{abs(breakeven - s) / s * 100:.2f}%"
        except (TypeError, ValueError):
            return "داده موجود نیست"

    lines=[
        "📊 گزارش ۱۵ فرصت برتر","Optionmarket | TSETMC-ONLY","━━━━━━━━━━━━━━━━━━━━",
        f"وضعیت بازار: {market_state['status']}",
        f"مبنای رتبه‌بندی: امتیاز اقتصادی TSETMC | وضعیت: {ranking.get('status','داده موجود نیست')}",
        f"دامنه رتبه‌بندی: {ranking.get('ranking_scope','داده موجود نیست')}" + (" | تکمیل از ردیف‌های دارای قیمت صریح TSETMC" if ranking.get("eligibility_fallback_used") else ""),
        f"Universe TSETMC: {snapshot.get('universe_row_count',0)} قرارداد",
        f"کاندیدهای گیت کیفیت: {ranking.get('quality_gate_row_count','داده موجود نیست')}",
        f"کاندیدهای مجاز جهت: {ranking.get('ranking_scope_row_count','داده موجود نیست')}",
        f"تعداد قراردادهای نهایی: {snapshot.get('row_count',0)}",
        f"آخرین timestamp منبع: {basis_timestamp}",
        f"تحلیل سهم پایه: {snapshot.get('underlying_intelligence', {}).get('status', 'داده موجود نیست')} | موتور: TSETMC-UNDERLYING-INTELLIGENCE-1.2-CORRECTION-DIRECTIONAL-PRELOCK",
        "پیش‌قفلی / PRE-LOCK: Shadow | تشخیص توالی حجم→قیمت→مومنتوم در جلسه‌های روزانه؛ وارد رتبه‌بندی نشده است.",
        f"گیت جهت: {(snapshot.get('direction_gate') or {}).get('status', 'داده موجود نیست')} | Bullish→CALL | Bearish→PUT | Neutral/Conflicted→عدم تأیید",
        f"گیت کیفیت معاملات: {(snapshot.get('tradability_gate') or {}).get('status', 'داده موجود نیست')} | OTM حذف | قیمت < ۱۰ ریال حذف | اهرم > 20x حذف",
        "ℹ️ فیلد فاقد شواهد مستقیم TSETMC = «داده موجود نیست». این گزارش سیگنال خرید/فروش نیست.",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    ui = snapshot.get("underlying_intelligence", {}).get("instruments") or {}
    for idx,item in enumerate(rows,1):
        c0=item.get("canonical") or {}; ident=item.get("identity") or {}
        score=item.get("_economic_score")
        score_text=f"{float(score):.2f}" if score is not None else "داده موجود نیست"
        rid=str(ident.get("instrument_id") or "")
        rank_item=ranking_by_id.get(rid) or {}
        block_scores=rank_item.get("block_scores") or {}
        context=ui.get(str(ident.get("underlying_id") or "")) or {}
        bias=str(context.get("bias") or "داده موجود نیست")
        confidence=str(context.get("confidence") or "داده موجود نیست")
        score_parts=", ".join(f"{k}={float(v):.1f}" for k,v in block_scores.items() if v is not None) or "داده موجود نیست"
        evidence_list=context.get("evidence") or []
        evidence_text=" | ".join(
            f"{e.get('family')}: {e.get('detail')}"
            for e in evidence_list[:4]
            if isinstance(e, dict) and e.get("detail")
        ) or "داده موجود نیست"
        why_direction = (
            "CALL با Bias صعودی سهم پایه تأیید شده"
            if ident.get("contract_type") == "CALL" and bias == "BULLISH"
            else "PUT با Bias نزولی سهم پایه تأیید شده"
            if ident.get("contract_type") == "PUT" and bias == "BEARISH"
            else "جهت از گیت سهم پایه تأیید نشده"
        )
        model=item.get("option_model") or {}
        delta_text=(
            f"{float(model.get('delta')):.4f}"
            if model.get("status") == "SUCCESS" and model.get("delta") is not None
            else "داده موجود نیست"
        )
        bs_text=(
            number(model.get("black_scholes"))
            if model.get("status") == "SUCCESS" and model.get("black_scholes") is not None
            else "داده موجود نیست"
        )
        lines.extend([
            f"🔹 {idx}. {c0.get('نماد') or 'داده موجود نیست'}",
            f"نوع: {ident.get('contract_type') or 'داده موجود نیست'}",
            f"اعمال: {number(c0.get('قیمت اعمال'))}",
            f"سررسید: {days_to_expiry(c0.get('تاریخ سررسید'))} روز",
            f"آخرین قیمت: {number(c0.get('آخرین قیمت'))}",
            f"پایانی: {number(c0.get('قیمت پایانی'))}",
            f"فاصله سربه‌سر: {breakeven_distance(item)}",
            f"اهرم: {leverage(item)}",
            f"دلتا: {delta_text}",
            f"بلک‌شولز: {bs_text}",
            f"امتیاز: {score_text}/100",
            f"شواهد امتیاز: {score_parts}",
            f"پایه: {ident.get('underlying_symbol') or 'داده موجود نیست'} | Bias={bias} | Confidence={confidence}",
            f"وضعیت اصلاح پایه: {(context.get('correction_state') or 'داده موجود نیست')} | "
            f"افت از سقف اخیر={percent(context.get('correction_from_prior_peak_pct'))}",
            f"شواهد سهم پایه: {evidence_text}",
            f"چرا انتخاب شد: {why_direction}؛ سپس امتیاز اقتصادی و گیت کیفیت معاملاتی اعمال شده است.",
            "━━━━━━━━━━━━━━━━━━━━",
        ])

    bases={}; total_volume=0.0; total_value=0.0; va=False; vala=False; days=[]
    for item in rows:
        c0=item.get("canonical") or {}
        u=str((item.get("identity") or {}).get("underlying_symbol") or "").strip() or "داده موجود نیست"
        bases[u]=bases.get(u,0)+1
        try: total_volume+=float(c0.get("حجم معاملات")); va=True
        except (TypeError,ValueError): pass
        try: total_value+=float(c0.get("ارزش معاملات")); vala=True
        except (TypeError,ValueError): pass
        d=days_to_expiry(c0.get("تاریخ سررسید"))
        if d!="داده موجود نیست": days.append(int(d))
    conc=sorted(bases.items(),key=lambda x:(-x[1],x[0]))
    conc_text=", ".join(f"{k} ({v})" for k,v in conc[:5])
    ui = snapshot.get("underlying_intelligence", {}).get("instruments") or {}
    if ui:
        bullish = sum(1 for x in ui.values() if x.get("bias") == "BULLISH")
        bearish = sum(1 for x in ui.values() if x.get("bias") == "BEARISH")
        conflicted = sum(1 for x in ui.values() if x.get("bias") == "CONFLICTED")
        neutral = sum(1 for x in ui.values() if x.get("bias") == "NEUTRAL")
        lines.extend([
            "🧭 تحلیل سهم‌های پایه — مرحله ۱","━━━━━━━━━━━━━━━━━━━━",
            f"پایه‌های تحلیل‌شده: {len(ui)} | Bullish: {bullish} | Bearish: {bearish} | Neutral: {neutral} | Conflicted: {conflicted}",
        ])
        for uid, item in ui.items():
            context = (snapshot.get("underlying_context", {}).get("instruments") or {}).get(uid) or {}
            lines.append(
                f"پایه {context.get('instrument_id', uid)} | Bias={item.get('bias','N/A')} | "
                f"Confidence={item.get('confidence','N/A')} | Score={item.get('score','N/A')}"
            )
            correction_state = context.get("correction_state") or "داده موجود نیست"
            correction_confidence = context.get("correction_confidence") or "داده موجود نیست"
            correction_peak = percent(context.get("correction_from_prior_peak_pct"))
            lines.append(
                f"اصلاح {context.get('instrument_id', uid)} | وضعیت={correction_state} | "
                f"اعتماد={correction_confidence} | افت از سقف اخیر={correction_peak}"
            )
            touched = context.get("touched_upper_limit_today")
            if touched is True:
                lock_state = "LOCKED_TODAY"
            elif touched is False:
                lock_state = "NOT_LOCKED_EVIDENCE"
            else:
                lock_state = "UNAVAILABLE"
            lines.append(
                f"وضعیت قفلی {context.get('instrument_id', uid)} | {lock_state}"
            )
            prelock = context.get("early_move", {}).get("pre_lock_sequence") or {}
            if prelock.get("status") == "PASS":
                lines.append(
                    f"پیش‌قفلی {context.get('instrument_id', uid)} | وضعیت={prelock.get('state','N/A')} | "
                    f"Sequence={prelock.get('sequence','N/A')} | جهت={prelock.get('sequence_direction','N/A')} | "
                    f"Confidence={prelock.get('confidence','N/A')} | "
                    f"فاصله تا سقف={percent(prelock.get('distance_to_upper_limit_pct'))}"
                )
        lines.extend([
            "این بخش توصیفی است؛ اصلاح، Early-Move، PRE-LOCK و LOCKED به‌صورت Shadow/شواهد توصیفی محاسبه می‌شوند و هنوز گیت رتبه‌بندی نیستند. جهت توالی قبل از اعلام PRE-LOCK اعتبارسنجی می‌شود؛ توالی فقط در سطح جلسه‌های روزانه است و ادعای ترتیب درون‌روزی یا پیش‌بینی قطعی قفل‌شدن نمی‌کند.",
            "━━━━━━━━━━━━━━━━━━━━",
        ])

    lines.extend([
        f"📈 تحلیل جامع {len(rows)} فرصت","━━━━━━━━━━━━━━━━━━━━",
        "1) نقدشوندگی و فعالیت",
        f"حجم معاملات مجموع: {number(total_volume) if va else 'داده موجود نیست'}",
        f"ارزش معاملات مجموع: {number(total_value) if vala else 'داده موجود نیست'}",
        f"تمرکز بر پایه‌ها: {conc_text or 'داده موجود نیست'}",
        "OI و تغییرات OI: داده موجود نیست؛ تفسیر جریان موقعیت‌ها انجام نشده است.","",
        "2) اهرم، فاصله سربه‌سر و زمان",
        f"بازه سررسید: {min(days)} تا {max(days)} روز" if days else "بازه سررسید: داده موجود نیست",
        "سررسید نزدیک، حساسیت به فرسایش زمانی را افزایش می‌دهد؛ اهرم بالا به‌تنهایی مبنای تصمیم نیست.",
        "دلتا و بلک‌شولز از مدل Black-Scholes با نوسان تاریخی TSETMC محاسبه شده‌اند؛ نرخ بدون ریسک مدل 0% و سود تقسیمی 0% است و این دو عدد داده مشاهده‌شده بازار نیستند.","",
        "3) تمرکز ریسک",
        f"تعداد پایه‌های متمایز: {len(bases)}",
        f"بیشترین تمرکز: {conc_text or 'داده موجود نیست'}",
        "تمرکز چند قرارداد روی یک پایه، تنوع واقعی سبد را کاهش می‌دهد.","",
        "4) چرایی انتخاب رتبه‌ها",
        "هر قرارداد ابتدا از گیت کیفیت عبور کرده، سپس جهت آن با تحلیل سهم پایه کنترل شده و در نهایت با امتیاز اقتصادی TSETMC رتبه گرفته است. Early-Move فعلاً فقط شواهد تغییر و توالی را گزارش می‌کند و در رتبه‌بندی دخالت ندارد.",
        "امتیازهای بلوکی نمایش‌داده‌شده شواهد عددی رتبه‌بندی هستند؛ داده‌های غایب صفر فرض نشده‌اند.","",
        "5) جمع‌بندی",
        "فرصت‌ها: قراردادهای با امتیاز اقتصادی و شواهد فعالیت TSETMC در صدر فهرست قرار گرفته‌اند.",
        "ریسک‌ها: سررسید نزدیک، اهرم، تمرکز روی پایه و تفاوت بین ارزش Black-Scholes مدل و قیمت بازار.",
        "پایش جلسه بعد: آخرین/پایانی، حجم، ارزش معاملات، عمق بازار، تغییرات نوسان تاریخی و اختلاف قیمت مدل با بازار.",
        "⚠️ این خروجی رتبه‌بندی و تحلیل توصیفی است و BUY/SELL خودکار تولید نمی‌کند.","━━━━━━━━━━━━━━━━━━━━",
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
