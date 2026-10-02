#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chronological TSETMC-only pre-limit-up screening validation.

This is an evidence-only research classifier. The historical event is an
observable strong-upper-move proxy because retained historical snapshots do
not preserve the exchange's historical static-limit table. No exact
historical limit-up claim is made from this proxy.
"""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"
ENGINE_VERSION="PRE-LIMIT-UP-SCREEN-1.0"
SOURCE="TSETMC"
EVENT_THRESHOLD=0.055

def num(v):
    try:
        if v in (None,""): return None
        x=float(v); return x if math.isfinite(x) else None
    except: return None

def pct(a,b):
    return (a/b-1.0) if a is not None and b not in (None,0) else None

def load():
    rows=[]
    for p in sorted((OUT/"history"/"underlying").glob("*.json")):
        try: d=json.loads(p.read_text(encoding="utf-8"))
        except: continue
        if d.get("source_of_truth")!=SOURCE: continue
        iid=str(d.get("instrument_id") or "")
        for r in d.get("daily_history",{}).get("rows",[]) or []:
            if str(r.get("insCode") or "")!=iid: continue
            rows.append((iid,r))
    return rows

def features(history,i):
    closes=[num(x.get("pClosing")) for x in history[:i+1]]
    vols=[num(x.get("qTotTran5J")) for x in history[:i+1]]
    close=closes[-1] if closes else None
    def sma(a,n):
        a=[x for x in a if x is not None]
        return sum(a[-n:])/n if len(a)>=n else None
    sma5,sma20=sma(closes,5),sma(closes,20)
    v5,v20=sma(vols,5),sma(vols,20)
    r5=pct(close,closes[-6]) if len(closes)>=6 else None
    r20=pct(close,closes[-21]) if len(closes)>=21 else None
    vr=v5/v20 if v5 is not None and v20 not in (None,0) else None
    highs=[num(x.get("priceMax")) for x in history[max(0,i-19):i+1]]
    lows=[num(x.get("priceMin")) for x in history[max(0,i-19):i+1]]
    hi=max([x for x in highs if x is not None],default=None)
    lo=min([x for x in lows if x is not None],default=None)
    pos=(close-lo)/(hi-lo) if close is not None and hi is not None and lo is not None and hi>lo else None
    return {"return_5":r5,"return_20":r20,"volume_ratio_5_20":vr,
            "range_position_20":pos,"above_sma20": close>sma20 if close is not None and sma20 is not None else None}

def build():
    raw=load()
    by={}
    for iid,r in raw:
        by.setdefault(iid,[]).append(r)
    observations=[]
    for iid,h in by.items():
        h=sorted(h,key=lambda r:int(r.get("dEven") or 0))
        for i in range(20,len(h)-1):
            f=features(h,i)
            entry=num(h[i].get("pClosing"))
            nxt_high=num(h[i+1].get("priceMax"))
            event=pct(nxt_high,entry)
            if event is None: continue
            observations.append({"instrument_id":iid,"entry_date":str(h[i].get("dEven")),
              "forward_date":str(h[i+1].get("dEven")),"features":f,
              "next_session_high_return":event,
              "event_label":event>=EVENT_THRESHOLD})
    observations.sort(key=lambda x:(x["entry_date"],x["instrument_id"]))
    split=max(1,int(len(observations)*0.70))
    train,test=observations[:split],observations[split:]
    def vals(data,k): return sorted(x["features"][k] for x in data if x["features"].get(k) is not None)
    def q(v,p):
        if not v:return None
        j=(len(v)-1)*p; lo=int(j); hi=min(lo+1,len(v)-1)
        return v[lo]+(v[hi]-v[lo])*(j-lo)
    thresholds={k:q(vals(train,k),.75) for k in ("return_5","volume_ratio_5_20","range_position_20")}
    def trigger(x):
        f=x["features"]
        checks=[]
        if thresholds["return_5"] is not None: checks.append((f.get("return_5") or -999)>=thresholds["return_5"])
        if thresholds["volume_ratio_5_20"] is not None: checks.append((f.get("volume_ratio_5_20") or -999)>=thresholds["volume_ratio_5_20"])
        if thresholds["range_position_20"] is not None: checks.append((f.get("range_position_20") or -999)>=thresholds["range_position_20"])
        return sum(checks)>=2
    def metrics(data):
        tp=fp=fn=tn=0
        for x in data:
            pred=trigger(x); actual=x["event_label"]
            if pred and actual:tp+=1
            elif pred and not actual:fp+=1
            elif not pred and actual:fn+=1
            else:tn+=1
        n=tp+fp+fn+tn
        return {"rows":n,"TP":tp,"FP":fp,"FN":fn,"TN":tn,
                "precision":tp/(tp+fp) if tp+fp else None,
                "recall":tp/(tp+fn) if tp+fn else None}
    result={"status":"PASS" if len(test)>0 and len(train)>0 else "PARTIAL",
      "engine_version":ENGINE_VERSION,"source_of_truth":SOURCE,
      "event_definition":{"name":"NEXT_SESSION_STRONG_UPPER_MOVE_PROXY",
        "threshold":EVENT_THRESHOLD,
        "definition":"next retained TSETMC session high >= 5.5% above entry close",
        "historical_exact_limit_table_available":False,
        "exact_limit_up_claim":False},
      "dataset":{"observation_count":len(observations),"train_count":len(train),"test_count":len(test),
                 "split":"chronological_70_30","instrument_count":len(by)},
      "thresholds":{"source":"TRAINING_ONLY_P75","values":thresholds,"rule":"at_least_2_of_3"},
      "train_metrics":metrics(train),"out_of_sample_metrics":metrics(test),
      "rules":{"matching":"TSETMC instrument and chronological daily observations",
               "signal_generation":"FORBIDDEN","production_buy_sell":False,
               "interpretation":"screening validation only; not a claim that the proxy predicts exchange limit-up events"},
      "evidence_sha256":None}
    canonical=json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    result["evidence_sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    OUT.mkdir(exist_ok=True)
    (OUT/"pre_limit_up_validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STATUS=",result["status"],"TRAIN=",len(train),"TEST=",len(test),"OOS=",json.dumps(result["out_of_sample_metrics"],ensure_ascii=False),"SHA=",result["evidence_sha256"])
    return result
if __name__=="__main__": build()
