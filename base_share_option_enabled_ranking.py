#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
RANK_FILE = ROOT / "output/base_share/latest_plain_symbol_trend_report.json"
SNAPSHOT_FILE = ROOT / "output/tsetmc_first/latest_snapshot.json"
OUT = ROOT / "output/base_share"

def normalize(value):
    s = str(value or "").strip()
    return s.translate(str.maketrans({
        "ي": "ی", "ى": "ی", "ك": "ک",
        "‌": "", " ": "", "\u200c": ""
    }))

def sha256_json(value):
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), default=str
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def stop(message):
    raise SystemExit("STATUS = BLOCKED\nREASON = " + message)

if not RANK_FILE.is_file():
    stop("BASE_SHARE_RANKING_NOT_FOUND")
if not SNAPSHOT_FILE.is_file():
    stop("TSETMC_OPTION_SNAPSHOT_NOT_FOUND")

rank_report = json.loads(RANK_FILE.read_text(encoding="utf-8"))
snapshot = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))

if rank_report.get("source_of_truth") != "TSETMC":
    stop("RANKING_SOURCE_NOT_TSETMC")
if snapshot.get("source_of_truth") != "TSETMC":
    stop("OPTION_SNAPSHOT_SOURCE_NOT_TSETMC")
if not isinstance(rank_report.get("rows"), list):
    stop("RANKING_ROWS_INVALID")
if not isinstance(snapshot.get("rows"), list) or not snapshot["rows"]:
    stop("OPTION_SNAPSHOT_ROWS_INVALID")

rank_rows = rank_report["rows"]
snapshot_rows = snapshot["rows"]

rank_by_symbol = {}
for rank, row in enumerate(rank_rows, 1):
    symbol = normalize(row.get("symbol"))
    if not symbol:
        continue
    if symbol in rank_by_symbol:
        stop("DUPLICATE_BASE_SYMBOL_IN_RANKING:" + symbol)
    rank_by_symbol[symbol] = {
        "rank": rank,
        "row": row
    }

contracts_by_symbol = {}
contract_ids_by_symbol = {}

for row in snapshot_rows:
    ident = row.get("identity") or {}
    symbol = normalize(ident.get("underlying_symbol"))
    underlying_id = str(ident.get("underlying_id") or "").strip()
    option_id = str(ident.get("instrument_id") or "").strip()
    option_symbol = str(
        (row.get("canonical") or {}).get("نماد")
        or ident.get("option_symbol")
        or (row.get("raw_market_watch") or {}).get("symbol")
        or ""
    ).strip()

    if not symbol or not underlying_id or not option_id:
        continue

    if symbol not in contracts_by_symbol:
        contracts_by_symbol[symbol] = {
            "underlying_id": underlying_id,
            "contracts": []
        }

    if contracts_by_symbol[symbol]["underlying_id"] != underlying_id:
        stop("UNDERLYING_ID_CONFLICT:" + symbol)

    if option_id not in contract_ids_by_symbol.setdefault(symbol, set()):
        contracts_by_symbol[symbol]["contracts"].append({
            "option_symbol": option_symbol or "اطلاعات موجود نیست",
            "instrument_id": option_id,
            "contract_type": ident.get("contract_type"),
            "strike": (row.get("canonical") or {}).get("قیمت اعمال"),
            "expiry": ident.get("end_date")
                or (row.get("canonical") or {}).get("تاریخ سررسید")
        })
        contract_ids_by_symbol[symbol].add(option_id)

matched = []
unmatched = []

for symbol, data in contracts_by_symbol.items():
    ranked = rank_by_symbol.get(symbol)
    if ranked is None:
        unmatched.append({
            "symbol": symbol,
            "underlying_id": data["underlying_id"],
            "contract_count": len(data["contracts"]),
            "reason": "OPTION_UNDERLYING_NOT_FOUND_IN_BASE_RANKING"
        })
        continue

    base = ranked["row"]
    score = base.get("final_score")
    matched.append({
        "base_rank": ranked["rank"],
        "symbol": base.get("symbol"),
        "final_score": score,
        "classification": base.get("classification"),
        "evidence_coverage_pct": base.get("evidence_coverage_pct"),
        "latest_market_date": base.get("latest_market_date"),
        "underlying_id": data["underlying_id"],
        "contract_count": len(data["contracts"]),
        "contracts": sorted(
            data["contracts"],
            key=lambda c: (
                str(c.get("expiry") or ""),
                str(c.get("option_symbol") or "")
            )
        )
    })

matched.sort(key=lambda x: (
    x["final_score"] is None,
    -(float(x["final_score"]) if x["final_score"] is not None else 0),
    x["base_rank"]
))

for new_rank, row in enumerate(matched, 1):
    row["option_enabled_rank"] = new_rank

now = datetime.now(ZoneInfo("Asia/Tehran")).isoformat()
payload = {
    "report_version": "OPTION_ENABLED_BASE_SHARE_RANKING_V1",
    "generated_at": now,
    "source_of_truth": "TSETMC",
    "ranking_source_file": str(RANK_FILE),
    "option_snapshot_file": str(SNAPSHOT_FILE),
    "ranking_history_date": rank_report.get("latest_history_date"),
    "ranking_history_date_jalali": rank_report.get("latest_history_date_jalali"),
    "option_snapshot_generated_at": snapshot.get("generated_at"),
    "option_snapshot_hash": snapshot.get("snapshot_sha256"),
    "base_share_count_in_ranking": len(rank_rows),
    "option_snapshot_row_count": len(snapshot_rows),
    "matched_option_enabled_underlyings": len(matched),
    "unmatched_option_underlyings": unmatched,
    "rows": matched,
    "rules": {
        "sort": "EXISTING_BASE_SHARE_FINAL_SCORE_DESCENDING",
        "weights_changed": False,
        "missing_score_imputed": False,
        "buy_sell_signal": "NOT_GENERATED",
        "fresh_market_capture_performed": False
    }
}
payload["report_sha256"] = sha256_json(payload)

OUT.mkdir(parents=True, exist_ok=True)
json_path = OUT / "latest_option_enabled_base_share_ranking.json"
txt_path = OUT / "latest_option_enabled_base_share_ranking.txt"

json_path.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    encoding="utf-8"
)

lines = [
    "رتبه‌بندی سهام پایه دارای قرارداد اختیار معامله",
    "=" * 100,
    "منبع: TSETMC",
    f"تاریخ مبنای رتبه‌بندی: {rank_report.get('latest_history_date_jalali') or rank_report.get('latest_history_date') or 'اطلاعات موجود نیست'}",
    f"تعداد نمادهای رتبه‌بندی پایه: {len(rank_rows)}",
    f"تعداد سهم‌های پایه آپشن‌دار تطبیق‌یافته: {len(matched)}",
    f"تعداد نمادهای آپشن‌دار بدون تطبیق در رتبه‌بندی: {len(unmatched)}",
    "ترتیب بر اساس امتیاز نهایی موجود سهم پایه است؛ وزن‌ها تغییر نکرده‌اند.",
    "امتیاز مفقود جایگزین نشده و این گزارش سیگنال خریدوفروش نیست.",
    "-" * 100,
    "رتبه آپشن‌دار | رتبه کل | نماد پایه | امتیاز پایه | تعداد قرارداد | نمادهای قرارداد",
    "-" * 100
]

for row in matched:
    symbols = [
        c["option_symbol"] for c in row["contracts"]
        if c["option_symbol"] != "اطلاعات موجود نیست"
    ]
    lines.append(
        f'{row["option_enabled_rank"]} | {row["base_rank"]} | '
        f'{row["symbol"]} | '
        f'{row["final_score"] if row["final_score"] is not None else "اطلاعات موجود نیست"} | '
        f'{row["contract_count"]} | '
        f'{", ".join(symbols) if symbols else "اطلاعات موجود نیست"}'
    )

if unmatched:
    lines += ["", "نمادهای دارای قرارداد که در رتبه‌بندی پایه تطبیق نشدند:"]
    for row in unmatched:
        lines.append(
            f'{row["symbol"]} | قراردادها: {row["contract_count"]} | '
            f'{row["reason"]}'
        )

lines += [
    "",
    "گزارش کامل قراردادها و شناسه‌ها در فایل JSON ذخیره شده است.",
    "JSON: " + str(json_path),
    "TXT: " + str(txt_path),
    "BUY_SELL_SIGNAL = OFF"
]
txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("STATUS = OPTION_ENABLED_BASE_SHARE_RANKING_COMPLETE")
print("BASE_RANKING_ROWS =", len(rank_rows))
print("OPTION_SNAPSHOT_ROWS =", len(snapshot_rows))
print("MATCHED_OPTION_ENABLED_UNDERLYINGS =", len(matched))
print("UNMATCHED_OPTION_UNDERLYINGS =", len(unmatched))
print("TEXT_REPORT =", txt_path)
print("JSON_REPORT =", json_path)
print("RANKING_HISTORY_DATE =", rank_report.get("latest_history_date"))
print("OPTION_SNAPSHOT_MODE =", snapshot.get("data_mode") or "MODE_NOT_DECLARED")
print("WEIGHTS_CHANGED = NO")
print("BUY_SELL_SIGNAL = OFF")
print()
print("\n".join(lines[:10 + len(matched)]))
