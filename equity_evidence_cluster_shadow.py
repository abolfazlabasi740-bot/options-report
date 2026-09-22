#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic evidence clustering for standalone equity intelligence."""
from __future__ import annotations
import hashlib,json
from collections import defaultdict
ENGINE_VERSION="EQUITY-CLUSTER-SHADOW-1.0"
MIN_FAMILIES=2

def _hash(v):
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def build_equity_evidence_clusters(cases, historical_patterns=None, red_team=None):
    cases=list(cases or [])
    groups=defaultdict(list)
    for c in cases:
        if c.get("status")!="OBSERVED": continue
        iid=str(c.get("instrument_id") or "").strip()
        fam=str(c.get("family") or "").strip()
        if iid and fam: groups[iid].append(c)
    patterns=historical_patterns or {}
    pmap=defaultdict(list)
    for p in patterns.get("patterns",[]) or []:
        iid=p.get("instrument_id") or p.get("identity") or p.get("symbol")
        if iid: pmap[str(iid)].append(p)
    rmap={str(x.get("case_id")):x for x in (red_team or {}).get("cases",[]) or []}
    clusters=[]
    for iid in sorted(groups):
        fams=defaultdict(list); contradictions=[]
        for c in sorted(groups[iid],key=lambda x:str(x.get("case_id",""))):
            fams[c["family"]].append(c["case_id"])
            if c.get("case_id") in rmap: contradictions.append(rmap[c["case_id"]])
        if len(fams)<MIN_FAMILIES: continue
        refs=[{"family":f,"case_ids":sorted(ids),"case_count":len(ids)} for f,ids in sorted(fams.items())]
        payload={"engine_version":ENGINE_VERSION,"instrument_id":iid,
                 "independent_family_count":len(refs),"case_ids":sorted(x for ids in fams.values() for x in ids),
                 "historical_pattern_count":len(pmap.get(iid,[])),"contradiction_count":len(contradictions)}
        cl={**payload,"status":"MULTI_FAMILY_OBSERVED","supporting_evidence":refs,
            "historical_patterns":pmap.get(iid,[]),"contradictory_evidence":contradictions,
            "direction_inference":"DISABLED","score_change":"NONE"}
        cl["cluster_id"]=_hash(payload)[:24]; cl["cluster_sha256"]=_hash(cl); clusters.append(cl)
    out={"status":"SUCCESS","engine_version":ENGINE_VERSION,
         "summary":{"cluster_count":len(clusters),"max_independent_family_count":max((x["independent_family_count"] for x in clusters),default=0)},
         "clusters":clusters,
         "rules":{"minimum_families":MIN_FAMILIES,"only_observed_cases":True,"direction_inference":"DISABLED","score_change":"NONE"}}
    out["clusters_sha256"]=_hash(clusters)
    return out
