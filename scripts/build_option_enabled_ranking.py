import json
from pathlib import Path
from collections import defaultdict

base_path = Path("output/base_share/latest_plain_symbol_trend_report.json")
snap_path = Path("output/tsetmc_first/latest_universe_snapshot.json")
out_dir = Path("output/base_share")

base = json.loads(base_path.read_text(encoding="utf-8"))
snap = json.loads(snap_path.read_text(encoding="utf-8"))
ranked = base.get("rows", [])
options = snap.get("rows", [])

if not ranked or not options:
    raise SystemExit("ERROR: base ranking or option snapshot is empty")

by_symbol = {
    str(row.get("symbol", "")).strip(): (rank, row)
    for rank, row in enumerate(ranked, 1)
    if str(row.get("symbol", "")).strip()
}
grouped = defaultdict(list)
for row in options:
    identity = row.get("identity") or {}
    symbol = str(identity.get("underlying_symbol", "")).strip()
    if symbol:
        grouped[symbol].append(row)

matched, unmatched = [], []
for symbol, contracts in grouped.items():
    item = {
        "underlying_symbol": symbol,
        "option_contract_count": len(contracts),
        "option_symbols": sorted({
            str((r.get("canonical") or {}).get("نماد")
                or (r.get("raw_market_watch") or {}).get("symbol") or "")
            for r in contracts
        }),
        "contracts": [
            {
                "symbol": (r.get("canonical") or {}).get("نماد")
                          or (r.get("raw_market_watch") or {}).get("symbol"),
                "type": (r.get("identity") or {}).get("contract_type"),
                "strike": (r.get("canonical") or {}).get("قیمت اعمال"),
                "expiry": (r.get("identity") or {}).get("end_date"),
                "last_price": (r.get("canonical") or {}).get("آخرین قیمت"),
                "close_price": (r.get("canonical") or {}).get("قیمت پایانی"),
                "volume": (r.get("canonical") or {}).get("حجم معاملات"),
                "open_interest": (r.get("canonical") or {}).get("موقعیت های باز"),
            }
            for r in contracts
        ],
    }
    if symbol in by_symbol:
        rank, row = by_symbol[symbol]
        item.update({
            "base_rank": rank,
            "base_score": row.get("final_score"),
            "base_classification": row.get("classification"),
        })
        matched.append(item)
    else:
        item["status"] = "NOT_IN_BASE_SHARE_RANKING"
        unmatched.append(item)

matched.sort(key=lambda x: x["base_rank"])
unmatched.sort(key=lambda x: x["underlying_symbol"])

report = {
    "status": "BUILT_FROM_AVAILABLE_SNAPSHOT",
    "ranking_basis": "EXISTING_BASE_SHARE_RANKING",
    "base_ranking_date": base.get("latest_history_date"),
    "base_ranking_count": len(ranked),
    "option_snapshot_mode": snap.get("data_mode"),
    "option_snapshot_generated_at": snap.get("generated_at"),
    "option_snapshot_rows": len(options),
    "distinct_option_underlyings": len(grouped),
    "matched_ranked_underlyings": len(matched),
    "unmatched_underlyings": len(unmatched),
    "weights_changed": False,
    "buy_sell_signal": "OFF",
    "matched": matched,
    "unmatched": unmatched,
}

json_path = out_dir / "latest_option_enabled_base_share_ranking.json"
txt_path = out_dir / "latest_option_enabled_base_share_ranking.txt"
json_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)

lines = [
    "OPTION-ENABLED BASE SHARE RANKING",
    "Ranking basis: existing base-share rank; no rescoring",
    f"Base ranking date: {report['base_ranking_date']}",
    f"Snapshot mode: {report['option_snapshot_mode']}",
    f"Snapshot generated at: {report['option_snapshot_generated_at']}",
    f"Base ranking rows: {len(ranked)}",
    f"Option records: {len(options)}",
    f"Matched ranked underlyings: {len(matched)}",
    f"Unmatched underlyings: {len(unmatched)}",
    "",
    "RANK | SYMBOL | SCORE | CONTRACTS | OPTION SYMBOLS",
]
for x in matched:
    lines.append(
        f"{x['base_rank']} | {x['underlying_symbol']} | "
        f"{x['base_score']} | {x['option_contract_count']} | "
        f"{', '.join(x['option_symbols'])}"
    )
lines.extend(["", "NOT IN BASE SHARE RANKING:"])
for x in unmatched:
    lines.append(
        f"{x['underlying_symbol']} | {x['option_contract_count']} contracts | "
        f"{', '.join(x['option_symbols'])}"
    )

txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("STATUS:", report["status"])
print("BASE_ROWS:", len(ranked))
print("OPTION_ROWS:", len(options))
print("DISTINCT_UNDERLYINGS:", len(grouped))
print("MATCHED:", len(matched))
print("UNMATCHED:", len(unmatched))
print("TEXT_REPORT:", txt_path)
print("JSON_REPORT:", json_path)
print()
print("\n".join(lines))
