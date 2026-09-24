#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TSETMC-only production source boundary for OptimusAI V4.1.1.

No legacy workbook is consumed by the active runtime.
Historical external-source artifacts remain archival evidence only.

The report is operational while keeping live-market claims fail-closed:
- SESSION_OPEN: source may be current, but scoring remains gated.
- OFFMARKET: the latest TSETMC snapshot is reportable, never as live movement.
- SINGLE_SOURCE_OBSERVATION: movement is not proven from one observation.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from tsetmc_first_source import build_tsetmc_snapshot

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
    if session == "OFFMARKET":
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
        "unique_timestamp_count": observation["unique_timestamp_count"],
        "latest_source_market_timestamp": observation["latest_source_market_timestamp"],
    }


def build_tsetmc_report(*, top_count=None, symbol_prefix=None, flow=1):
    limit = TOP_COUNT if top_count is None else int(top_count)
    if isinstance(limit, bool) or limit <= 0:
        raise ValueError("تعداد قراردادها باید عدد صحیح مثبت باشد")

    snapshot = build_tsetmc_snapshot(
        flow=flow,
        max_instruments=limit,
        symbol_prefix=symbol_prefix,
    )
    rows = list(snapshot.get("rows", []))[:limit]
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
    lines = [
        "📊 گزارش اولیه بازار اختیار معامله — TSETMC-ONLY",
        "━━━━━━━━━━━━━━━━━━━━",
        "📥 منبع حقیقت: TSETMC",
        f"📌 وضعیت جلسه بازار: {market_state['session_state']}",
        f"📌 وضعیت مشاهده منبع: {market_state['status']}",
        f"📌 تعداد timestamp مشاهده‌شده از منبع: {market_state['unique_timestamp_count']}",
        f"📌 آخرین timestamp صریح منبع: {market_state['latest_source_market_timestamp'] or 'داده موجود نیست'}",
        f"📌 تعداد رکوردهای Market-Watch: {mw.get('record_count', 0)}",
        f"📌 تعداد قراردادهای قابل استخراج: {snapshot.get('row_count', 0)}",
        f"⏱ زمان دریافت: {mw.get('retrieved_at', 'داده موجود نیست')}",
        f"🔐 Snapshot SHA256: {snapshot.get('snapshot_sha256')}",
        "⚠️ امتیازدهی شش‌بلوک و رتبه‌بندی تولیدی تا تکمیل Evidence Gate فعال نیست.",
        "⚠️ هر فیلد فاقد شواهد مستقیم TSETMC عمداً «داده موجود نیست» باقی می‌ماند.",
    ]

    if market_state["session_state"] == "OFFMARKET":
        lines.append("ℹ️ بازار خارج از جلسه معاملاتی است؛ این خروجی snapshot منبع است و به‌عنوان حرکت زنده بازار تفسیر نمی‌شود.")
    elif market_state["observation_state"] == "SINGLE_SOURCE_OBSERVATION":
        lines.append("ℹ️ timestamp مشاهده‌شده یکتا است؛ حرکت لحظه‌ای بازار اثبات نشده و گزارش live-moving محسوب نمی‌شود.")

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

    report_path.write_text(report, encoding="utf-8")
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    audit = {
        "status": "PASS" if snapshot.get("status") == "SUCCESS" else "FAIL",
        "source_of_truth": snapshot.get("source_of_truth"),
        "external_comparison_source": None,
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "row_count": snapshot.get("row_count"),
        "generated_at": snapshot.get("generated_at"),
        "market_watch": snapshot.get("evidence", {}).get("market_watch", {}),
        "market_state": snapshot.get("market_state", {}),
        "scoring_status": "OFF_FIELD_EVIDENCE_GATE_OPEN",
        "ranking_status": "OFF",
        "live_movement_claim": "NOT_CLAIMED",
    }
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate the active V4.1.1 report from TSETMC only."
    )
    parser.add_argument("--symbol", help="Exact TSETMC symbol prefix filter")
    parser.add_argument("--top", type=int, default=None)
    parser.add_argument("--flow", type=int, default=1)
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
    print("SCORING_STATUS = OFF_FIELD_EVIDENCE_GATE_OPEN")
    print("LIVE_MOVEMENT_CLAIM = NOT_CLAIMED")


if __name__ == "__main__":
    main()
