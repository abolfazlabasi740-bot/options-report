#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Direct Termux diagnostic receipt publisher; bypasses the command bridge."""
import base64, json, os, subprocess, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path.home()/"OptimusAI_V41_LIVE"
OUT=ROOT/"output"/"termux_root_cause"
OUT.mkdir(parents=True,exist_ok=True)
def read(path, limit=14000):
    try: return Path(path).read_text(encoding="utf-8",errors="replace")[-limit:]
    except Exception as e: return "UNAVAILABLE: "+type(e).__name__+": "+str(e)
def cmd(args,timeout=12):
    try:
        p=subprocess.run(args,cwd=str(ROOT),text=True,capture_output=True,timeout=timeout)
        return {"exit_code":p.returncode,"stdout":p.stdout[-6000:],"stderr":p.stderr[-3000:]}
    except Exception as e: return {"error":type(e).__name__+": "+str(e)}
def http(path,payload=None,timeout=5):
    url="http://127.0.0.1:8080/v1/"+path
    try:
        data=json.dumps(payload).encode() if payload is not None else None
        req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json","Authorization":"Bearer local"})
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return {"http_status":r.status,"body":r.read(10000).decode("utf-8","replace")}
    except Exception as e: return {"error":type(e).__name__+": "+str(e)}
status_raw=read(OUT/"repair_status.json",8000)
try: status=json.loads(status_raw)
except Exception: status={"raw":status_raw}
report_raw=read(OUT/"repair_report.json",14000)
try: report=json.loads(report_raw)
except Exception: report={"raw":report_raw}
models=http("models",timeout=4)
inference=None
if "http_status" in models:
    model=os.environ.get("OPTIMUSAI_LLM_MODEL","Qwen/Qwen3-4B-GGUF:Q4_K_M")
    inference=http("chat/completions",{"model":model,"messages":[{"role":"user","content":"Reply exactly LLM_INFERENCE_OK"}],"max_tokens":16,"temperature":0},timeout=35)
receipt={
 "receipt_type":"DIRECT_TERMUX_DIAGNOSTIC_BYPASS_BRIDGE",
 "collected_at":datetime.now(timezone.utc).isoformat(),
 "project_head":cmd(["git","rev-parse","HEAD"]),
 "git_status":cmd(["git","status","--short"]),
 "repair_pid":read(OUT/"repair_agent.pid",500).strip(),
 "repair_status":status,
 "repair_report":report,
 "repair_log_tail":read(OUT/"repair_agent.log",18000),
 "bridge_log_tail":read(Path.home()/".termux_command_bridge"/"bridge_agent.log",18000),
 "processes":cmd(["ps","-A","-o","pid,ppid,stat,etime,args"],10),
 "llm_models":models,
 "llm_inference":inference,
}
raw=json.dumps(receipt,ensure_ascii=False,indent=2)
local=OUT/"direct_receipt.json"
local.write_text(raw,encoding="utf-8")
# Publish directly through the authenticated GitHub CLI; no Bridge daemon required.
encoded=base64.b64encode(raw.encode("utf-8")).decode("ascii")
payload={"message":"diagnostic: publish direct Termux repair receipt","content":encoded,"branch":"bridge-results","committer":{"name":"Termux Direct Receipt","email":"termux-direct-receipt@users.noreply.github.com"}}
p=subprocess.run(["gh","api","repos/abolfazlabasi740-bot/options-report/contents/termux_direct_receipt_20261009.json","--method","PUT","--input","-"],cwd=str(ROOT),text=True,input=json.dumps(payload),capture_output=True,timeout=45)
if p.returncode:
    print("DIRECT_RECEIPT_LOCAL_ONLY")
    print("PUBLISH_EXIT_CODE="+str(p.returncode))
    print("PUBLISH_ERROR="+(p.stderr or p.stdout)[-2500:])
    print("LOCAL_RECEIPT="+str(local))
    raise SystemExit(2)
try:
    response=json.loads(p.stdout)
    sha=response.get("content",{}).get("sha","")
    commit=response.get("commit",{}).get("sha","")
except Exception:
    sha=""; commit=""
print("DIRECT_RECEIPT_PUBLISHED")
print("BRANCH=bridge-results")
print("FILE=termux_direct_receipt_20261009.json")
print("FILE_SHA="+sha)
print("COMMIT_SHA="+commit)
print("LOCAL_RECEIPT="+str(local))
print("LLM_MODELS_OK="+str("http_status" in models))
print("LLM_INFERENCE_OK="+str(bool(inference and "http_status" in inference)))
