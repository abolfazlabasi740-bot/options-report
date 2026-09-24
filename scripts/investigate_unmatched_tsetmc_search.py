#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only investigation of unmatched OptionSchool symbols via TSETMC InstrumentSearch.

This script does not infer identity and does not modify production scoring/ranking.
For each unmatched symbol it queries the authoritative TSETMC InstrumentSearch
endpoint and retains only exact returned symbol matches as identity evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from tsetmc_adapter import TSETMCAdapter, TSETMCError


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_records(data):
    if isinstance(data, dict):
        for key in ("instrumentSearch", "data", "items", "results"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data if isinstance(data, list) else []


def exact_matches(symbol, records):
    out = []
    for item in records:
        if not isinstance(item, dict):
            continue
        returned_symbols = [
            item.get("lVal18AFC"),
            item.get("symbol"),
            item.get("lVal18"),
        ]
        if symbol in {str(v).strip() for v in returned_symbols if v not in (None, "")}:
            out.append(item)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unmatched", required=True,
                    help="Corrected unmatched_symbols_v3.json")
    ap.add_argument("--output", required=True)
    ap.add_argument("--delay-seconds", type=float, default=0.25)
    a = ap.parse_args()

    src = json.loads(Path(a.unmatched).read_text(encoding="utf-8"))
    symbols = [str(x["symbol"]).strip() for x in src.get("unmatched", [])]
    adapter = TSETMCAdapter()
    evidence = []

    for i, symbol in enumerate(symbols, start=1):
        item = {
            "symbol": symbol,
            "sequence": i,
            "status": "SEARCH_FAILED",
            "endpoint": None,
            "snapshot_sha256": None,
            "retrieved_at": None,
            "exact_match_count": 0,
            "exact_matches": [],
            "identity_inference": "DISABLED",
        }
        try:
            result = adapter.search_instrument(symbol)
            records = extract_records(result.get("data"))
            matches = exact_matches(symbol, records)
            item.update({
                "status": "EXACT_SYMBOL_MATCH" if len(matches) == 1 else (
                    "AMBIGUOUS_EXACT_SYMBOL_MATCH" if len(matches) > 1 else
                    "NO_EXACT_SYMBOL_MATCH"
                ),
                "endpoint": result.get("endpoint"),
                "snapshot_sha256": result.get("snapshot_sha256"),
                "retrieved_at": result.get("retrieved_at"),
                "exact_match_count": len(matches),
                "exact_matches": matches,
            })
        except (TSETMCError, Exception) as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        evidence.append(item)
        if i < len(symbols) and a.delay_seconds > 0:
            time.sleep(a.delay_seconds)

    counts = {}
    for x in evidence:
        counts[x["status"]] = counts.get(x["status"], 0) + 1

    out = {
        "status": "SUCCESS",
        "input_unmatched_file_sha256": sha256_file(a.unmatched),
        "symbol_count": len(symbols),
        "status_counts": counts,
        "evidence": evidence,
        "identity_inference": "DISABLED",
        "production_changed": False,
        "note": (
            "Exact symbol equality is the only identity rule. InstrumentSearch "
            "results are evidence only; no symbol prefix, strike, expiry, or "
            "other similarity is used to infer identity."
        ),
    }
    Path(a.output).write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "SUCCESS", "symbol_count": len(symbols),
                      "status_counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
