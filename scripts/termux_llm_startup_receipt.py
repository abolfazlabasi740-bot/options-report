#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect the missing local-LLM startup evidence and publish directly to bridge-results."""
import base64, json, os, subprocess, urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.home() / "OptimusAI_V41_LIVE"
OUT = ROOT / "output" / "termux_root_cause"
LLM = ROOT / "output" / "local_llm"
OUT.mkdir(parents=True, exist_ok=True)

def read(path, limit=10000):
    try:
        p = Path(path)
        return p.read_text(encoding="utf-8", errors="replace")[-limit:]
    except Exception as e:
        return "UNAVAILABLE: " + type(e).__name__ + ": " + str(e)

def cmd(args, timeout=10):
    try:
        p = subprocess.run(args, cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
        return {"exit_code": p.returncode, "stdout": p.stdout[-5000:], "stderr": p.stderr[-2000:]}
    except Exception as e:
        return {"error": type(e).__name__ + ": " + str(e)}

def http(path):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080" + path, timeout=4) as r:
            return {"status": r.status, "body": r.read(5000).decode("utf-8", "replace")}
    except Exception as e:
        return {"error": type(e).__name__ + ": " + str(e)}

pid_text = read(LLM / "llama-server.pid", 500).strip()
pid_state = cmd(["bash", "-lc", "p=" + (pid_text if pid_text.isdigit() else "0") + "; if [ \"$p\" -gt 0 ] && kill -0 \"$p\" 2>/dev/null; then echo PID_ALIVE; else echo PID_NOT_ALIVE; fi"])
cache_paths = [
    Path.home() / ".cache" / "llama.cpp",
    Path.home() / ".cache" / "huggingface",
    Path.home() / ".huggingface",
    Path.home() / "llama.cpp" / "models",
]
cache_info = []
for p in cache_paths:
    if p.exists():
        cache_info.append({"path": str(p), "du": cmd(["du", "-sh", str(p)], 20)})
    else:
        cache_info.append({"path": str(p), "exists": False})

receipt = {
    "receipt_type": "DIRECT_LOCAL_LLM_STARTUP_DIAGNOSTIC",
    "collected_at": datetime.now(timezone.utc).isoformat(),
    "project_head": cmd(["git", "rev-parse", "HEAD"]),
    "git_status": cmd(["git", "status", "--short"]),
    "repair_status": read(OUT / "repair_status.json", 3000),
    "repair_log_tail": read(OUT / "repair_agent.log", 9000),
    "llm_server_log_tail": read(LLM / "llama-server.log", 14000),
    "llm_models_json": read(LLM / "models.json", 4000),
    "llm_pid_file": pid_text,
    "llm_pid_state": pid_state,
    "llama_server_binary": cmd(["bash", "-lc", "test -x \"$HOME/llama.cpp/build/bin/llama-server\" && echo LLAMA_SERVER_BINARY_EXISTS || echo LLAMA_SERVER_BINARY_MISSING"]),
    "processes": cmd(["ps", "-A", "-o", "pid,ppid,stat,etime,args"]),
    "disk": cmd(["df", "-h", str(ROOT)]),
    "memory": cmd(["bash", "-lc", "grep -E 'MemTotal|MemAvailable' /proc/meminfo"]),
    "cache_info": cache_info,
    "health": http("/health"),
    "models": http("/v1/models"),
}
raw = json.dumps(receipt, ensure_ascii=False, indent=2)
local = OUT / "llm_startup_receipt.json"
local.write_text(raw, encoding="utf-8")
payload = {
    "message": "diagnostic: publish local LLM startup evidence",
    "content": base64.b64encode(raw.encode("utf-8")).decode("ascii"),
    "branch": "bridge-results",
    "committer": {"name": "Termux Direct Receipt", "email": "termux-direct-receipt@users.noreply.github.com"},
}
p = subprocess.run(
    ["gh", "api", "repos/abolfazlabasi740-bot/options-report/contents/termux_llm_startup_receipt_20261009.json", "--method", "PUT", "--input", "-"],
    cwd=str(ROOT), text=True, input=json.dumps(payload), capture_output=True, timeout=45,
)
if p.returncode:
    print("LLM_DIAGNOSTIC_LOCAL_ONLY")
    print("ERROR=" + (p.stderr or p.stdout)[-2500:])
    print("LOCAL_RECEIPT=" + str(local))
    raise SystemExit(2)
try:
    response = json.loads(p.stdout)
    print("LLM_DIAGNOSTIC_PUBLISHED")
    print("COMMIT_SHA=" + response.get("commit", {}).get("sha", ""))
    print("FILE_SHA=" + response.get("content", {}).get("sha", ""))
except Exception:
    print("LLM_DIAGNOSTIC_PUBLISHED")
print("FILE=termux_llm_startup_receipt_20261009.json")
print("LOCAL_RECEIPT=" + str(local))
print("HEALTH=" + json.dumps(receipt["health"], ensure_ascii=False))
print("MODELS=" + json.dumps(receipt["models"], ensure_ascii=False))
