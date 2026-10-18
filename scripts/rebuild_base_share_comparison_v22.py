#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import re
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from base_share_opportunity_engine_v2 import (
    score_opportunity,
    ENGINE_VERSION,
)

ARCHIVE_15 = ROOT / "output/base_share/daily_history/20261007.json"
SOURCE_18 = ROOT / "output/base_share/latest_whole_market_opportunity_report.json"
OUT = ROOT / "output/base_share/comparison_v22"
DIGIT_AT_END = re.compile(r"[0-9\u0660-\u0669\u06F0-\u06F9]$")


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(obj):
    raw = json.dumps(
        obj, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), default=str
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_report(path, expected_date):
    if not path.exists():
        raise SystemExit(f"SOURCE_MISSING: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("source_of_truth") != "TSETMC":
        raise SystemExit(f"NON_TSETMC_SOURCE: {path}")

    actual_date = str(data.get("latest_history_date") or "")
    if actual_date != expected_date:
        raise SystemExit(
            f"DATE_MISMATCH: {path}; expected={expected_date}; actual={actual_date}"
        )

    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"INVALID_OR_EMPTY_ROWS: {path}")

    return data, rows


def prepare_rows(rows, label):
    result = {}
    excluded_suffix = 0
    missing_id = 0
    duplicate_ids = []

    for original in rows:
        symbol = str(original.get("symbol") or "").strip()
        iid = str(original.get("instrument_id") or "").strip()

        if not symbol or not iid:
            missing_id += 1
            continue

        # Same preliminary filter used by the existing plain-symbol report.
        # This is not verified instrument-master classification.
        if DIGIT_AT_END.search(symbol):
            excluded_suffix += 1
            continue

        if iid in result:
            duplicate_ids.append(iid)
            continue

        # Re-run the actual V2.2 scoring function on archived feature fields.
        scored = score_opportunity(original)
        row = dict(original)
        row.update(scored)
        row["instrument_classification"] = (
            "COMMON_SHARE_CANDIDATE_HEURISTIC_NOT_VERIFIED"
        )
        row["historical_feature_recalculation"] = (
            "NOT_PERFORMED; SCORED_FROM_ARCHIVED_FEATURES"
        )
        row["source_period_label"] = label
        result[iid] = row

    if duplicate_ids:
        raise SystemExit(
            f"DUPLICATE_INSTRUMENT_IDS_{label}: "
            + ",".join(duplicate_ids[:10])
        )

    print(
        f"FILTER_{label}: rows={len(rows)}; retained={len(result)}; "
        f"excluded_digit_suffix={excluded_suffix}; missing_identity={missing_id}"
    )
    return result


def rank_rows_by_score(rows):
    return sorted(
        rows,
        key=lambda r: (
            r.get("final_score") is None,
            -(float(r["final_score"]) if r.get("final_score") is not None else 0.0),
            str(r.get("symbol") or ""),
            str(r.get("instrument_id") or ""),
        ),
    )


def make_payload(label, date, source_path, source_data, source_rows, scored_map):
    ranked = rank_rows_by_score(list(scored_map.values()))
    payload = {
        "report_version": "BASE_SHARE_HISTORICAL_RESCORE_V2.2",
        "period_label": label,
        "market_date": date,
        "generated_at": datetime.now(ZoneInfo("Asia/Tehran")).isoformat(),
        "source_of_truth": "TSETMC",
        "score_engine": ENGINE_VERSION,
        "source_file": str(source_path.relative_to(ROOT)),
        "source_file_sha256": sha256_file(source_path),
        "source_report_sha256": source_data.get("report_sha256"),
        "source_row_count": len(source_rows),
        "retained_plain_symbol_count": len(ranked),
        "classification_policy": (
            "SYMBOL_SUFFIX_HEURISTIC_ONLY; "
            "COMMON_SHARE_CANDIDATE_HEURISTIC_NOT_VERIFIED"
        ),
        "scoring_method": (
            "V2.2 SCORE FUNCTION RE-RUN ON ARCHIVED FEATURE FIELDS; "
            "RAW HISTORICAL INDICATORS NOT RECOMPUTED"
        ),
        "missing_data_policy": "NO_IMPUTATION",
        "buy_sell_signal": "NOT_GENERATED",
        "rows": ranked,
    }
    payload["report_sha256"] = canonical_hash(payload)
    return payload


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def score_sort_key(item):
    score = item.get("final_score")
    return (score is None, -(float(score) if score is not None else 0.0),
            str(item.get("symbol") or ""))


def main():
    # Validate source dates before creating any output.
    report15, rows15 = load_report(ARCHIVE_15, "20261007")
    report18, rows18 = load_report(SOURCE_18, "20261010")

    print("ENGINE:", ENGINE_VERSION)
    print("SOURCE_15_SHA256:", sha256_file(ARCHIVE_15))
    print("SOURCE_18_SHA256:", sha256_file(SOURCE_18))
    print("SOURCE_15_ENGINE_VERSIONS:",
          dict(Counter(str(r.get("engine_version")) for r in rows15)))
    print("SOURCE_18_ENGINE_VERSIONS:",
          dict(Counter(str(r.get("engine_version")) for r in rows18)))

    # Refuse unexpected source engines rather than silently accepting a changed
    # or mixed source file.
    if not all(str(r.get("engine_version", "")).endswith("V2.1") for r in rows15):
        raise SystemExit("SOURCE_15_ENGINE_NOT_EXPECTED_V2.1")
    if not all(str(r.get("engine_version", "")).endswith("V2.2") for r in rows18):
        raise SystemExit("SOURCE_18_ENGINE_NOT_EXPECTED_V2.2")

    scored15 = prepare_rows(rows15, "1405/07/15")
    scored18 = prepare_rows(rows18, "1405/07/18")

    # Only identical instrument IDs present in both periods are used for the
    # rank-change comparison.
    common_ids = sorted(set(scored15) & set(scored18))
    if not common_ids:
        raise SystemExit("NO_COMMON_INSTRUMENTS; COMPARISON_NOT_CREATED")

    prev_order = sorted(
        common_ids,
        key=lambda iid: score_sort_key(scored15[iid])
    )
    curr_order = sorted(
        common_ids,
        key=lambda iid: score_sort_key(scored18[iid])
    )
    rank15 = {iid: i for i, iid in enumerate(prev_order, 1)}
    rank18 = {iid: i for i, iid in enumerate(curr_order, 1)}

    changes = []
    for iid in common_ids:
        a, b = scored15[iid], scored18[iid]
        sa, sb = a.get("final_score"), b.get("final_score")
        changes.append({
            "instrument_id": iid,
            "symbol_15": a.get("symbol"),
            "symbol_18": b.get("symbol"),
            "score_15_v22": sa,
            "score_18_v22": sb,
            "score_delta": round(float(sb) - float(sa), 2)
                if sa is not None and sb is not None else None,
            "rank_15_common_universe": rank15[iid],
            "rank_18_common_universe": rank18[iid],
            "rank_change": rank15[iid] - rank18[iid],
            "engine_15": a.get("engine_version"),
            "engine_18": b.get("engine_version"),
            "score_comparable": (
                sa is not None and sb is not None
                and a.get("engine_version") == ENGINE_VERSION
                and b.get("engine_version") == ENGINE_VERSION
            ),
        })

    # Rank delta convention: positive means the instrument improved its rank.
    changes.sort(
        key=lambda x: (
            x["score_delta"] is None,
            -(x["score_delta"] if x["score_delta"] is not None else 0.0),
            x["symbol_18"] or "",
        )
    )

    payload15 = make_payload(
        "1405/07/15", "20261007", ARCHIVE_15, report15, rows15, scored15
    )
    payload18 = make_payload(
        "1405/07/18", "20261010", SOURCE_18, report18, rows18, scored18
    )

    # Comparison-only ranks are recalculated over the same common universe.
    comparison = {
        "report_version": "BASE_SHARE_DAILY_COMPARISON_V2.2",
        "previous_market_date": "1405/07/15",
        "current_market_date": "1405/07/18",
        "previous_market_date_gregorian": "20261007",
        "current_market_date_gregorian": "20261010",
        "score_engine": ENGINE_VERSION,
        "source_15_report_sha256": payload15["report_sha256"],
        "source_18_report_sha256": payload18["report_sha256"],
        "common_instrument_count": len(common_ids),
        "only_previous_count": len(set(scored15) - set(scored18)),
        "only_current_count": len(set(scored18) - set(scored15)),
        "rank_method": "RANKS_COMPUTED_WITHIN_IDENTICAL_COMMON_INSTRUMENT_UNIVERSE",
        "score_delta_convention": "CURRENT_MINUS_PREVIOUS",
        "rank_change_convention": "POSITIVE_MEANS_RANK_IMPROVED",
        "limitations": [
            "Historical feature indicators are reused from archived report rows; they were not recalculated from raw daily prices.",
            "Missing historical feature fields remain missing; no imputation is performed.",
            "Ordinary-share classification remains a symbol-suffix heuristic and is not verified against an instrument master.",
            "This comparison is descriptive and is not a buy/sell signal.",
        ],
        "largest_score_increases": [
            x for x in sorted(
                changes,
                key=lambda x: (
                    x["score_delta"] is None,
                    -(x["score_delta"] if x["score_delta"] is not None else 0.0),
                ),
            ) if x["score_delta"] is not None
        ][:20],
        "largest_score_decreases": [
            x for x in sorted(
                changes,
                key=lambda x: (
                    x["score_delta"] is None,
                    x["score_delta"] if x["score_delta"] is not None else 0.0,
                ),
            ) if x["score_delta"] is not None
        ][:20],
        "all_common_instruments": changes,
    }
    comparison["report_sha256"] = canonical_hash(comparison)

    path15 = OUT / "base_share_14050715_v22.json"
    path18 = OUT / "base_share_14050718_v22.json"
    pathc = OUT / "comparison_14050715_vs_14050718_v22.json"

    save_json(path15, payload15)
    save_json(path18, payload18)
    save_json(pathc, comparison)

    print("\nREBUILD_STATUS: COMPLETE")
    print("ENGINE:", ENGINE_VERSION)
    print("15_MEHR_RESCORING_ROWS:", len(scored15))
    print("18_MEHR_RESCORING_ROWS:", len(scored18))
    print("COMMON_INSTRUMENTS:", len(common_ids))
    print("ONLY_15_MEHR:", comparison["only_previous_count"])
    print("ONLY_18_MEHR:", comparison["only_current_count"])
    print("OUTPUT_15:", path15.relative_to(ROOT))
    print("OUTPUT_18:", path18.relative_to(ROOT))
    print("COMPARISON:", pathc.relative_to(ROOT))
    print("SHA256_15:", payload15["report_sha256"])
    print("SHA256_18:", payload18["report_sha256"])
    print("SHA256_COMPARISON:", comparison["report_sha256"])

    print("\nTOP_SCORE_INCREASES:")
    for x in comparison["largest_score_increases"][:10]:
        print(
            f"{x['symbol_18']} | {x['score_15_v22']} -> {x['score_18_v22']} "
            f"| delta={x['score_delta']:+.2f} "
            f"| rank={x['rank_15_common_universe']}->{x['rank_18_common_universe']}"
        )

    print("\nTOP_SCORE_DECREASES:")
    for x in comparison["largest_score_decreases"][:10]:
        print(
            f"{x['symbol_18']} | {x['score_15_v22']} -> {x['score_18_v22']} "
            f"| delta={x['score_delta']:+.2f} "
            f"| rank={x['rank_15_common_universe']}->{x['rank_18_common_universe']}"
        )


if __name__ == "__main__":
    main()
