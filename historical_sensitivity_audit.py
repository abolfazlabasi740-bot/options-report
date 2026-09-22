#!/usr/bin/env python3
from __future__ import annotations
from typing import Any
import hashlib, json
import pandas as pd
from scoring_engine import shadow_score_dataframe

BLOCKS = {
    "Liquidity": ("BlockScore_Liquidity", 20.0),
    "Valuation": ("BlockScore_Valuation", 25.0),
    "Payoff": ("BlockScore_Payoff", 18.0),
    "Time": ("BlockScore_Time", 15.0),
    "Greeks": ("BlockScore_Greeks", 12.0),
    "Market": ("BlockScore_Market", 10.0),
}

def _ranked(df: pd.DataFrame, score_col: str) -> pd.DataFrame:
    out = df.copy()
    out["_score"] = pd.to_numeric(out[score_col], errors="coerce")
    out = out[out["_score"].notna()].copy()
    out = out.sort_values(["_score", "ارزش معاملات", "حجم معاملات", "نماد"],
                          ascending=[False, False, False, True], kind="mergesort")
    out["_rank"] = range(1, len(out) + 1)
    return out

def _sha(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def run_sensitivity(df: pd.DataFrame, top_n: int = 15) -> dict[str, Any]:
    if top_n < 1:
        raise ValueError("top_n must be positive")
    scored = shadow_score_dataframe(df)
    base = _ranked(scored, "FinalScore")
    if base.empty:
        raise ValueError("no valid shadow scores for sensitivity audit")
    base_top = base.head(top_n)
    base_symbols = list(base_top["نماد"].astype(str))
    rows = []
    for name, (column, weight) in BLOCKS.items():
        variant = scored.copy()
        remaining_weight = 100.0 - weight
        variant["_AblatedBase"] = (
            (pd.to_numeric(variant["BaseScore"], errors="coerce") -
             pd.to_numeric(variant[column], errors="coerce"))
            * 100.0 / remaining_weight
        )
        spread = pd.to_numeric(variant.get("Spread_Percentage"), errors="coerce")
        execution = ((spread - 12.0) / 28.0).clip(lower=0, upper=0.35).where(spread.notna(), 0.10).clip(0, 0.45)
        days = pd.to_numeric(variant.get("RemainingDays"), errors="coerce")
        decay = pd.Series(0.0, index=variant.index)
        decay.loc[days <= 2] = 0.30
        decay.loc[(days > 2) & (days <= 5)] = 0.18
        decay.loc[(days > 5) & (days <= 10)] = 0.08
        confidence = (pd.to_numeric(variant["DataConfidence"], errors="coerce").fillna(0) / 100.0).clip(0.55, 1.0)
        variant["_AblatedFinal"] = (variant["_AblatedBase"] * (1.0-execution) * (1.0-decay) * confidence).round(2)
        ranked = _ranked(variant.rename(columns={"_AblatedFinal":"AuditScore"}), "AuditScore")
        top = ranked.head(top_n)
        symbols = list(top["نماد"].astype(str))
        base_rank = base.set_index("نماد")["_rank"].to_dict()
        new_rank = ranked.set_index("نماد")["_rank"].to_dict()
        common = set(base_rank) & set(new_rank)
        deltas = [abs(float(base.loc[base["نماد"] == s, "_score"].iloc[0]) -
                      float(ranked.loc[ranked["نماد"] == s, "_score"].iloc[0])) for s in common]
        rows.append({
            "block": name, "block_weight": weight, "top_n": top_n,
            "top_n_overlap": len(set(base_symbols) & set(symbols)),
            "top_n_overlap_pct": round(len(set(base_symbols) & set(symbols)) / min(top_n, len(base_top)) * 100.0, 4),
            "rank_changes_common_universe": sum(base_rank[s] != new_rank[s] for s in common),
            "max_score_delta": round(max(deltas), 6) if deltas else 0.0,
            "mean_score_delta": round(sum(deltas)/len(deltas), 6) if deltas else 0.0,
            "ablated_top_symbols": symbols,
        })
    evidence = {
        "audit":"G7-2_HISTORICAL_SENSITIVITY_ABLATION", "status":"EVIDENCE_ONLY",
        "production_mutation":False, "engine":"V4.1.1",
        "input_row_count":int(len(df)), "scored_row_count":int(len(scored)),
        "top_n":top_n, "baseline_top_symbols":base_symbols, "blocks":rows,
    }
    evidence["evidence_hash"] = _sha(evidence)
    return evidence

if __name__ == "__main__":
    raise SystemExit("Import run_sensitivity() from an external historical dataset runner.")
