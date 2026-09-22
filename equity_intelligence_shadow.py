#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only standalone equity intelligence for V4.1."""
from __future__ import annotations
import hashlib, json, math
from typing import Any
import pandas as pd

ENGINE_VERSION = "EQUITY-INTELLIGENCE-SHADOW-1.0"

def _num(row, *names):
    for name in names:
        if name not in row.index: continue
        try:
            v=row.get(name)
            if v is None or pd.isna(v): continue
            v=float(v)
            if math.isfinite(v): return v
        except (TypeError, ValueError): pass
    return None

def _hash(value):
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()
    return hashlib.sha256(raw).hexdigest()

def _case(snapshot_id,iid,family,status,evidence,reason):
    return {"snapshot_id":snapshot_id,"instrument_id":iid,"family":family,
            "status":status,"evidence":evidence,
            "case_id":f"{snapshot_id}:{family}:{iid}",
            "engine_version":ENGINE_VERSION,"reason":reason,
            "direction_inference":"DISABLED","score_change":"NONE"}

def _price(row,s,i):
    last=_num(row,"last_price","آخرین قیمت","آخرین"); close=_num(row,"close_price","قیمت پایانی","پایانی")
    ev=[{"name":"last_price","value":last,"source":"explicit_market_field"},{"name":"close_price","value":close,"source":"explicit_market_field"}]
    if last is None or close in (None,0): st="INSUFFICIENT_DATA"
    else:
        ev.append({"name":"last_vs_close_pct","value":(last-close)/abs(close)*100,"source":"derived_from_explicit_fields"}); st="OBSERVED"
    return _case(s,i,"PRICE_STRUCTURE",st,ev,"Explicit price structure is observable; no directional conclusion is inferred.")

def _liquidity(row,s,i):
    vals=[("volume",_num(row,"volume","حجم معاملات","حجم")),("trade_value",_num(row,"trade_value","ارزش معاملات","ارزش")),("trade_count",_num(row,"trade_count","تعداد معاملات"))]
    ev=[{"name":n,"value":v,"source":"explicit_market_field"} for n,v in vals]
    st="OBSERVED" if any(v is not None for _,v in vals) else "INSUFFICIENT_DATA"
    return _case(s,i,"LIQUIDITY",st,ev,"Explicit liquidity fields are retained for evidence review.")

def _price_volume(row,s,i):
    ret=_num(row,"return_pct","بازده"); vc=_num(row,"volume_change_pct","تغییر حجم درصدی")
    ev=[{"name":"return_pct","value":ret,"source":"market_history_or_explicit_field"},{"name":"volume_change_pct","value":vc,"source":"market_history_or_explicit_field"}]
    if ret is None or vc is None: st="INSUFFICIENT_DATA"
    else:
        rel="CONCORDANT" if (ret>0 and vc>0) or (ret<0 and vc<0) else "DIVERGENT" if ret!=0 and vc!=0 else "NEUTRAL"
        ev.append({"name":"price_volume_relationship","value":rel,"source":"derived_from_explicit_fields"}); st="OBSERVED"
    return _case(s,i,"PRICE_VOLUME",st,ev,"Price/volume relationship is descriptive evidence only.")

def _flow(row,s,i):
    vals=[]
    for n in ("individual_net_flow","legal_net_flow","حقیقی_خالص","حقوقی_خالص"):
        v=_num(row,n)
        if v is not None: vals.append((n,v))
    ev=[{"name":n,"value":v,"source":"explicit_flow_field"} for n,v in vals]
    return _case(s,i,"FLOW","OBSERVED" if vals else "INSUFFICIENT_DATA",ev,"Explicit investor-flow evidence is retained without interpreting intent.")

def _relative(row,s,i):
    sr=_num(row,"return_pct","بازده"); br=_num(row,"benchmark_return_pct","بازده شاخص")
    ev=[{"name":"equity_return_pct","value":sr,"source":"explicit_market_field"},{"name":"benchmark_return_pct","value":br,"source":"explicit_benchmark_field"}]
    if sr is None or br is None: st="INSUFFICIENT_DATA"
    else:
        ev.append({"name":"relative_return_difference_pct","value":sr-br,"source":"derived_from_explicit_fields"}); st="OBSERVED"
    return _case(s,i,"MARKET_RELATIVE",st,ev,"Relative market evidence requires an explicit benchmark.")

def _historical(row,s,i):
    p=row.get("historical_pattern") if "historical_pattern" in row.index else None
    ev=[{"name":"historical_pattern","value":p,"source":"historical_pattern_shadow"}]
    ok=p is not None and not pd.isna(p) and p!=""
    return _case(s,i,"HISTORICAL_PATTERN","OBSERVED" if ok else "INSUFFICIENT_DATA",ev,"Historical pattern is descriptive prior evidence only.")

def analyze_equities(df: pd.DataFrame, snapshot_id: str):
    if not isinstance(df,pd.DataFrame): raise TypeError("df must be a pandas DataFrame")
    if not str(snapshot_id).strip(): raise ValueError("snapshot_id is required")
    col=next((c for c in ("instrument_id","insCode","InstrumentID","کد معاملاتی") if c in df.columns),None)
    if col is None:
        return {"status":"INSUFFICIENT_DATA","engine_version":ENGINE_VERSION,"snapshot_id":str(snapshot_id),
                "reason":"EXPLICIT_EQUITY_INSTRUMENT_ID_REQUIRED","cases":[],"summary":{}}
    cases=[]
    for _,row in df.iterrows():
        iid=str(row.get(col) or "").strip()
        if not iid or iid.lower() in {"nan","none"}: continue
        for fn in (_price,_liquidity,_price_volume,_flow,_relative,_historical): cases.append(fn(row,str(snapshot_id),iid))
    result={"status":"SUCCESS","engine_version":ENGINE_VERSION,"snapshot_id":str(snapshot_id),
            "analysis_mode":"EQUITY_ONLY",
            "summary":{"instrument_count":len({c["instrument_id"] for c in cases}),
                       "cases_total":len(cases),"observed_total":sum(c["status"]=="OBSERVED" for c in cases),
                       "insufficient_total":sum(c["status"]=="INSUFFICIENT_DATA" for c in cases)},
            "cases":cases,
            "rules":{"explicit_instrument_id_required":True,"symbol_inference":False,
                     "direction_inference":"DISABLED","score_change":"NONE","missing_data_policy":"INSUFFICIENT_DATA"}}
    result["cases_sha256"]=_hash(cases)
    return result
