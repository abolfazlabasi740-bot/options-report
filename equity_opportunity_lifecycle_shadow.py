#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auditable cross-snapshot lifecycle memory for Equity opportunities."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Iterable

ENGINE_VERSION="EQUITY-LIFECYCLE-SHADOW-1.0"
STATES={"NEW","PERSISTENT","STRENGTHENING","WEAKENING","RECURRING","RESOLVED"}

def _hash(v:Any)->str:
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def opportunity_key(o:dict[str,Any])->str:
    iid=str(o.get("instrument_id") or "").strip()
    typ=str(o.get("type") or "").strip()
    fams="|".join(sorted(str(x) for x in (o.get("evidence_families") or []) if x))
    return f"{iid}::{typ}::{fams}"

def load_events(path:str|Path)->list[dict[str,Any]]:
    p=Path(path)
    if not p.exists(): return []
    out=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip(): out.append(json.loads(line))
    return out

def _strength(status:str|None)->int:
    return {"REJECTED":0,"INSUFFICIENT_DATA":1,"WATCH":2,"CONFIRMED":3}.get(status or "",1)

def append_opportunity_events(path:str|Path,snapshot_id:str,opportunities:Iterable[dict[str,Any]])->dict[str,Any]:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    prior=load_events(p); latest={}
    for e in prior:
        if e.get("opportunity_key"): latest[e["opportunity_key"]]=e
    current=list(opportunities); keys=set(); events=[]
    for o in current:
        key=opportunity_key(o)
        if not key: continue
        keys.add(key); old=latest.get(key); cur=_strength(o.get("status"))
        if old is None:
            state="NEW"; transition="FIRST_SEEN"; first=snapshot_id; count=1
        else:
            first=old.get("first_seen_snapshot") or old.get("snapshot_id")
            count=int(old.get("seen_count",0))+1
            prev=int(old.get("strength",1)); old_state=old.get("state")
            if old_state=="RESOLVED": state="RECURRING"; transition="RECURRED"
            elif cur>prev: state="STRENGTHENING"; transition="STRENGTH_INCREASED"
            elif cur<prev: state="WEAKENING"; transition="STRENGTH_DECREASED"
            else: state="PERSISTENT"; transition="PERSISTED"
        events.append({
            "engine_version":ENGINE_VERSION,"snapshot_id":snapshot_id,
            "opportunity_key":key,"opportunity_id":o.get("opportunity_id"),
            "instrument_id":o.get("instrument_id"),"type":o.get("type"),
            "status":o.get("status"),"strength":cur,"state":state,
            "transition":transition,"first_seen_snapshot":first,"seen_count":count,
            "evidence_families":sorted(o.get("evidence_families") or []),
            "cluster_id":o.get("cluster_id"),
            "red_team_challenges":list(o.get("red_team_challenges") or []),
            "red_team_challenge_count":len(o.get("red_team_challenges") or []),
        })
    for key,old in latest.items():
        if key in keys or old.get("state")=="RESOLVED": continue
        events.append({
            "engine_version":ENGINE_VERSION,"snapshot_id":snapshot_id,
            "opportunity_key":key,"opportunity_id":old.get("opportunity_id"),
            "instrument_id":old.get("instrument_id"),"type":old.get("type"),
            "status":"REJECTED","strength":0,"state":"RESOLVED",
            "transition":"DISAPPEARED_FROM_CURRENT_SNAPSHOT",
            "first_seen_snapshot":old.get("first_seen_snapshot"),
            "seen_count":int(old.get("seen_count",0)),
            "evidence_families":old.get("evidence_families",[]),
            "cluster_id":old.get("cluster_id"),
            "red_team_challenges":old.get("red_team_challenges",[]),
            "red_team_challenge_count":len(old.get("red_team_challenges",[]) or []),
        })
    events.sort(key=lambda e:(e["opportunity_key"],e["state"],str(e.get("opportunity_id") or "")))
    with p.open("a",encoding="utf-8") as f:
        for e in events: f.write(json.dumps(e,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n")
    return {"status":"SUCCESS","engine_version":ENGINE_VERSION,"snapshot_id":snapshot_id,
            "events_written":len(events),"opportunity_count":len(current),
            "resolved_count":sum(e["state"]=="RESOLVED" for e in events),
            "states":sorted({e["state"] for e in events}),"file":p.name,
            "events_sha256":_hash(events)}

def current_state(path:str|Path)->dict[str,dict[str,Any]]:
    latest={}
    for e in load_events(path):
        if e.get("opportunity_key"): latest[e["opportunity_key"]]=e
    return latest
