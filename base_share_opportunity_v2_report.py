#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BASE SHARE OPPORTUNITY SCORE V2 report; TSETMC-only; descriptive ranking."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from tsetmc_first_source import build_tsetmc_snapshot
from underlying_trend_engine import fetch_underlying_context
from base_share_opportunity_engine_v2 import score_opportunity, ENGINE_VERSION

ROOT = Path(__file__).resolve().parent
TEHRAN = ZoneInfo("Asia/Tehran")


def _num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _expiry(value):
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        if len(text) == 8 and text.isdigit():
            return datetime.strptime(text, "%Y%m%d").date()
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _option_quality(rows, underlying_id, as_of):
    """Aggregate explicit active and liquid option evidence for an underlying."""
    related = [
        row for row in rows
        if str((row.get("identity") or {}).get("underlying_id") or "").strip() == str(underlying_id)
    ]
    active = liquid = traded = two_sided = unknown_expiry = 0
    for row in related:
        identity = row.get("identity") or {}
        canonical = row.get("canonical") or {}
        expiry = _expiry(identity.get("end_date") or canonical.get("تاریخ سررسید"))
        if expiry is None:
            unknown_expiry += 1
            continue
        if expiry <= as_of:
            continue
        active += 1
        market = row.get("market_watch_fields") or {}
        volume = _num(market.get("volume"))
        trades = _num(market.get("trade_count"))
        bid = _num(market.get("bid_quantity"))
        ask = _num(market.get("ask_quantity"))
        is_traded = volume is not None and volume > 0 and trades is not None and trades > 0
        is_two_sided = bid is not None and bid > 0 and ask is not None and ask > 0
        traded += int(is_traded)
        two_sided += int(is_two_sided)
        liquid += int(is_traded or is_two_sided)
    if active == 0:
        status = "UNVERIFIED" if unknown_expiry else "BLOCKED"
    elif liquid == 0:
        status = "BLOCKED"
    else:
        status = "PASS"
    return {
        "status": status,
        "contracts_total": len(related),
        "active_contracts": active,
        "liquid_contracts": liquid,
        "traded_contracts": traded,
        "two_sided_contracts": two_sided,
        "liquidity_coverage_pct": round(liquid / active * 100.0, 2) if active else None,
        "unknown_expiry_contracts": unknown_expiry,
        "rule": "ACTIVE_EXPIRY_AND_TRADED_OR_TWO_SIDED_EVIDENCE",
    }

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

    now = datetime.now(TEHRAN)
    snapshot_rows = [row for row in snap.get("rows") or [] if isinstance(row, dict)]
    option_quality = {
        uid: _option_quality(snapshot_rows, uid, now.date())
        for uid in underlyings
    }
    underlyings = {
        uid: symbol for uid, symbol in underlyings.items()
        if option_quality[uid]["status"] != "BLOCKED"
    }
    is_trading_day = now.weekday() in {5, 6, 0, 1, 2}
    board_live_window = is_trading_day and time(9, 0) <= now.time() <= time(12, 30)
    # Current client/order-book fields are fetched only during the live TSETMC session.
    # Outside that window, score retained daily history and report board coverage as unavailable.
    context_result = fetch_underlying_context(sorted(underlyings), include_board=board_live_window)
    contexts = context_result.get("instruments") or {}
    ranked = []
    for uid, symbol in underlyings.items():
        ctx = contexts.get(str(uid))
        if not isinstance(ctx, dict):
            ctx = {}
        ctx = dict(ctx)
        ctx["option_quality"] = option_quality.get(uid)
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
            "macd_pct": ctx.get("macd_pct"),
            "volume_ratio_5_to_20": ctx.get("volume_ratio_5_to_20"),
            "volume_ratio_5_to_50": ctx.get("volume_ratio_5_to_50"),
            "value_ratio_5_to_20": ctx.get("value_ratio_5_to_20"),
            "individual_power_ratio": ctx.get("individual_power_ratio"),
            "orderbook_imbalance_5": ctx.get("orderbook_imbalance_5"),
            "early_move": ctx.get("early_move"),
            "atr_14": ctx.get("atr_14"),
            "atr_14_pct": ctx.get("atr_14_pct"),
            "volatility_20_pct": ctx.get("volatility_20_pct"),
            "history_age_days": ctx.get("history_age_days"),
            "freshness_status": ctx.get("freshness_status"),
            "option_quality": option_quality.get(uid),
        })

    ranked.sort(key=lambda x: (
        x.get("final_score") is None,
        -(x.get("final_score") or 0.0),
        -(x.get("evidence_coverage_pct") or 0.0),
        -((x.get("option_quality") or {}).get("liquidity_coverage_pct") or 0.0),
        -((x.get("components") or {}).get("entry_quality", {}).get("score") or 0.0),
        x.get("symbol") or "",
    ))
    # Report the actual latest market date evidenced by the retained daily histories.
    # Do not equate report-generation time with market-data time.
    history_dates = sorted({
        str(row.get("latest_market_date"))
        for row in ranked
        if row.get("latest_market_date") not in (None, "")
    })
    latest_history_date = history_dates[-1] if history_dates else None
    history_date_coverage = sum(1 for row in ranked if row.get("latest_market_date") not in (None, ""))
    source_mode = str(snap.get("data_mode") or "DATA_MODE_UNAVAILABLE")
    selection_reason = str(snap.get("selection_reason") or "SELECTION_REASON_UNAVAILABLE")
    source_hash = str(snap.get("snapshot_sha256") or "SNAPSHOT_HASH_UNAVAILABLE")
    report = [
        "گزارش فرصت‌یابی سهم پایه — BASE SHARE OPPORTUNITY V2.1",
        "=" * 62,
        "منبع حقیقت: TSETMC | نسخه موتور: " + ENGINE_VERSION,
        "زمان تولید گزارش: " + datetime.now(TEHRAN).isoformat(),
        "آخرین تاریخ بازار در تاریخچه سهم‌های بررسی‌شده: " + (latest_history_date or "اطلاعات موجود نیست"),
        f"پوشش تاریخچه: {history_date_coverage}/{len(ranked)} سهم دارای تاریخ آخرین داده",
        "حالت داده منبع اختیار: " + source_mode,
        "دلیل انتخاب snapshot: " + selection_reason,
        "هش snapshot منبع: " + source_hash,
        "دامنه: سهم‌های پایه‌ای که در Universe فعلی اختیار معامله شناسایی شده‌اند؛ نه کل بازار سهام.",
        f"تابلوی زنده: {'در بازه مجاز بازار درخواست می‌شود' if board_live_window else 'به‌روزرسانی نشده؛ از تاریخچه معتبر موجود استفاده می‌شود'}",
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
        quality = row.get("option_quality") or {}
        report.append(
            f"OPTION_QUALITY={quality.get('status')}"
            f" | ACTIVE={quality.get('active_contracts')}"
            f" | LIQUID={quality.get('liquid_contracts')}"
            f" | COVERAGE={quality.get('liquidity_coverage_pct')}%"
        )
        report.append("-" * 62)

    payload = {
        "report_version": "BASE-SHARE-OPPORTUNITY-V2.2",
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
