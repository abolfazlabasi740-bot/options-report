#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only historical evidence fusion for Equity opportunities."""
from __future__ import annotations
import hashlib,json
from typing import Any

ENGINE_VERSION="EQUITY-HISTORICAL-EVIDENCE-FUSION-SHADOW-1.0"

def _hash(v:Any)->str:
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def fuse_historical_evidence(opportunities:Any)->dict[str,Any]:
    rows=list((opportunities or {}).get("opportunities",[]) if isinstance(opportunities,dict) else opportunities or [])
    out=[]
    for o in rows:
        x=dict(o)
        c=x.get("historical_confirmation") or {}
        m=x.get("historical_memory") or {}
        p=x.get("historical_memory_profile") or {}
        status=str(c.get("status") or "NO_CROSS_SNAPSHOT_CONFIRMATION")
        level=str(m.get("level") or "NEW_OR_UNCONFIRMED")
        profile_continuity=str(p.get("continuity") or "")
        evidence=[]
        if status=="REPEATED_EVIDENCE": evidence.append("CROSS_SNAPSHOT_CONFIRMATION")
        if level!="NEW_OR_UNCONFIRMED": evidence.append("HISTORICAL_MEMORY")
        if profile_continuity in {"REPEATED","RECURRING"}: evidence.append("MEMORY_CONTINUITY")
        if not evidence: fusion_state="NO_HISTORICAL_CONFIRMATION"
        elif "RECURRING" in {level,profile_continuity}: fusion_state="RECURRING_HISTORICAL_EVIDENCE"
        elif "CROSS_SNAPSHOT_CONFIRMATION" in evidence: fusion_state="REPEATED_HISTORICAL_EVIDENCE"
        else: fusion_state="HISTORICAL_CONTEXT_PRESENT"
        x["historical_evidence_fusion"]={
            "state":fusion_state,
            "evidence":sorted(set(evidence)),
            "observation_count":int(c.get("observation_count") or m.get("observation_count") or 0),
            "recurrence_count":int(c.get("recurrence_count") or m.get("recurrence_count") or 0),
            "pattern_type":c.get("pattern_type"),
            "descriptive_only":True,
            "direction_inference":"DISABLED",
            "score_change":"NONE",
            "causal_inference":False,
            "engine_version":ENGINE_VERSION,
        }
        out.append(x)
    return {"status":"SUCCESS","engine_version":ENGINE_VERSION,
            "opportunity_count":len(out),"opportunities":out,
            "rules":{"source":"historical_confirmation_and_memory","direction_inference":"DISABLED",
                     "score_change":"NONE","causal_inference":False,"missing_data_policy":"NO_ZERO_FILL"},
            "fusion_sha256":_hash(out)}
