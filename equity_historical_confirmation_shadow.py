#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only historical confirmation for Equity opportunities."""
from __future__ import annotations
import hashlib,json
from typing import Any
from equity_opportunity_lifecycle_shadow import opportunity_key

ENGINE_VERSION="EQUITY-HISTORICAL-CONFIRMATION-SHADOW-1.0"

def _hash(v:Any)->str:
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def enrich_opportunities(opportunities:Any, cross_snapshot_patterns:Any=None)->dict[str,Any]:
    opps=list((opportunities or {}).get("opportunities",[]) if isinstance(opportunities,dict) else opportunities or [])
    patterns=list((cross_snapshot_patterns or {}).get("patterns",[]) if isinstance(cross_snapshot_patterns,dict) else cross_snapshot_patterns or [])
    pmap={str(p.get("opportunity_key")):p for p in patterns if p.get("opportunity_key")}
    out=[]
    for o in opps:
        x=dict(o)
        key=opportunity_key(x)
        p=pmap.get(key)
        if p:
            x["historical_confirmation"]={
                "status":"REPEATED_EVIDENCE",
                "pattern_type":p.get("type"),
                "observation_count":p.get("observation_count"),
                "recurrence_count":p.get("recurrence_count",0),
                "first_seen_snapshot":p.get("first_seen_snapshot"),
                "last_seen_snapshot":p.get("last_seen_snapshot"),
                "evidence_families":p.get("evidence_families",[]),
            }
        else:
            x["historical_confirmation"]={
                "status":"NO_CROSS_SNAPSHOT_CONFIRMATION",
                "observation_count":0,
                "reason":"No matching multi-snapshot lifecycle pattern was supplied."
            }
        x["historical_confirmation"]["direction_inference"]="DISABLED"
        x["historical_confirmation"]["score_change"]="NONE"
        x["historical_confirmation"]["engine_version"]=ENGINE_VERSION
        out.append(x)
    return {
        "status":"SUCCESS","engine_version":ENGINE_VERSION,
        "opportunity_count":len(out),"opportunities":out,
        "rules":{"source":"cross_snapshot_patterns_only","direction_inference":"DISABLED",
                 "score_change":"NONE","causal_inference":False,"missing_data_policy":"NO_ZERO_FILL"},
        "opportunities_sha256":_hash(out),
    }
