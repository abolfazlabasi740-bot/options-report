#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BASE SHARE OPPORTUNITY SCORE V2 report; TSETMC-only; descriptive ranking."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from tsetmc_first_source import build_tsetmc_snapshot
from underlying_trend_engine import fetch_underlying_context
from base_share_opportunity_engine_v2 import score_opportunity, ENGINE_VERSION

ROOT = Path(__file__).resolve().parent
TEHRAN = ZoneInfo("Asia/Tehran")

def main():
    snap = build_tsetmc_snapshot(flow=None, max_instruments=None, symbol_prefix=None)
    if snap.get("source_of_truth") != "TSETMC":
        raise RuntimeError("TSETMC_SOURCE_OF_TRUTH_REQUIRED")

    underlyings = {}
    for row in snap.get("rows") or []:
        if not isinstance(row, dict):
            continue
        ident = row.get("identity") or {}
        uid = str(ident.get("underlying_id") or "").strip()
        symbol = str(ident.get("underlying_symbol") or "").strip()
        if uid and symbol:
            underlyings[uid] = symbol

    context_result = fetch_underlying_context(sorted(underlyings), include_board=True)
    contexts = context_result.get("instruments") or {}
    ranked = []
    for uid, symbol in underlyings.items():
        ctx = contexts.get(str(uid))
        if not isinstance(ctx, dict):
            ctx = {}
        scored = score_opportunity(ctx)
        ranked.append({
            "instrument_id": str(uid),
            "symbol": symbol,
            **scored,
            "source": "TSETMC",
            "history_status": ctx.get("status"),
            "history_count": ctx.get("history_count"),
            "latest_market_date": ctx.get("latest_market_date"),
            "last_price": ctx.get("last_price"),
            "last_close": ctx.get("last_close"),
            "sma_5": ctx.get("sma_5"),
            "sma_10": ctx.get("sma_10"),
            "sma_20": ctx.get("sma_20"),
            "sma_50": ctx.get("sma_50"),
            "macd_12_26": ctx.get("macd_12_26"),
            "volume_ratio_5_to_20": ctx.get("volume_ratio_5_to_20"),
            "value_ratio_5_to_20": ctx.get("value_ratio_5_to_20"),
            "individual_power_ratio": ctx.get("individual_power_ratio"),
            "orderbook_imbalance_5": ctx.get("orderbook_imbalance_5"),
            "early_move": ctx.get("early_move"),
        })

    ranked.sort(key=lambda x: (x.get("final_score") is None, -(x.get("final_score") or 0.0)))
    report = [
        "گزارش فرصت‌یابی سهم پایه — BASE SHARE OPPORTUNITY V2",
        "=" * 62,
        "منبع حقیقت: TSETMC | نسخه موتور: " + ENGINE_VERSION,
        "دامنه: سهم‌های پایه‌ای که در Universe فعلی اختیار معامله شناسایی شده‌اند؛ نه کل بازار سهام.",
        "امتیاز: 0 تا 100 | خروجی توصیفی است و سیگنال خرید/فروش نیست.",
        "داده مفقود نه صفرگذاری شده و نه با حدس جایگزین شده؛ وزن مؤلفه‌های موجود نرمال شده است.",
        "RSI بالای 70 و به‌ویژه بالای 80، رشد شدید بدون تأیید حجم و وضعیت اصلاح در کیفیت نقطه ورود اثر منفی دارند.",
        "BestLimits تا عبور از دروازه شواهد وارد امتیاز نمی‌شود؛ بنیادی و Strategy Fit نیز تا فراهم‌شدن داده معتبر امتیاز نمی‌گیرند.",
        f"تعداد سهم پایه: {len(ranked)}",
        "=" * 62,
    ]
    for i, row in enumerate(ranked, 1):
        score = row.get("final_score")
        report.append(
            f"#{i} {row['symbol']} | امتیاز={score if score is not None else 'داده موجود نیست'}"
            f" | کلاس={row.get('classification')} | پوشش شواهد={row.get('evidence_coverage_pct')}%"
            f" | اطمینان={row.get('confidence')}"
        )
        report.append(
            f"   روند={row.get('components', {}).get('trend', {}).get('score')}"
            f" | مومنتوم={row.get('components', {}).get('momentum', {}).get('score')}"
            f" | تکنیکال={row.get('components', {}).get('technical', {}).get('score')}"
            f" | حجم/ارزش={row.get('components', {}).get('volume_value', {}).get('score')}"
        )
        report.append(
            f"   Early-Move={row.get('components', {}).get('early_move', {}).get('score')}"
            f" | تابلو={row.get('components', {}).get('board', {}).get('score')}"
            f" | کیفیت ورود={row.get('components', {}).get('entry_quality', {}).get('score')}"
            f" | RSI14={row.get('rsi_14')}"
        )
        report.append(
            f"   بازده 5/20 جلسه={row.get('return_5_sessions_pct')}/{row.get('return_20_sessions_pct')}"
            f" | نسبت حجم/ارزش 5/20={row.get('volume_ratio_5_to_20')}/{row.get('value_ratio_5_to_20')}"
        )
        report.append("   هشدارها=" + (", ".join(row.get("warnings") or []) or "موردی ثبت نشد"))
        report.append("   مؤلفه‌های فاقد داده=" + (", ".join(row.get("unavailable_families") or []) or "هیچ‌کدام"))
        report.append("-" * 62)

    payload = {
        "report_version": "BASE-SHARE-OPPORTUNITY-V2",
        "engine_version": ENGINE_VERSION,
        "generated_at": datetime.now(TEHRAN).isoformat(),
        "source_of_truth": "TSETMC",
        "source_snapshot_sha256": snap.get("snapshot_sha256"),
        "data_mode": snap.get("data_mode"),
        "selection_reason": snap.get("selection_reason"),
        "underlying_count": len(ranked),
        "rows": ranked,
        "missing_policy": "EXCLUDED_FROM_DENOMINATOR_NO_IMPUTATION",
        "buy_sell_signal": "NOT_GENERATED",
    }
    out = ROOT / "output" / "base_share"
    out.mkdir(parents=True, exist_ok=True)
    txt = "\n".join(report)
    (out / "latest_opportunity_v2_report.txt").write_text(txt, encoding="utf-8")
    (out / "latest_opportunity_v2_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(txt)
    print("\nREPORT_FILE =", out / "latest_opportunity_v2_report.txt")
    print("REPORT_JSON =", out / "latest_opportunity_v2_report.json")
    print("REPORT_SHA256 =", hashlib.sha256(txt.encode("utf-8")).hexdigest())
    print("BASE_SHARE_ENGINE_VERSION =", ENGINE_VERSION)
    print("BASE_SHARE_BUY_SELL_SIGNAL = OFF")

if __name__ == "__main__":
    main()
