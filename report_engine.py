#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TSETMC-only production report boundary for OptimusAI V4.1.1.

Reporting remains available outside market hours by using the latest valid
TSETMC snapshot. Cached data is explicitly labelled and never presented as
live movement. Scoring/ranking remain fail-closed behind the evidence gate.
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
from tsetmc_scoring_engine import build_evidence_ranking
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


def build_tsetmc_report(*, top_count=None, symbol_prefix=None, flow=None):
    limit = TOP_COUNT if top_count is None else int(top_count)
    if isinstance(limit, bool) or limit <= 0:
        raise ValueError("تعداد قراردادها باید عدد صحیح مثبت باشد")

    snapshot = build_tsetmc_snapshot(
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
    snapshot["universe_row_count"] = len(rows)
    ranking = build_evidence_ranking(rows)
    snapshot["ranking"] = ranking
    eligibility = classify_universe(rows)
    snapshot["eligibility"] = eligibility
    opportunity = build_opportunity_candidates(rows, ranking, eligibility)
    snapshot["opportunity"] = opportunity

    candidate_ids = set(eligibility.get("candidate_instrument_ids") or [])
    ranked_order = {
        item.get("instrument_id"): item.get("rank")
        for item in ranking.get("ranking_rows", [])
    }
    candidate_rows = [
        row for row in rows
        if (row.get("identity") or {}).get("instrument_id") in candidate_ids
    ]
    candidate_rows.sort(
        key=lambda row: (
            ranked_order.get((row.get("identity") or {}).get("instrument_id")) is None,
            ranked_order.get((row.get("identity") or {}).get("instrument_id")) or 10**9,
        )
    )
    rows = candidate_rows[:limit]
    snapshot["rows"] = rows
    snapshot["row_count"] = len(rows)

    market_state = _market_state(snapshot)
    snapshot["market_state"] = market_state

    def number(value):
        if value in (None, ""):
            return "داده موجود نیست"
        try:
            return f"{float(value):,.2f}".replace(".00", "")
        except (TypeError, ValueError):
            return str(value)

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
        f"📌 INSUFFICIENT_ACTIVITY_EVIDENCE: {eligibility.get('counts', {}).get('INSUFFICIENT_ACTIVITY_EVIDENCE', 0)} | RANKABLE: {eligibility.get('counts', {}).get('RANKABLE', 0)}",
        f"⏱ زمان دریافت/تولید منبع: {mw.get('retrieved_at', 'داده موجود نیست')}",
        f"🔐 Snapshot SHA256: {snapshot.get('snapshot_sha256')}",
        f"📊 وضعیت امتیازدهی: {ranking.get('mode')} | وضعیت رتبه‌بندی: {ranking.get('status')}",
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
    lines.append("RANKABLE = قابل رتبه‌بندی بر اساس شواهد فرمولی")
    lines.append("OPPORTUNITY_CANDIDATE = شواهد فعالیت صریح یا عمق دوطرفه TSETMC")
    lines.append("⚠️ Candidate به معنی سیگنال خرید/فروش یا احتمال سود نیست.")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("🏆 رتبه‌بندی شواهد TSETMC")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    rankable = [x for x in ranking.get("ranking_rows", []) if x.get("score") is not None][:10]
    if rankable:
        for x in rankable:
            lines.append(f"#{x['rank']} {x.get('symbol') or 'داده موجود نیست'} | امتیاز {x['score']:.2f} | بلوک‌های معتبر: {','.join(x.get('supported_blocks', []))}")
    else:
        lines.append("داده کافی برای رتبه‌بندی وجود ندارد.")
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
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )

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
        "scoring_status": "TSETMC_EVIDENCE_RANKING",
        "ranking_status": "TSETMC_EVIDENCE_RANKING",
        "ranking": snapshot.get("ranking", {}),
        "eligibility": snapshot.get("eligibility", {}),
        "opportunity": snapshot.get("opportunity", {}),
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
    parser.add_argument("--symbol", help="Exact TSETMC symbol prefix filter")
    parser.add_argument("--top", type=int, default=None)
    parser.add_argument("--flow", type=int, default=None)
    args = parser.parse_args()

    report, snapshot = build_tsetmc_report(
        top_count=args.top,
        symbol_prefix=args.symbol,
        flow=args.flow,
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
