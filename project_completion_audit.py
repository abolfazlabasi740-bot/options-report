#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only completion audit for OptimusAI V4.1."""
from __future__ import annotations
import json, os, hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"
STATE=ROOT/"PROJECT_FINISHER_STATE.json"
CONTRACT=ROOT/"docs/PROJECT_COMPLETION_CONTRACT_V2.md"

def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def exists(name): return (ROOT/name).exists()

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def main():
    report=OUT/"latest_report.txt"
    audit=OUT/"latest_audit.json"
    runtime=OUT/"runtime_verification.json"
    g75=OUT/"g7_5_economic_validation_evidence.json"
    bale=OUT/"bale_delivery_verification.json"
    state=load(STATE)
    evidence=load(g75)
    runtime_d=load(runtime)
    audit_d=load(audit)
    closure=(evidence.get("closure") or {}).get("g7_5_status")
    report_text=report.read_text(encoding="utf-8",errors="ignore") if report.exists() else ""
    report_ok=report.exists() and "TSETMC" in report_text and "RANKING_STATUS" in report_text
    audit_ok=audit_d.get("status")=="PASS"
    runtime_ok=runtime_d.get("status")=="PASS"
    bale_receipt=state.get("bale_receipt")
    track_a = report_ok and audit_ok and runtime_ok and bool(bale_receipt)
    track_b = closure=="VERIFIED" and int(evidence.get("observed_transition_count") or 0)>0 and int(evidence.get("matched_transition_count") or 0)>0
    c=load(OUT/"pre_limit_up_validation.json")
    c_metrics=c.get("out_of_sample_metrics") or {}
    track_c = c.get("status")=="PASS" and int((c.get("dataset") or {}).get("test_count") or 0)>0 and "precision" in c_metrics and "recall" in c_metrics and (c.get("current_session_alert") or {}).get("status")=="PASS"
    c_reason=None if track_c else "chronological pre-limit-up screening evidence is incomplete"
    track_d = report_ok and audit_ok and runtime_ok and evidence.get("source_of_truth")=="TSETMC" and int(evidence.get("source_snapshot_count") or 0)>0
    strategy=(ROOT/"docs/STRATEGY_POLICY_V1.md").read_text(encoding="utf-8") if exists("docs/STRATEGY_POLICY_V1.md") else ""
    risk=(ROOT/"docs/RISK_POLICY_V1.md").read_text(encoding="utf-8") if exists("docs/RISK_POLICY_V1.md") else ""
    shadow=load(OUT/"strategy_risk_shadow_validation.json")
    shadow_oos=shadow.get("out_of_sample_validation") or {}
    track_e = shadow.get("status")=="PASS" and int((shadow.get("calibration") or {}).get("oos_count") or 0)>0 and bool(shadow.get("strategy_policy")) and bool(shadow.get("risk_policy")) and shadow.get("production_buy_sell") is False
    e_reason=None if track_e else "shadow strategy/risk validation evidence is incomplete"
    worker_alive=False
    try:
        pid=int((OUT/"project_finisher_agent.pid").read_text().strip())
        os.kill(pid,0); worker_alive=True
    except Exception: pass
    last_cycle=state.get("last_cycle") or []
    cycle_pass = bool(last_cycle) and all(x.get("status")=="PASS" for x in last_cycle)
    track_f = worker_alive and cycle_pass and bool(bale_receipt)
    f_reason=None if track_f else "worker/next-full-cycle/Bale receipt evidence is incomplete"

    tracks={
      "A":{"status":"PASS" if track_a else "PARTIAL","reason":None if track_a else "report/audit/runtime/Bale evidence incomplete"},
      "B":{"status":"PASS" if track_b else "PARTIAL","reason":None if track_b else "G7-5 historical evidence incomplete"},
      "C":{"status":"PASS" if track_c else "PARTIAL","reason":c_reason},
      "D":{"status":"PASS" if track_d else "PARTIAL","reason":None if track_d else "TSETMC context evidence incomplete"},
      "E":{"status":"PASS" if track_e else "SHADOW_ONLY","reason":e_reason},
      "F":{"status":"PASS" if track_f else "PARTIAL","reason":f_reason},
    }
    blockers=[f"TRACK_{k}: {v['reason']}" for k,v in tracks.items() if v["status"]!="PASS" and v["reason"]]
    complete=all(v["status"]=="PASS" for v in tracks.values())
    out={
      "status":"COMPLETE" if complete else "IN_PROGRESS",
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "contract_sha256":sha(CONTRACT) if CONTRACT.exists() else None,
      "tracks":tracks,
      "blockers":blockers,
      "production_buy_sell":False,
      "evidence":{"report_sha256":sha(report) if report.exists() else None,
                  "audit_sha256":sha(audit) if audit.exists() else None,
                  "runtime_sha256":sha(runtime) if runtime.exists() else None,
                  "g7_5_sha256":sha(g75) if g75.exists() else None,
                  "pre_limit_up_sha256":sha(OUT/"pre_limit_up_validation.json") if (OUT/"pre_limit_up_validation.json").exists() else None,
                  "strategy_risk_sha256":sha(OUT/"strategy_risk_shadow_validation.json") if (OUT/"strategy_risk_shadow_validation.json").exists() else None},
      "notes":[
        "Evidence-only audit; never fabricates completion.",
        "News/Codal remain outside approved completion scope.",
        "Production BUY/SELL remains forbidden."
      ]
    }
    p=OUT/"project_completion_audit.json"
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("STATUS=",out["status"])
    for k,v in tracks.items(): print(f"TRACK_{k}={v['status']} | {v['reason'] or 'PASS'}")
    print("AUDIT_SHA256=",sha(p))
if __name__=="__main__": main()
