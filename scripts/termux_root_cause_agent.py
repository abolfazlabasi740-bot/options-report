#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only diagnostic agent for OptimusAI Termux bridge and local LLM."""
import json, os, platform, shutil, socket, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request

ROOT = Path(os.environ.get("OPTIMUSAI_ROOT", str(Path.home() / "OptimusAI_V41_LIVE"))).expanduser().resolve()
WORK = Path.home() / ".termux_command_bridge"
OUT = ROOT / "output" / "termux_root_cause"
API = os.environ.get("OPTIMUSAI_API_BASE", "http://127.0.0.1:8080/v1").rstrip("/")

def now():
    return datetime.now(timezone.utc).isoformat()

def run(args, timeout=10):
    try:
        p = subprocess.run(args, cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
        return {"exit_code": p.returncode, "stdout": (p.stdout or "")[-3500:], "stderr": (p.stderr or "")[-1200:]}
    except Exception as e:
        return {"error": type(e).__name__ + ": " + str(e)}

def tail(path, n=70):
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])[-3500:]
    except Exception as e:
        return "UNAVAILABLE: " + type(e).__name__ + ": " + str(e)

def port(port_num):
    s = socket.socket()
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", port_num))
        return True
    except Exception:
        return False
    finally:
        s.close()

def models():
    try:
        req = Request(API + "/models", headers={"Authorization": "Bearer local"})
        with urlopen(req, timeout=5) as r:
            j = json.loads(r.read(10000).decode("utf-8", "replace"))
            return {"reachable": True, "http_status": r.status, "models": [m.get("id") for m in j.get("data", []) if isinstance(m, dict)][:15]}
    except Exception as e:
        return {"reachable": False, "error": type(e).__name__ + ": " + str(e)}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = {}
    checks["project_exists"] = ROOT.is_dir()
    checks["python_version"] = sys.version
    checks["platform"] = platform.platform()
    checks["executables"] = {x: shutil.which(x) for x in ("python", "git", "gh", "bash", "termux-wake-lock")}
    checks["git_head"] = run(["git", "rev-parse", "HEAD"])
    checks["git_branch"] = run(["git", "branch", "--show-current"])
    checks["git_status"] = run(["git", "status", "--short"])
    checks["git_ahead_behind_origin_main"] = run(["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"])
    checks["git_remote_main"] = run(["git", "ls-remote", "--heads", "origin", "main"], timeout=20)
    checks["github_auth"] = run(["gh", "auth", "status"], timeout=15)
    checks["bridge_lock"] = {"exists": (WORK / "bridge_agent.lock").exists(), "text": tail(WORK / "bridge_agent.lock", 3)}
    checks["bridge_log_tail"] = tail(WORK / "bridge_agent.log", 100)
    checks["watchdog_installed"] = (Path.home() / ".termux/boot/optimusai_bridge_watchdog.sh").exists()
    checks["watchdog_log_tail"] = tail(WORK / "boot_watchdog.log", 35)
    ps = run(["ps", "-A", "-o", "pid,etime,args"], timeout=10)
    ps_text = ps.get("stdout", "")
    checks["relevant_processes"] = [line for line in ps_text.splitlines() if any(t in line.lower() for t in ("termux_command_bridge_agent", "llm_recovery_async", "llama-server", "llama.cpp"))][:40]
    checks["local_ports"] = {str(p): port(p) for p in (8080, 8000, 1234)}
    checks["llm_models_api"] = models()
    status_path = ROOT / "output/local_llm/recovery_status.json"
    try:
        checks["llm_recovery_status"] = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception as e:
        checks["llm_recovery_status"] = {"exists": status_path.exists(), "error": type(e).__name__ + ": " + str(e)}
    checks["llm_log_tail"] = tail(ROOT / "output/local_llm/recovery_worker.log", 80)
    checks["bridge_upgrade_log_tail"] = tail(ROOT / "output/local_llm/bridge_upgrade_finalize.log", 40)
    compile_checks = {}
    for rel in ("scripts/termux_command_bridge_agent.py", "scripts/bridge_upgrade.py", "scripts/llm_recovery_async.py", "scripts/llm_recovery_status.py", "agent/project_manager.py"):
        path = ROOT / rel
        compile_checks[rel] = run([sys.executable, "-m", "py_compile", str(path)]) if path.exists() else {"missing": True}
    checks["python_compile"] = compile_checks
    checks["local_queue_files"] = sorted(p.name for p in (WORK / "queue" / "bridge-commands").glob("*.json"))[:80]
    report_data = {"agent": "OPTIMUSAI_TERMUX_ROOT_CAUSE_AGENT", "version": "1.0", "started_finished_at": now(), "project": str(ROOT), "checks": checks}
    report = OUT / ("diagnostic_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    report.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ROOT_CAUSE_AGENT_FINISHED")
    print("REPORT=" + str(report))
    print(json.dumps(report_data, ensure_ascii=False, indent=2)[:17000])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
