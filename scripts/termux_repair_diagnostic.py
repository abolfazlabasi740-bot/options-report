#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect non-secret live evidence for the autonomous Termux repair worker."""
import json, os, subprocess, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

root = Path.home() / "OptimusAI_V41_LIVE"
out = root / "output" / "termux_root_cause"
def read(path, limit=12000):
    p = Path(path)
    try:
        return p.read_text(encoding="utf-8", errors="replace")[-limit:]
    except Exception as e:
        return "UNAVAILABLE: " + type(e).__name__ + ": " + str(e)
def cmd(args, timeout=8):
    try:
        p = subprocess.run(args, cwd=str(root), text=True, capture_output=True, timeout=timeout)
        return {"rc":p.returncode,"stdout":p.stdout[-5000:],"stderr":p.stderr[-3000:]}
    except Exception as e:
        return {"error":type(e).__name__+": "+str(e)}
def http(path, payload=None, timeout=5):
    url="http://127.0.0.1:8080/v1/"+path
    try:
        data=json.dumps(payload).encode() if payload is not None else None
        req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json","Authorization":"Bearer local"})
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw=r.read(12000).decode("utf-8","replace")
            return {"http_status":r.status,"body":raw}
    except Exception as e:
        return {"error":type(e).__name__+": "+str(e)}
status_path=out/"repair_status.json"
report_path=out/"repair_report.json"
log_path=out/"repair_agent.log"
status_text=read(status_path,8000)
try: status=json.loads(status_text)
except Exception: status={"raw":status_text}
report_text=read(report_path,14000)
try: report=json.loads(report_text)
except Exception: report={"raw":report_text}
pid_text=read(out/"repair_agent.pid",1000).strip()
proc=cmd(["ps","-A","-o","pid,ppid,stat,etime,args"],10)
bridge_log=read(Path.home()/".termux_command_bridge"/"bridge_agent.log",14000)
models=http("models",timeout=4)
inference=None
if "http_status" in models:
    inference=http("chat/completions",{"model":os.environ.get("OPTIMUSAI_LLM_MODEL","Qwen/Qwen3-4B-GGUF:Q4_K_M"),"messages":[{"role":"user","content":"Reply with exactly: LLM_INFERENCE_OK"}],"max_tokens":16,"temperature":0},timeout=35)
result={
 "diagnostic":"OPTIMUSAI_TERMUX_REPAIR_DIAGNOSTIC",
 "collected_at":datetime.now(timezone.utc).isoformat(),
 "root_exists":root.exists(),
 "git_head":cmd(["git","rev-parse","HEAD"]),
 "git_status":cmd(["git","status","--short"]),
 "repair_pid_file":pid_text,
 "repair_status":status,
 "repair_report":report,
 "repair_log_tail":read(log_path,18000),
 "process_list":proc,
 "llm_models":models,
 "llm_inference":inference,
 "bridge_log_tail":bridge_log,
}
print(json.dumps(result,ensure_ascii=False,indent=2))
