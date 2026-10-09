#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect detailed model-load failure evidence and publish it without the bridge."""
import base64, json, subprocess
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path.home() / "OptimusAI_V41_LIVE"
OUT = ROOT / "output" / "termux_root_cause"
LLM = ROOT / "output" / "local_llm"
OUT.mkdir(parents=True, exist_ok=True)

def run(args, timeout=20):
    try:
        p = subprocess.run(args, cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
        return {"exit_code": p.returncode, "stdout": p.stdout[-12000:], "stderr": p.stderr[-4000:]}
    except Exception as e:
        return {"error": type(e).__name__ + ": " + str(e)}

def read(path, limit=20000):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")[-limit:]
    except Exception as e:
        return "UNAVAILABLE: " + type(e).__name__ + ": " + str(e)

cache = Path.home() / ".cache" / "huggingface"
gguf = run(["bash", "-lc", "find \"$HOME/.cache/huggingface\" \"$HOME/.cache/llama.cpp\" \"$HOME/llama.cpp/models\" -type f \\( -iname '*.gguf' -o -iname '*Qwen3*' \\) -printf '%s %p\\n' 2>/dev/null | sort -nr | head -40"], 45)
log = read(LLM / "llama-server.log", 30000)
log_lines = log.splitlines()
log_tail = "\n".join(log_lines[-220:])
receipt = {
 "receipt_type": "DETAILED_MODEL_LOAD_FAILURE_DIAGNOSTIC",
 "collected_at": datetime.now(timezone.utc).isoformat(),
 "project_head": run(["git", "rev-parse", "HEAD"]),
 "git_status": run(["git", "status", "--short"]),
 "llama_server_log_last_220_lines": log_tail,
 "llama_server_log_line_count": len(log_lines),
 "llama_server_log_bytes": run(["wc", "-c", str(LLM / "llama-server.log")]),
 "llama_server_pid_file": read(LLM / "llama-server.pid", 1000),
 "llama_server_process": run(["bash", "-lc", "p=$(cat \"$HOME/OptimusAI_V41_LIVE/output/local_llm/llama-server.pid\" 2>/dev/null || true); if [ -n \"$p\" ] && kill -0 \"$p\" 2>/dev/null; then ps -p \"$p\" -o pid,ppid,stat,etime,rss,args; else echo PID_NOT_RUNNING; fi"]),
 "model_cache_files": gguf,
 "cache_size": run(["du", "-sh", str(cache)], 20),
 "disk": run(["df", "-h", str(ROOT)]),
 "memory": run(["bash", "-lc", "grep -E 'MemTotal|MemAvailable|SwapTotal|SwapFree' /proc/meminfo"]),
 "kernel_oom_evidence": run(["bash", "-lc", "logcat -d -t 250 2>&1 | grep -iE 'llama-server|lowmemorykiller|lmkd|out of memory|killed process|phantom' | tail -100"], 25),
 "llama_server_help_load_flags": run([str(Path.home() / "llama.cpp" / "build" / "bin" / "llama-server"), "--help"], 20),
}
raw = json.dumps(receipt, ensure_ascii=False, indent=2)
local = OUT / "model_load_failure_diagnostic.json"
local.write_text(raw, encoding="utf-8")
payload = {
 "message": "diagnostic: capture detailed llama-server load failure",
 "content": base64.b64encode(raw.encode("utf-8")).decode("ascii"),
 "branch": "bridge-results",
 "committer": {"name": "Termux Direct Receipt", "email": "termux-direct-receipt@users.noreply.github.com"}
}
p = subprocess.run(["gh", "api", "repos/abolfazlabasi740-bot/options-report/contents/termux_model_load_diagnostic_20261009.json", "--method", "PUT", "--input", "-"], cwd=str(ROOT), text=True, input=json.dumps(payload), capture_output=True, timeout=45)
if p.returncode:
 print("MODEL_DIAGNOSTIC_LOCAL_ONLY")
 print("PUBLISH_ERROR=" + (p.stderr or p.stdout)[-2000:])
 print("LOCAL_RECEIPT=" + str(local))
 raise SystemExit(2)
try:
 r = json.loads(p.stdout)
 print("MODEL_DIAGNOSTIC_PUBLISHED")
 print("COMMIT_SHA=" + r.get("commit", {}).get("sha", ""))
 print("FILE_SHA=" + r.get("content", {}).get("sha", ""))
except Exception:
 print("MODEL_DIAGNOSTIC_PUBLISHED")
print("FILE=termux_model_load_diagnostic_20261009.json")
print("LOCAL_RECEIPT=" + str(local))
print("LOG_LINES=" + str(len(log_lines)))
print("GGUF_SEARCH_EXIT=" + str(gguf.get("exit_code", "unknown")))
