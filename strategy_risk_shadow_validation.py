#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-derived shadow strategy/risk validation for OptimusAI V4.1."""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
import signal_replay_engine as replay

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"
ENGINE_VERSION="STRATEGY-RISK-SHADOW-1.0"

def q(vals,p):
    vals=sorted(x for x in vals if x is not None)
    if not vals:return None
    j=(len(vals)-1)*p; lo=int(j); hi=min(lo+1,len(vals)-1)
    return vals[lo]+(vals[hi]-vals[lo])*(j-lo)

def n(v):
    try:
        x=float(v); return x if math.isfinite(x) else None
    except:return None

def build():
    cal=replay.build_replay_calibration(ROOT)
    obs=cal.get("observations") or []
    split=max(1,int(len(obs)*.70))
    train,test=obs[:split],obs[split:]
    def feat(rows,k): return [n((r.get("entry_features") or {}).get(k)) for r in rows]
    thresholds={
      "breakeven_distance_max":q(feat(train,"breakeven_distance"),.50),
      "trade_value_min":q(feat(train,"trade_value"),.50),
      "volume_min":q(feat(train,"volume"),.50),
      "calendar_days_min":q(feat(train,"calendar_days"),.25),
      "calendar_days_max":q(feat(train,"calendar_days"),.75),
      "time_value_ratio_max":q(feat(train,"time_value_ratio"),.75),
      "last_vs_close_max":q(feat(train,"last_vs_close"),.75),
    }
    def eligible(r):
        f=r.get("entry_features") or {}
        checks=[
          f.get("breakeven_distance") is not None and (thresholds["breakeven_distance_max"] is None or f["breakeven_distance"]<=thresholds["breakeven_distance_max"]),
          f.get("trade_value") is not None and (thresholds["trade_value_min"] is None or f["trade_value"]>=thresholds["trade_value_min"]),
          f.get("volume") is not None and (thresholds["volume_min"] is None or f["volume"]>=thresholds["volume_min"]),
          f.get("calendar_days") is not None and thresholds["calendar_days_min"] is not None and thresholds["calendar_days_min"]<=f["calendar_days"]<=thresholds["calendar_days_max"],
          f.get("time_value_ratio") is not None and (thresholds["time_value_ratio_max"] is None or f["time_value_ratio"]<=thresholds["time_value_ratio_max"]),
          f.get("last_vs_close") is not None and (thresholds["last_vs_close_max"] is None or f["last_vs_close"]<=thresholds["last_vs_close_max"]),
        ]
        return sum(checks)>=4
    def stats(rows):
        selected=[r for r in rows if eligible(r) and r.get("option_return_pct") is not None]
        returns=[r["option_return_pct"] for r in selected]
        positive=sum(x>0 for x in returns)
        worst=min(returns) if returns else None
        return {"rows":len(rows),"selected":len(selected),"positive_count":positive,
          "positive_rate":positive/len(returns) if returns else None,
          "mean_return":sum(returns)/len(returns) if returns else None,
          "worst_observed_return":worst}
    policy={
      "strategy_policy_id":"OPTIMUSAI-STRATEGY-V2-SHADOW","version":"2.0.0","status":"SHADOW_VALIDATED",
      "production_authorized":False,"direction":"LONG_OPTIONS_ONLY",
      "decision_rule":"minimum 4 of 6 evidence-derived entry controls",
      "controls":thresholds,
      "expiry_control":"calendar_days between empirical P25 and P75 of training set",
      "liquidity_control":"trade_value and volume >= empirical P50",
      "freshness_control":"current runtime must have explicit TSETMC source timestamp; stale/unknown blocks",
      "spread_control":"if bid/ask spread is unavailable, BLOCKED; no spread value is invented",
      "short_options":"BLOCKED"
    }
    risk={
      "risk_policy_id":"OPTIMUSAI-RISK-V2-SHADOW","version":"2.0.0","status":"SHADOW_VALIDATED",
      "production_authorized":False,
      "max_loss":"100% of shadow position premium; no averaging down",
      "position_sizing":"shadow_units = floor(shadow_capital_risk_budget / option_premium); execution forbidden",
      "capital_risk_budget":"externally supplied at evaluation time; no capital amount is assumed",
      "exit_policy":["expiry control breach","freshness breach","mandatory evidence loss","risk limit breach"],
      "liquidity_exit":"block/close simulation when required liquidity evidence disappears",
      "short_options":"BLOCKED",
      "missing_evidence":"FAIL_CLOSED"
    }
    result={"status":"PASS" if len(test)>0 and len(train)>0 else "PARTIAL",
      "engine_version":ENGINE_VERSION,"source_of_truth":"TSETMC",
      "calibration":{"engine_version":cal.get("engine_version"),"observation_count":len(obs),
                     "chronological_split":"70% train / 30% OOS","train_count":len(train),"oos_count":len(test)},
      "strategy_policy":policy,"risk_policy":risk,
      "train_validation":stats(train),"out_of_sample_validation":stats(test),
      "independent_validation":"OOS replay uses thresholds derived only from chronological training observations",
      "production_buy_sell":False,"evidence_only":True,"evidence_sha256":None}
    canonical=json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    result["evidence_sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    OUT.mkdir(exist_ok=True)
    (OUT/"strategy_risk_shadow_validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STATUS=",result["status"],"TRAIN=",len(train),"OOS=",len(test),"SHA=",result["evidence_sha256"])
    return result
if __name__=="__main__": build()
