#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic validator for a selected-output Golden report baseline.

This tool is evidence-only. It never recalculates scores, changes ranking, or
participates in the production report path.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


_CARD_RE = re.compile(
    r"🔹\s+(?P<rank>\d+)\.\s+(?P<symbol>.+?)\n"
    r".*?🏆 امتیاز:\s+(?P<score>\d+(?:\.\d+)?)",
    re.DOTALL,
)


def load_golden(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    selected = data.get("selected")
    if not isinstance(selected, list) or not selected:
        raise ValueError("Golden fixture must contain a non-empty selected list")
    return data


def parse_report_cards(report_text: str) -> list[dict]:
    rows = []
    for match in _CARD_RE.finditer(report_text):
        rows.append(
            {
                "rank": int(match.group("rank")),
                "symbol": match.group("symbol").strip(),
                "final_score": float(match.group("score")),
            }
        )
    rows.sort(key=lambda x: x["rank"])
    return rows


def validate_report_against_golden(
    report_text: str,
    golden: dict,
    *,
    require_source_file: bool = True,
) -> dict:
    source_file = golden.get("source_file")
    if require_source_file and source_file:
        if f"📄 فایل: {source_file}" not in report_text:
            return {
                "status": "MISMATCH",
                "reason": "SOURCE_FILE_MISMATCH",
                "expected_source_file": source_file,
            }

    expected = golden["selected"]
    actual = parse_report_cards(report_text)

    if len(actual) != len(expected):
        return {
            "status": "MISMATCH",
            "reason": "SELECTED_COUNT_MISMATCH",
            "expected_count": len(expected),
            "actual_count": len(actual),
        }

    mismatches = []
    for exp, act in zip(expected, actual):
        if exp["rank"] != act["rank"] or exp["symbol"] != act["symbol"]:
            mismatches.append(
                {
                    "rank": exp["rank"],
                    "expected_symbol": exp["symbol"],
                    "actual_symbol": act["symbol"],
                    "expected_score": exp["final_score"],
                    "actual_score": act["final_score"],
                    "reason": "IDENTITY_OR_RANK_MISMATCH",
                }
            )
            continue

        if not math.isclose(
            float(exp["final_score"]),
            float(act["final_score"]),
            rel_tol=0.0,
            abs_tol=0.005,
        ):
            mismatches.append(
                {
                    "rank": exp["rank"],
                    "symbol": exp["symbol"],
                    "expected_score": exp["final_score"],
                    "actual_score": act["final_score"],
                    "reason": "SCORE_MISMATCH",
                }
            )

    return {
        "status": "MATCH" if not mismatches else "MISMATCH",
        "expected_count": len(expected),
        "actual_count": len(actual),
        "mismatches": mismatches,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("golden")
    args = parser.parse_args()

    report_text = Path(args.report).read_text(encoding="utf-8")
    result = validate_report_against_golden(
        report_text, load_golden(args.golden)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "MATCH" else 1)
