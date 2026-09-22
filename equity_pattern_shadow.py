#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only cross-snapshot equity pattern intelligence."""
from __future__ import annotations
import hashlib,json
from collections import Counter,defaultdict
from typing import Any,Iterable

ENGINE_VERSION="EQUITY-PATTERN-SHADOW-1.0"

def _hash(v:Any)->str:
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def _events(source:Any)->list[dict[str,Any]]:
    if not source:return []
    if isinstance(source,dict): return list(source.get("events",[]) or [])
    return list(source)

def analyze_cross_snapshot_patterns(events:Iterable[dict[str,Any]]|dict[str,Any],
                                    min_observations:int=2)->dict[str,Any]:
    rows=_events(events)
    groups=defaultdict(list)
    for e in rows:
        key=e.get("opportunity_key")
        if key:
            groups[str(key)].append(e)
    patterns=[]
    for key,items in sorted(groups.items()):
        items=sorted(items,key=lambda x:str(x.get("snapshot_id","")))
        if len(items)<min_observations: continue
        states=[str(x.get("state")) for x in items]
        transitions=[str(x.get("transition")) for x in items]
        active_items=[x for x in items if str(x.get("state")) != "RESOLVED"]
        active_observation_count=len(active_items)
        resolution_count=sum(str(x.get("state")) == "RESOLVED" for x in items)
        fams=sorted({f for x in items for f in (x.get("evidence_families") or [])})
        counts=dict(Counter(states))
        recurring=sum(s=="RECURRING" for s in states)
        pattern_type="REPEATED_OBSERVATION"
        if recurring: pattern_type="RECURRING_PATTERN"
        elif "STRENGTHENING" in states and "WEAKENING" in states: pattern_type="OSCILLATING_PATTERN"
        elif all(s in {"NEW","PERSISTENT","STRENGTHENING"} for s in states): pattern_type="PERSISTENT_OR_STRENGTHENING"
        patterns.append({
            "opportunity_key":key,
            "instrument_id":items[-1].get("instrument_id"),
            "type":pattern_type,
            "observation_count":active_observation_count,
            "timeline_event_count":len(items),
            "resolution_count":resolution_count,
            "snapshots":[x.get("snapshot_id") for x in items],
            "states":states,
            "transitions":transitions,
            "evidence_families":fams,
            "state_counts":counts,
            "recurrence_count":recurring,
            "first_seen_snapshot":items[0].get("snapshot_id"),
            "last_seen_snapshot":items[-1].get("snapshot_id"),
            "descriptive_only":True,
            "direction_inference":"DISABLED",
            "score_change":"NONE",
            "engine_version":ENGINE_VERSION,
        })
    out={"status":"SUCCESS","engine_version":ENGINE_VERSION,
         "pattern_count":len(patterns),"patterns":patterns,
         "rules":{"minimum_observations":min_observations,
                  "source":"lifecycle_events_only","causal_inference":False,
                  "direction_inference":"DISABLED","score_change":"NONE",
                  "missing_data_policy":"NO_ZERO_FILL",
                  "resolution_events_preserved":True}}
    out["patterns_sha256"]=_hash(patterns)
    return out
