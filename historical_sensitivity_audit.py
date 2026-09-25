#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only sensitivity/ablation audit for the active TSETMC V4.1 scorer.

This module never calls the legacy scoring_engine.py and never changes the
production report path. It consumes real saved TSETMC snapshots and reuses the
active tsetmc_scoring_engine with explicit audit-only ablations.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from tsetmc_scoring_engine import BLOCK_WEIGHTS, FACTOR_WEIGHTS, build_evidence_ranking

ENGINE_VERSION = "G7-2-TSETMC-SENSITIVITY-1.0"


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _id(row: dict[str, Any]) -> str | None:
    value = (row.get("identity") or {}).get("instrument_id")
    return str(value) if value not in (None, "") else None


def _symbol(row: dict[str, Any]) -> str:
    return str((row.get("canonical") or {}).get("نماد") or "داده موجود نیست")


def _rank_map(ranking: dict[str, Any]) -> dict[str, int]:
    return {
        str(x["instrument_id"]): int(x["rank"])
        for x in ranking.get("ranking_rows", [])
        if x.get("instrument_id") not in (None, "") and x.get("rank") is not None
    }


def _top_ids(ranking: dict[str, Any], top_n: int) -> list[str]:
    return [
        str(x["instrument_id"])
        for x in ranking.get("ranking_rows", [])[:top_n]
        if x.get("instrument_id") not in (None, "")
    ]


def _spearman(base: dict[str, int], variant: dict[str, int]) -> float | None:
    common = sorted(set(base) & set(variant))
    if len(common) < 2:
        return None
    n = len(common)
    d2 = sum((base[k] - variant[k]) ** 2 for k in common)
    return round(1.0 - (6.0 * d2) / (n * (n * n - 1)), 8)


def _comparison(base: dict[str, Any], variant: dict[str, Any], top_n: int) -> dict[str, Any]:
    base_ids = _top_ids(base, top_n)
    variant_ids = _top_ids(variant, top_n)
    base_rank = _rank_map(base)
    variant_rank = _rank_map(variant)
    common = set(base_rank) & set(variant_rank)
    return {
        "top_n": top_n,
        "base_top_n": base_ids,
        "variant_top_n": variant_ids,
        "top_n_overlap_count": len(set(base_ids) & set(variant_ids)),
        "top_n_overlap_pct": round(
            len(set(base_ids) & set(variant_ids)) / max(1, min(top_n, len(base_ids))) * 100.0, 4
        ),
        "common_ranked_count": len(common),
        "rank_changes_common": sum(base_rank[k] != variant_rank[k] for k in common),
        "spearman_rank_correlation": _spearman(base_rank, variant_rank),
    }


def _candidate_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    if snapshot.get("source_of_truth") != "TSETMC":
        raise ValueError("SOURCE_OF_TRUTH_MUST_BE_TSETMC")
    if not snapshot.get("snapshot_sha256"):
        raise ValueError("SNAPSHOT_SHA256_REQUIRED")
    rows = snapshot.get("rows")
    if not isinstance(rows, list):
        rows = snapshot.get("records")
    if not isinstance(rows, list):
        raise ValueError("TSETMC_ROWS_REQUIRED")
    eligibility = snapshot.get("eligibility") or {}
    ids = {str(x) for x in (eligibility.get("candidate_instrument_ids") or [])}
    if not ids:
        raise ValueError("OPPORTUNITY_CANDIDATE_IDS_REQUIRED")
    selected = [r for r in rows if _id(r) in ids]
    if not selected:
        raise ValueError("NO_OPPORTUNITY_CANDIDATE_ROWS")
    return selected


def _audit_one(rows: list[dict[str, Any]], top_n: int) -> dict[str, Any]:
    baseline = build_evidence_ranking(rows)
    blocks = []
    for block in BLOCK_WEIGHTS:
        variant = build_evidence_ranking(rows, disabled_blocks={block})
        blocks.append({
            "type": "BLOCK_ABLATION",
            "name": block,
            "weight": BLOCK_WEIGHTS[block],
            "comparison": _comparison(baseline, variant, top_n),
        })

    factors = []
    for block, factor_map in FACTOR_WEIGHTS.items():
        for factor in factor_map:
            variant = build_evidence_ranking(rows, disabled_factors={factor})
            factors.append({
                "type": "FACTOR_ABLATION",
                "block": block,
                "name": factor,
                "weight": factor_map[factor],
                "comparison": _comparison(baseline, variant, top_n),
            })

    by_type = {}
    for contract_type in ("CALL", "PUT"):
        subset = [
            r for r in rows
            if str((r.get("identity") or {}).get("contract_type") or "").upper() == contract_type
        ]
        if subset:
            by_type[contract_type] = _audit_one_without_split(subset, top_n)

    return {
        "baseline": {
            "status": baseline.get("status"),
            "ranking_scope": baseline.get("ranking_scope"),
            "ranking_scope_row_count": baseline.get("ranking_scope_row_count"),
            "top_n": _top_ids(baseline, top_n),
        },
        "block_ablations": blocks,
        "factor_ablations": factors,
        "by_contract_type": by_type,
    }


def _audit_one_without_split(rows: list[dict[str, Any]], top_n: int) -> dict[str, Any]:
    baseline = build_evidence_ranking(rows)
    block_results = []
    for block in BLOCK_WEIGHTS:
        variant = build_evidence_ranking(rows, disabled_blocks={block})
        block_results.append({
            "name": block,
            "comparison": _comparison(baseline, variant, top_n),
        })
    return {
        "row_count": len(rows),
        "baseline_top_n": _top_ids(baseline, top_n),
        "block_ablations": block_results,
    }


def run_snapshot(snapshot: dict[str, Any], top_n: int = 15) -> dict[str, Any]:
    if top_n < 1:
        raise ValueError("TOP_N_MUST_BE_POSITIVE")
    rows = _candidate_rows(snapshot)
    result = {
        "engine_version": ENGINE_VERSION,
        "audit": "G7-2_HISTORICAL_SENSITIVITY_ABLATION",
        "status": "EVIDENCE_ONLY",
        "production_mutation": False,
        "source_of_truth": "TSETMC",
        "snapshot_id": snapshot.get("snapshot_sha256"),
        "retrieved_at": snapshot.get("generated_at") or snapshot.get("retrieved_at"),
        "row_count": len(rows),
        "top_n": top_n,
        "analysis": _audit_one(rows, top_n),
    }
    result["evidence_hash"] = _sha(result)
    return result


def _observation_identity(item: dict[str, Any]) -> tuple[str | None, str | None]:
    return (
        str(item.get("snapshot_id")) if item.get("snapshot_id") not in (None, "") else None,
        str(item.get("retrieved_at")) if item.get("retrieved_at") not in (None, "") else None,
    )


def pair_stability(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = list(results)
    pairs = []
    rejected = []
    for previous, current in zip(items, items[1:]):
        previous_id, previous_time = _observation_identity(previous)
        current_id, current_time = _observation_identity(current)

        if not previous_id or not current_id:
            rejected.append({
                "previous_snapshot": previous_id,
                "current_snapshot": current_id,
                "status": "REJECTED_MISSING_SNAPSHOT_ID",
            })
            continue

        if previous_id == current_id:
            rejected.append({
                "previous_snapshot": previous_id,
                "current_snapshot": current_id,
                "status": "REJECTED_DUPLICATE_SNAPSHOT",
            })
            continue

        if not previous_time or not current_time:
            rejected.append({
                "previous_snapshot": previous_id,
                "current_snapshot": current_id,
                "status": "REJECTED_MISSING_RETRIEVAL_TIME",
            })
            continue

        if previous_time == current_time:
            rejected.append({
                "previous_snapshot": previous_id,
                "current_snapshot": current_id,
                "status": "REJECTED_DUPLICATE_RETRIEVAL_TIME",
            })
            continue

        a = previous.get("analysis", {}).get("baseline", {}).get("top_n", [])
        b = current.get("analysis", {}).get("baseline", {}).get("top_n", [])
        overlap = len(set(a) & set(b))
        pairs.append({
            "previous_snapshot": previous_id,
            "current_snapshot": current_id,
            "previous_retrieved_at": previous_time,
            "current_retrieved_at": current_time,
            "status": "INDEPENDENT_OBSERVATIONS",
            "top_n": previous.get("top_n"),
            "top_n_overlap_count": overlap,
            "top_n_overlap_pct": round(overlap / max(1, min(len(a), len(b))) * 100.0, 4),
        })
    return {
        "pair_count": len(pairs),
        "rejected_pair_count": len(rejected),
        "pairs": pairs,
        "rejected_pairs": rejected,
        "historical_closure_eligible": bool(pairs),
    }


if __name__ == "__main__":
    raise SystemExit("Use historical_dataset_runner.py with real saved TSETMC snapshots.")
