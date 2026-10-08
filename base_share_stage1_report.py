#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage-1 Base Shares report: option-enabled underlyings only, TSETMC evidence."""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from tsetmc_first_source import build_tsetmc_snapshot
from underlying_context_shadow import fetch_underlying_context
from underlying_intelligence_engine import build_underlying_intelligence

ROOT = Path(__file__).resolve().parent
TEHRAN = ZoneInfo("Asia/Tehran")

def main():
    snapshot = build_tsetmc_snapshot(flow=None, max_instruments=None, symbol_prefix=None)
    rows = list(snapshot.get("rows") or [])
    underlyings = {}
    for row in rows:
        ident = row.get("identity") or {}
        uid = str(ident.get("underlying_id") or "").strip()
        usym = str(ident.get("underlying_symbol") or "").strip()
        if uid and usym:
            underlyings[uid] = usym

    ids = sorted(underlyings)
    context = fetch_underlying_context(ids, include_board=True)
    intelligence = build_underlying_intelligence(context.get("instruments") or {})

    ranked = []
    for uid, analysis in (intelligence.get("instruments") or {}).items():
        if not isinstance(analysis, dict):
            continue
        ranked.append({
            "instrument_id": uid,
            "symbol": underlyings.get(uid),
            "bias": analysis.get("bias"),
            "confidence": analysis.get("confidence"),
            "score": analysis.get("score"),
            "evidence_count": analysis.get("evidence_count"),
            "bullish_evidence_count": analysis.get("bullish_evidence_count"),
            "bearish_evidence_count": analysis.get("bearish_evidence_count"),
            "trend_state": (context.get("instruments", {}).get(uid) or {}).get("trend_state"),
            "early_move": (context.get("instruments", {}).get(uid) or {}).get("early_move"),
            "correction_state": (context.get("instruments", {}).get(uid) or {}).get("correction_state"),
            "rsi_14": (context.get("instruments", {}).get(uid) or {}).get("rsi_14"),
            "macd_12_26": (context.get("instruments", {}).get(uid) or {}).get("macd_12_26"),
            "return_5_sessions_pct": (context.get("instruments", {}).get(uid) or {}).get("return_5_sessions_pct"),
            "return_20_sessions_pct": (context.get("instruments", {}).get(uid) or {}).get("return_20_sessions_pct"),
            "volume_ratio_5_to_20": (context.get("instruments", {}).get(uid) or {}).get("volume_ratio_5_to_20"),
            "value_ratio_5_to_20": (context.get("instruments", {}).get(uid) or {}).get("value_ratio_5_to_20"),
            "individual_power_ratio": (context.get("instruments", {}).get(uid) or {}).get("individual_power_ratio"),
            "orderbook_imbalance_5": (context.get("instruments", {}).get(uid) or {}).get("orderbook_imbalance_5"),
            "best_bid_price": (context.get("instruments", {}).get(uid) or {}).get("best_bid_price"),
            "best_ask_price": (context.get("instruments", {}).get(uid) or {}).get("best_ask_price"),
            "source": "TSETMC",
        })

    def key(x):
        s = x.get("score")
        return (s is None, -(float(s) if s is not None else -1e99))
    ranked.sort(key=key)

    report = [
        "📊 سهم‌های پایه — مرحله اول",
        "━━━━━━━━━━━━━━━━━━━━",
        "منبع حقیقت: TSETMC",
        "دامنه: فقط سهم‌های پایه‌ای که در Universe فعلی اختیار معامله برای آن‌ها قرارداد شناسایی شده است.",
        "هدف: شناسایی سهم‌های پایه مستعد رشد؛ بدون تحلیل یا انتخاب کال/پوت.",
        f"تعداد سهم‌های پایه شناسایی‌شده: {len(ranked)}",
        "⚠️ امتیاز زیر «امتیاز شواهد جهت‌دار» است و سیگنال خرید/فروش نیست.",
        "⚠️ داده مفقود حدس زده یا صفرگذاری نشده است.",
        "━━━━━━━━━━━━━━━━━━━━",
        "🏆 رتبه‌بندی سهم‌های پایه",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for i, x in enumerate(ranked, 1):
        report.append(
            f"#{i} {x.get('symbol') or 'داده موجود نیست'} | امتیاز {x.get('score') if x.get('score') is not None else 'داده موجود نیست'} | "
            f"جهت {x.get('bias') or 'داده موجود نیست'} | اعتماد {x.get('confidence') or 'داده موجود نیست'} | "
            f"شواهد صعودی {x.get('bullish_evidence_count') if x.get('bullish_evidence_count') is not None else 'داده موجود نیست'} | "
            f"شواهد نزولی {x.get('bearish_evidence_count') if x.get('bearish_evidence_count') is not None else 'داده موجود نیست'}"
        )
        report.append(
            f"   روند={x.get('trend_state') or 'داده موجود نیست'} | RSI={x.get('rsi_14') if x.get('rsi_14') is not None else 'داده موجود نیست'} | "
            f"MACD={x.get('macd_12_26') if x.get('macd_12_26') is not None else 'داده موجود نیست'} | "
            f"بازده 5/20={x.get('return_5_sessions_pct') if x.get('return_5_sessions_pct') is not None else 'داده موجود نیست'}/"
            f"{x.get('return_20_sessions_pct') if x.get('return_20_sessions_pct') is not None else 'داده موجود نیست'}"
        )
        report.append(
            f"   نسبت حجم 5/20={x.get('volume_ratio_5_to_20') if x.get('volume_ratio_5_to_20') is not None else 'داده موجود نیست'} | "
            f"نسبت ارزش 5/20={x.get('value_ratio_5_to_20') if x.get('value_ratio_5_to_20') is not None else 'داده موجود نیست'} | "
            f"قدرت خرید حقیقی={x.get('individual_power_ratio') if x.get('individual_power_ratio') is not None else 'داده موجود نیست'}"
        )
        report.append(
            f"   عدم‌تعادل سفارش={x.get('orderbook_imbalance_5') if x.get('orderbook_imbalance_5') is not None else 'داده موجود نیست'} | "
            f"وضعیت اصلاح={x.get('correction_state') or 'داده موجود نیست'}"
        )
        report.append("━━━━━━━━━━━━━━━━━━━━")

    payload = {
        "report_version": "BASE-SHARES-STAGE-1",
        "generated_at": datetime.now(TEHRAN).isoformat(),
        "source_of_truth": "TSETMC",
        "option_universe_rows": len(rows),
        "underlying_count": len(ranked),
        "rows": ranked,
        "intelligence": intelligence,
        "source_snapshot_sha256": snapshot.get("snapshot_sha256"),
    }
    out = ROOT / "output" / "base_share"
    out.mkdir(parents=True, exist_ok=True)
    txt = "\n".join(report)
    (out / "latest_report.txt").write_text(txt, encoding="utf-8")
    (out / "latest_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(txt)
    print("\nBASE_SHARE_REPORT_FILE =", out / "latest_report.txt")
    print("BASE_SHARE_REPORT_JSON =", out / "latest_report.json")
    print("BASE_SHARE_SOURCE = TSETMC")
    print("BASE_SHARE_UNDERLYING_COUNT =", len(ranked))
    print("BASE_SHARE_REPORT_SHA256 =", hashlib.sha256(txt.encode("utf-8")).hexdigest())

if __name__ == "__main__":
    main()
