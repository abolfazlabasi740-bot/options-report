#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare the full TSETMC-only plain-symbol trend ranking with the prior history date.

Observed feature changes are descriptive evidence, not causal attribution. This
report never changes score weights and never emits a buy/sell signal.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "base_share"
CURRENT = OUT / "latest_plain_symbol_trend_report.json"
HISTORY = OUT / "daily_history"
REPORT_JSON = OUT / "latest_daily_rank_change_report.json"
REPORT_TXT = OUT / "latest_daily_rank_change_report.txt"
TEHRAN = ZoneInfo("Asia/Tehran")
DIGIT_AT_END = re.compile(r"[0-9\u0660-\u0669\u06F0-\u06F9]$")
NUMERIC_FIELDS = (
    "final_score", "return_5_sessions_pct", "return_20_sessions_pct",
    "rsi_14", "volume_ratio_5_to_20", "value_ratio_5_to_20",
    "macd_12_26", "last_price", "last_close",
)


def canonical_sha256(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def numeric(value):
    if value is None or value == "":
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def data_date(payload: dict) -> str:
    value = str(payload.get("latest_history_date") or "").strip()
    if re.fullmatch(r"\d{8}", value):
        return value
    dates = [str(r.get("latest_market_date")) for r in payload.get("rows", [])
             if re.fullmatch(r"\d{8}", str(r.get("latest_market_date") or ""))]
    return max(dates) if dates else ""


def validate(payload: dict, label: str) -> None:
    if payload.get("source_of_truth") != "TSETMC":
        raise SystemExit(f"{label}_FAIL_SOURCE_NOT_TSETMC")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"{label}_FAIL_ROWS_MISSING")
    seen = set()
    for row in rows:
        symbol = str(row.get("symbol") or "").strip()
        if not symbol:
            raise SystemExit(f"{label}_FAIL_EMPTY_SYMBOL")
        if DIGIT_AT_END.search(symbol):
            raise SystemExit(f"{label}_FAIL_SYMBOL_FILTER:{symbol}")
        if symbol in seen:
            raise SystemExit(f"{label}_FAIL_DUPLICATE_SYMBOL:{symbol}")
        seen.add(symbol)
    claimed = payload.get("report_sha256")
    if claimed:
        check = dict(payload)
        check.pop("report_sha256", None)
        if canonical_sha256(check) != claimed:
            raise SystemExit(f"{label}_FAIL_REPORT_SHA256_MISMATCH")


def index_rows(payload: dict) -> dict:
    return {str(row["symbol"]).strip(): row for row in payload["rows"]}


def rank_map(payload: dict) -> dict:
    return {str(row["symbol"]).strip(): i for i, row in enumerate(payload["rows"], 1)}


def classify_changes(old: dict, new: dict, deltas: dict) -> list[str]:
    reasons = []
    score = deltas.get("final_score")
    if score is not None:
        if score > 0.01:
            reasons.append("امتیاز افزایش یافته")
        elif score < -0.01:
            reasons.append("امتیاز کاهش یافته")
    for field, up, down in (
        ("return_5_sessions_pct", "بازده ۵ جلسه بهتر شده", "بازده ۵ جلسه ضعیف‌تر شده"),
        ("return_20_sessions_pct", "بازده ۲۰ جلسه بهتر شده", "بازده ۲۰ جلسه ضعیف‌تر شده"),
        ("volume_ratio_5_to_20", "نسبت حجم ۵ به ۲۰ جلسه افزایش یافته", "نسبت حجم ۵ به ۲۰ جلسه کاهش یافته"),
        ("value_ratio_5_to_20", "نسبت ارزش ۵ به ۲۰ جلسه افزایش یافته", "نسبت ارزش ۵ به ۲۰ جلسه کاهش یافته"),
        ("rsi_14", "RSI افزایش یافته", "RSI کاهش یافته"),
        ("macd_12_26", "MACD افزایش یافته", "MACD کاهش یافته"),
    ):
        delta = deltas.get(field)
        if delta is not None:
            if delta > 0.000001:
                reasons.append(up)
            elif delta < -0.000001:
                reasons.append(down)
    old_macd, new_macd = numeric(old.get("macd_12_26")), numeric(new.get("macd_12_26"))
    if old_macd is not None and new_macd is not None and old_macd * new_macd < 0:
        reasons.append("علامت MACD عوض شده")
    if old.get("classification") != new.get("classification"):
        reasons.append("کلاس رتبه‌بندی تغییر کرده")
    old_warnings = set(old.get("warnings") or [])
    new_warnings = set(new.get("warnings") or [])
    if new_warnings - old_warnings:
        reasons.append("هشدار جدید ثبت شده")
    if old_warnings - new_warnings:
        reasons.append("برخی هشدارهای قبلی رفع شده")
    return reasons or ["تغییر شاخص‌های قابل‌مشاهده محدود یا ناموجود است؛ علت قطعی قابل‌اثبات نیست"]


def main():
    if not CURRENT.exists():
        raise SystemExit("CURRENT_TREND_REPORT_NOT_FOUND")
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    validate(current, "CURRENT")
    current_date = data_date(current)
    if not current_date:
        raise SystemExit("CURRENT_DATA_DATE_UNAVAILABLE")
    HISTORY.mkdir(parents=True, exist_ok=True)

    current_snapshot = HISTORY / f"{current_date}.json"
    prior_files = sorted(p for p in HISTORY.glob("????????.json")
                         if re.fullmatch(r"\d{8}", p.stem) and p.stem < current_date)
    prior = None
    prior_date = None
    if prior_files:
        prior_path = prior_files[-1]
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        validate(prior, "PRIOR")
        prior_date = data_date(prior)
        if not prior_date or prior_date >= current_date:
            raise SystemExit("PRIOR_SNAPSHOT_DATE_ORDER_INVALID")

    if not current_snapshot.exists():
        shutil.copy2(CURRENT, current_snapshot)

    now = datetime.now(TEHRAN).isoformat()
    cur_rows = index_rows(current)
    cur_ranks = rank_map(current)
    result_rows = []
    if prior is not None:
        old_rows = index_rows(prior)
        old_ranks = rank_map(prior)
        all_symbols = sorted(set(cur_rows) | set(old_rows))
        for symbol in all_symbols:
            old = old_rows.get(symbol)
            new = cur_rows.get(symbol)
            if old is None:
                result_rows.append({
                    "symbol": symbol, "status": "NEW_ENTRY",
                    "previous_rank": None, "current_rank": cur_ranks.get(symbol),
                    "rank_change": None, "previous_score": None,
                    "current_score": new.get("final_score"),
                    "score_change": None, "deltas": {},
                    "observations": ["نماد در گزارش تاریخ قبل وجود نداشت؛ علت ورود مستقل از داده قابل اثبات نیست"],
                })
                continue
            if new is None:
                result_rows.append({
                    "symbol": symbol, "status": "MISSING_FROM_CURRENT",
                    "previous_rank": old_ranks.get(symbol), "current_rank": None,
                    "rank_change": None, "previous_score": old.get("final_score"),
                    "current_score": None, "score_change": None, "deltas": {},
                    "observations": ["نماد در گزارش فعلی وجود ندارد؛ وضعیت داده/واجدشرایط‌بودن بررسی شود"],
                })
                continue
            deltas = {}
            for field in NUMERIC_FIELDS:
                a, b = numeric(old.get(field)), numeric(new.get(field))
                deltas[field] = round(b - a, 6) if a is not None and b is not None else None
            old_rank, new_rank = old_ranks[symbol], cur_ranks[symbol]
            result_rows.append({
                "symbol": symbol, "status": "CONTINUED",
                "previous_rank": old_rank, "current_rank": new_rank,
                "rank_change": old_rank - new_rank,
                "previous_score": old.get("final_score"),
                "current_score": new.get("final_score"),
                "score_change": deltas["final_score"],
                "deltas": deltas,
                "observations": classify_changes(old, new, deltas),
                "previous_warnings": old.get("warnings") or [],
                "current_warnings": new.get("warnings") or [],
            })

    moved = [r for r in result_rows if r["status"] == "CONTINUED" and r.get("rank_change") not in (None, 0)]
    improved = sorted((r for r in moved if r["rank_change"] > 0),
                      key=lambda r: (-r["rank_change"], -(r.get("score_change") or 0), r["symbol"]))
    declined = sorted((r for r in moved if r["rank_change"] < 0),
                      key=lambda r: (r["rank_change"], (r.get("score_change") or 0), r["symbol"]))
    if prior is None:
        status = "BASELINE_CREATED_NO_PRIOR_DATE"
    elif current_date == prior_date:
        status = "NO_NEW_HISTORY_DATE"
    else:
        status = "DAILY_COMPARISON_COMPLETE"

    payload = {
        "report_version": "BASE_SHARE_DAILY_RANK_CHANGE-1.0",
        "generated_at": now,
        "source_of_truth": "TSETMC",
        "current_data_date": current_date,
        "previous_data_date": prior_date,
        "current_report_sha256": current.get("report_sha256"),
        "previous_report_sha256": prior.get("report_sha256") if prior else None,
        "current_symbol_count": len(cur_rows),
        "previous_symbol_count": len(prior.get("rows", [])) if prior else 0,
        "status": status,
        "buy_sell_signal": "NOT_GENERATED",
        "score_weights_changed": False,
        "causality_policy": "OBSERVED_FEATURE_DELTAS_ONLY_NO_UNSUPPORTED_CAUSAL_CLAIMS",
        "missing_data_policy": "NO_IMPUTATION; DELTA_NULL_WHEN_EITHER_SIDE_MISSING",
        "rows": result_rows,
        "rank_improvements": improved[:30],
        "rank_declines": declined[:30],
        "limitations": [
            "Changes are comparisons of TSETMC-derived report fields; correlation is not proof of cause.",
            "Board/BestLimits, news, and fundamental evidence are not included unless present in source rows.",
            "Weights are not modified by this report; any change requires a separate validated backtest.",
            "A same-date rerun does not replace an existing archived snapshot."
        ],
    }
    payload["report_sha256"] = canonical_sha256(payload)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    lines = [
        "گزارش روزانه تغییر رتبه سهام — TSETMC",
        "=" * 88,
        f"وضعیت: {status}",
        f"تاریخ داده فعلی: {current_date}",
        f"تاریخ داده قبلی: {prior_date or 'اطلاعات موجود نیست'}",
        f"تعداد نماد فعلی: {len(cur_rows)} | تعداد نماد قبلی: {len(prior.get('rows', [])) if prior else 0}",
        "تغییر وزن مدل: خیر | سیگنال خرید/فروش: تولید نشده",
        "توضیح: شاخص‌ها و تغییرات قابل مشاهده گزارش می‌شوند؛ رابطه علّی بدون شواهد مستقل ادعا نمی‌شود.",
        "-" * 88,
    ]
    if prior is None:
        lines.append("این اجرا فقط خط مبنا را ذخیره کرد؛ پس از ورود تاریخ داده جدید، مقایسه روزانه تولید می‌شود.")
    else:
        lines.extend([
            f"نمادهای دارای بهبود رتبه: {len(improved)}",
            f"نمادهای دارای افت رتبه: {len(declined)}",
            "",
            "بیشترین بهبود رتبه:",
        ])
        for row in improved[:30]:
            lines.append(f"{row['symbol']} | رتبه {row['previous_rank']}→{row['current_rank']} "
                         f"| تغییر امتیاز {row['score_change']} | " + "؛ ".join(row["observations"]))
        lines.extend(["", "بیشترین افت رتبه:"])
        for row in declined[:30]:
            lines.append(f"{row['symbol']} | رتبه {row['previous_rank']}→{row['current_rank']} "
                         f"| تغییر امتیاز {row['score_change']} | " + "؛ ".join(row["observations"]))
        lines.extend(["", "جزئیات همه نمادها در فایل JSON موجود است."])
    lines.extend([
        "-" * 88,
        f"Snapshot: {current_snapshot}",
        f"JSON: {REPORT_JSON}",
        f"TXT: {REPORT_TXT}",
        f"SHA256: {payload['report_sha256']}",
    ])
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("STATUS =", status)
    print("CURRENT_DATA_DATE =", current_date)
    print("PREVIOUS_DATA_DATE =", prior_date or "UNAVAILABLE")
    print("CURRENT_SYMBOL_COUNT =", len(cur_rows))
    print("PREVIOUS_SYMBOL_COUNT =", len(prior.get("rows", [])) if prior else 0)
    print("RANK_IMPROVEMENTS =", len(improved))
    print("RANK_DECLINES =", len(declined))
    print("JSON_REPORT =", REPORT_JSON)
    print("TEXT_REPORT =", REPORT_TXT)
    print("SNAPSHOT =", current_snapshot)
    print("BUY_SELL_SIGNAL = OFF")
    print("SCORE_WEIGHTS_CHANGED = NO")


if __name__ == "__main__":
    main()
