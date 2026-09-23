#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

BLOCKS = ("Liquidity", "Valuation", "Payoff", "Time", "Greeks", "Market")
NUMERIC = ("top_n_overlap", "rank_changes_common_universe", "max_score_delta", "mean_score_delta")


def iter_evidence(node):
    if isinstance(node, dict):
        if node.get("block") in BLOCKS and any(k in node for k in NUMERIC):
            yield node
        for value in node.values():
            yield from iter_evidence(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_evidence(value)


def main():
    ap = argparse.ArgumentParser(description="Summarize G7-2 historical sensitivity evidence.")
    ap.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args()

    grouped = {b: [] for b in BLOCKS}
    total_files = 0
    total_sheets = 0
    ok_sheets = 0
    unresolved = 0

    for path in args.files:
        data = json.loads(path.read_text(encoding="utf-8"))
        total_files += len(data.get("files", []))
        for book in data.get("files", []):
            total_sheets += len(book.get("sheets", []))
            for sheet in book.get("sheets", []):
                if sheet.get("status") == "SENSITIVITY_OK":
                    ok_sheets += 1
                elif sheet.get("status") == "UNRESOLVED":
                    unresolved += 1
                for row in iter_evidence(sheet.get("evidence", {})):
                    grouped[row["block"]].append(row)

    print(f"FILES: {total_files}")
    print(f"SHEETS: {total_sheets}")
    print(f"SENSITIVITY_OK: {ok_sheets}")
    print(f"UNRESOLVED: {unresolved}")

    for block in BLOCKS:
        rows = grouped[block]
        print()
        print(f"BLOCK: {block}")
        print(f"records: {len(rows)}")
        for key in NUMERIC:
            vals = [float(r[key]) for r in rows if isinstance(r.get(key), (int, float))]
            label = "rank_changes" if key == "rank_changes_common_universe" else key
            if vals:
                print(f"{label}: min={min(vals):.6f} max={max(vals):.6f} mean={mean(vals):.6f}")
            else:
                print(f"{label}: NO_NUMERIC_DATA")


if __name__ == "__main__":
    main()
