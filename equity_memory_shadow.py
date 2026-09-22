#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only multi-level historical memory for Equity opportunities."""
from __future__ import annotations
import hashlib,json
from typing import Any

ENGINE_VERSION="EQUITY-MEMORY-SHADOW-1.0"

def _hash(v:Any)->str:
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def classify_confirmation(c:dict[str,Any]|None)->str:
    if not c or c.get("status")!="REPEATED_EVIDENCE":
        return "NEW_OR_UNCONFIRMED"
    p=str(c.get("pattern_type") or "")
    n=int(c.get("observation_count") or 0)
    r=int(c.get("recurrence_count") or 0)
    if p=="RECURRING_PATTERN" or r>0: return "RECURRING"
    if p=="OSCILLATING_PATTERN": return "OSCILLATING"
    if p=="PERSISTENT_OR_STRENGTHENING": return "PERSISTENT_OR_STRENGTHENING"
    if n>=2: return "REPEATED"
    return "NEW_OR_UNCONFIRMED"

def build_memory(opportunities:Any)->dict[str,Any]:
    rows=list((opportunities or {}).get("opportunities",[]) if isinstance(opportunities,dict) else opportunities or [])
    out=[]
    for o in rows:
        x=dict(o)
        c=x.get("historical_confirmation")
        level=classify_confirmation(c)
        x["historical_memory"]={
            "level":level,
            "observation_count":int((c or {}).get("observation_count") or 0),
            "recurrence_count":int((c or {}).get("recurrence_count") or 0),
            "pattern_type":(c or {}).get("pattern_type"),
            "source":"LIFECYCLE_CROSS_SNAPSHOT_EVIDENCE",
            "direction_inference":"DISABLED",
            "score_change":"NONE",
            "causal_inference":False,
            "engine_version":ENGINE_VERSION,
        }
        out.append(x)
    return {"status":"SUCCESS","engine_version":ENGINE_VERSION,
            "opportunity_count":len(out),"opportunities":out,
            "rules":{"source":"historical_confirmation_only","direction_inference":"DISABLED",
                     "score_change":"NONE","causal_inference":False,"missing_data_policy":"NO_ZERO_FILL"},
            "memory_sha256":_hash(out)}

