#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TSETMC-only production source boundary for OptimusAI V4.1.1.

This module deliberately contains no legacy workbook ingestion path.
Historical external-source artifacts remain archival evidence and are not
consumed by the active runtime.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from tsetmc_first_source import build_tsetmc_snapshot

ROOT = Path(__file__).resolve().parent
TEHRAN = ZoneInfo("Asia/Tehran")
TOP_COUNT = 15


def build_tsetmc_report(*, top_count=None, symbol_prefix=None, flow=1):
    """Build an evidence-only report from TSETMC Market-Watch."""
    limit = TOP_COUNT if top_count is None else int(top_count)
    if isinstance(limit, bool) or limit <= 0:
        raise ValueError("تعداد قراردادها باید عدد صحیح مثبت باشد")

    snapshot = build_tsetmc_snapshot(
        flow=flow,
        max_instruments=limit,
        symbol_prefix=symbol_prefix,
    )
    rows = list(snapshot.get("rows", []))[:limit]

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
        f"📌 تعداد رکوردهای Market-Watch: {mw.get('record_count', 0)}",
        f"📌 تعداد قراردادهای قابل استخراج: {snapshot.get('row_count', 0)}",
        f"⏱ زمان دریافت: {mw.get('retrieved_at', 'داده موجود نیست')}",
        f"🔐 Snapshot SHA256: {snapshot.get('snapshot_sha256')}",
        "⚠️ امتیازدهی شش‌بلوک و رتبه‌بندی تولیدی تا تکمیل Evidence Gate فعال نیست.",
        "⚠️ هر فیلد فاقد شواهد مستقیم TSETMC عمداً «داده موجود نیست» باقی می‌ماند.",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

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
    """Persist TSETMC report, raw canonical snapshot and source audit."""
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

    market_watch = snapshot.get("evidence", {}).get("market_watch", {})
    audit = {
        "status": "PASS" if snapshot.get("status") == "SUCCESS" else "FAIL",
        "source_of_truth": snapshot.get("source_of_truth"),
        "external_comparison_source": None,
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "row_count": snapshot.get("row_count"),
        "generated_at": snapshot.get("generated_at"),
        "market_watch": market_watch,
        "scoring_status": "OFF_FIELD_EVIDENCE_GATE_OPEN",
        "ranking_status": "OFF",
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


if __name__ == "__main__":
    main()
