#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Economic option scoring from canonical TSETMC evidence.

This engine is intentionally separate from the legacy scoring_engine.py and from
the evidence-ranking label. It scores economic efficiency, not expected return,
probability of profit, or a buy/sell decision.

Policy:
- TSETMC is the only source of truth.
- Missing inputs remain unavailable.
- No IV, Greeks, risk-free rate, or theoretical value is invented.
- The established V4.1 block weights are retained: 20/25/18/15/12/10.
- Economic value uses premium burden and break-even distance as its core
  valuation/payoff evidence.
- Liquidity and market stability are supporting execution evidence.
- Greeks remain unavailable and their weight is redistributed at block level.
- Calendar time is supporting evidence only; more remaining days is not treated
  as intrinsically profitable.
"""
from __future__ import annotations
import math
from typing import Any

BLOCK_WEIGHTS = {
    "LIQUIDITY": 20.0,
    "VALUATION": 25.0,
    "PAYOFF": 18.0,
    "TIME": 15.0,
    "GREEKS": 12.0,
    "MARKET": 10.0,
}

FACTOR_WEIGHTS = {
    "LIQUIDITY": {"trade_value": 7.0, "volume": 5.0},
    "VALUATION": {"premium_burden": 15.0, "intrinsic_coverage": 10.0},
    "PAYOFF": {"breakeven_distance": 13.0, "leverage_efficiency": 5.0},
    "TIME": {"calendar_days": 15.0},
    "GREEKS": {},
    "MARKET": {"last_vs_close": 4.0, "intraday_range": 3.0},
}


def _num(v: Any) -> float | None:
    try:
        if v in (None, ""):
            return None
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _rank(values: list[float | None], higher: bool) -> list[float | None]:
    valid = sorted(v for v in values if v is not None)
    if not valid:
        return [None] * len(values)
    n = len(valid)
    if n == 1:
        return [1.0 if v is not None else None for v in values]
    out=[]
    for v in values:
        if v is None:
            out.append(None)
            continue
        r=sum(1 for x in valid if x <= v)/n
        out.append(r if higher else 1.0-r+1.0/n)
    return [max(0.0,min(1.0,x)) if x is not None else None for x in out]


def _derived(row: dict[str, Any]) -> dict[str, Any]:
    c=row.get("canonical") or {}
    ident=row.get("identity") or {}
    typ=str(ident.get("contract_type") or "").upper()
    S=_num(c.get("قیمت سهم پایه")); K=_num(c.get("قیمت اعمال"))
    P=_num(c.get("آخرین قیمت")); close=_num(c.get("قیمت پایانی"))
    high=_num(c.get("بیشترین قیمت")); low=_num(c.get("کمترین قیمت"))
    days=_num(c.get("روزهای تقویمی"))
    if typ not in {"CALL","PUT"} or None in (S,K,P) or S <= 0 or K <= 0 or P <= 0:
        return {
            "contract_type": typ or None, "premium_burden": None,
            "intrinsic_coverage": None, "breakeven_distance": None,
            "leverage_efficiency": None, "calendar_days": days,
            "trade_value": _num(c.get("ارزش معاملات")),
            "volume": _num(c.get("حجم معاملات")),
            "last_vs_close": None if P is None or close in (None,0) else abs(P-close)/abs(close),
            "intraday_range": None if None in (high,low,P) or P == 0 else abs(high-low)/abs(P),
        }
    intrinsic=max(S-K,0.0) if typ=="CALL" else max(K-S,0.0)
    time_value=max(P-intrinsic,0.0)
    breakeven=K+P if typ=="CALL" else K-P
    premium_burden=time_value/S
    intrinsic_coverage=intrinsic/P
    breakeven_distance=abs(breakeven-S)/S
    raw_leverage=S/P
    # Efficiency rewards useful leverage but penalizes the extreme tail
    # deterministically; no market threshold is introduced.
    leverage_efficiency=math.log1p(raw_leverage)/(1.0+math.log1p(raw_leverage))
    return {
        "contract_type":typ, "premium_burden":premium_burden,
        "intrinsic_coverage":intrinsic_coverage,
        "breakeven_distance":breakeven_distance,
        "leverage_efficiency":leverage_efficiency,
        "calendar_days":days,
        "trade_value":_num(c.get("ارزش معاملات")),
        "volume":_num(c.get("حجم معاملات")),
        "last_vs_close":None if close in (None,0) else abs(P-close)/abs(close),
        "intraday_range":None if None in (high,low) or P==0 else abs(high-low)/abs(P),
    }


def build_economic_ranking(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows=list(rows or [])
    d=[_derived(r) for r in rows]
    factor_scores={}
    for block,factors in FACTOR_WEIGHTS.items():
        for factor in factors:
            vals=[x.get(factor) for x in d]
            higher=factor in {"trade_value","volume","intrinsic_coverage","leverage_efficiency"}
            factor_scores[factor]=_rank(vals,higher)

    ranked=[]
    for i,row in enumerate(rows):
        blocks={}
        for block,factors in FACTOR_WEIGHTS.items():
            num=0.0; den=0.0
            for factor,w in factors.items():
                s=factor_scores[factor][i]
                if s is not None:
                    num += s*w; den += w
            blocks[block]=num/den*BLOCK_WEIGHTS[block] if den else None
        blocks["GREEKS"]=None
        available=[b for b in BLOCK_WEIGHTS if blocks.get(b) is not None]
        denom=sum(BLOCK_WEIGHTS[b] for b in available)
        score=sum(blocks[b] for b in available)*100.0/denom if denom else None
        ranked.append({
            "rank":None,
            "instrument_id":(row.get("identity") or {}).get("instrument_id"),
            "symbol":(row.get("canonical") or {}).get("نماد"),
            "contract_type":d[i]["contract_type"],
            "economic_score":round(score,4) if score is not None else None,
            "supported_blocks":available,
            "unavailable_blocks":[b for b in BLOCK_WEIGHTS if b not in available],
            "block_scores":{b:(round(blocks[b],4) if blocks[b] is not None else None) for b in BLOCK_WEIGHTS},
            "features":d[i],
        })
    ranked.sort(key=lambda x:(x["economic_score"] is not None,x["economic_score"] if x["economic_score"] is not None else -1),reverse=True)
    for n,x in enumerate(ranked,1):
        x["rank"]=n if x["economic_score"] is not None else None
    return {
        "status":"PASS" if any(x["economic_score"] is not None for x in ranked) else "NO_RANKABLE_EVIDENCE",
        "mode":"TSETMC_ECONOMIC_SCORING",
        "source_of_truth":"TSETMC",
        "ranking_scope":"OPPORTUNITY_CANDIDATES",
        "ranking_rows":ranked,
        "weights":BLOCK_WEIGHTS,
        "rules":{
            "economic_score":"relative_economic_efficiency_not_expected_return",
            "premium_burden":"lower_better",
            "intrinsic_coverage":"higher_better",
            "breakeven_distance":"lower_better",
            "leverage_efficiency":"bounded_monotonic_efficiency",
            "calendar_days":"supporting_factor_only",
            "missing_data":"UNAVAILABLE_NOT_ZERO",
            "iv":"NOT_USED",
            "greeks":"NOT_USED",
            "buy_sell_signal":"NOT_GENERATED",
        },
    }
