#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only historical memory profile for Equity opportunities."""
from __future__ import annotations
import hashlib,json
from typing import Any

ENGINE_VERSION="EQUITY-MEMORY-PROFILE-SHADOW-1.0"

def _hash(v:Any)->str:
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def build_memory_profiles(opportunities:Any)->dict[str,Any]:
    rows=list((opportunities or {}).get("opportunities",[]) if isinstance(opportunities,dict) else opportunities or [])
    profiles=[]
    for o in rows:
        h=o.get("historical_memory") or {}
        c=o.get("historical_confirmation") or {}
        states=[]
        if h.get("level"): states.append(h["level"])
        if c.get("pattern_type"): states.append(c["pattern_type"])
        obs=int(c.get("observation_count") or h.get("observation_count") or 0)
        rec=int(c.get("recurrence_count") or h.get("recurrence_count") or 0)
        if rec>0:
            continuity="RECURRING"
        elif obs>1:
            continuity="REPEATED"
        else:
            continuity="SINGLE_OR_UNCONFIRMED"
        profiles.append({
            "instrument_id":o.get("instrument_id"),
            "opportunity_id":o.get("opportunity_id"),
            "opportunity_type":o.get("type"),
            "evidence_families":sorted(o.get("evidence_families") or []),
            "memory_level":h.get("level","NEW_OR_UNCONFIRMED"),
            "continuity":continuity,
            "observation_count":obs,
            "recurrence_count":rec,
            "pattern_type":c.get("pattern_type"),
            "first_seen_snapshot":c.get("first_seen_snapshot"),
            "last_seen_snapshot":c.get("last_seen_snapshot"),
            "historical_evidence_present":obs>1,
            "descriptive_only":True,
            "direction_inference":"DISABLED",
            "score_change":"NONE",
            "engine_version":ENGINE_VERSION,
        })
    return {"status":"SUCCESS","engine_version":ENGINE_VERSION,
            "profile_count":len(profiles),"profiles":profiles,
            "rules":{"source":"equity_historical_memory_only","causal_inference":False,
                     "direction_inference":"DISABLED","score_change":"NONE",
                     "missing_data_policy":"NO_ZERO_FILL"},
            "profiles_sha256":_hash(profiles)}
