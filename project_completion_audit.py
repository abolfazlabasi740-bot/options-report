#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal operational completion check for OptimusAI V4.1."""
from __future__ import annotations
import json, os
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"
STATE=ROOT/"PROJECT_FINISHER_STATE.json"

def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def main():
    report=OUT/"latest_report.txt"
    audit=OUT/"latest_audit.json"
    runtime=OUT/"runtime_verification.json"
    state=load(STATE)
    report_text=report.read_text(encoding="utf-8",errors="ignore") if report.exists() else ""
    report_ok=report.exists() and "TSETMC" in report_text and "RANKING_STATUS" in report_text
    audit_ok=load(audit).get("status")=="PASS"
    runtime_ok=load(runtime).get("status")=="PASS"
    bale_receipt=state.get("bale_receipt")
    bale_ok=bool(bale_receipt) and "FAILED" not in str(bale_receipt) and "MISSING" not in str(bale_receipt)
    checks={
      "report_generated":report_ok,
      "audit_integrity_pass":audit_ok,
      "runtime_pass":runtime_ok,
      "bale_delivery_receipt_present":bale_ok,
    }
    complete=all(checks.values())
    out={
      "status":"COMPLETE" if complete else "IN_PROGRESS",
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "checks":checks,
      "blockers":[k for k,v in checks.items() if not v],
      "scope":"OPERATIONAL_TSETMC_REPORT_AND_BALE",
      "excluded_optional_work":["G7-5","historical_pre_limit_up_validation","strategy_risk_shadow_validation","news_codal_enrichment","bulk_evidence_archives"],
      "production_buy_sell":False,
    }
    p=OUT/"project_completion_audit.json"
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("STATUS=",out["status"])
    for k,v in checks.items(): print(f"{k.upper()}={'PASS' if v else 'FAIL'}")
    if out["blockers"]: print("BLOCKERS=",",".join(out["blockers"]))
if __name__=="__main__": main()
