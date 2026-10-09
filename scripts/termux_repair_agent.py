#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launch a bounded autonomous Termux repair agent and persist its evidence."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("OPTIMUSAI_ROOT", str(Path.home() / "OptimusAI_V41_LIVE"))).expanduser().resolve()
OUT = ROOT / "output" / "termux_root_cause"
STATUS = OUT / "repair_status.json"
LOG = OUT / "repair_agent.log"
PID = OUT / "repair_agent.pid"

TASK = r"""
You are the on-device senior repair engineer for this OptimusAI Termux installation. This is an EXECUTE-AND-FIX task, not a report-only task.

MISSION: Find and fix the actual reason the Termux bridge/LLM/agent chain is unreliable. Do not wait for a GitHub receipt as a substitute for diagnosis. Use the local filesystem and commands to inspect evidence, make minimal durable fixes, and verify them.

Mandatory sequence:
1. Inspect git_status, then read relevant files before changing anything: scripts/termux_command_bridge_agent.py, scripts/bridge_upgrade.py, scripts/llm_recovery_async.py, scripts/llm_recovery_status.py, scripts/run_local_agent.sh, scripts/setup_local_llm.sh, agent/project_manager.py, and any watchdog/diagnostic scripts present.
2. Inspect output/termux_root_cause and output/local_llm reports/logs, ~/.termux_command_bridge/bridge_agent.log, queue state, process list, gh auth status, git status, git log -5 --oneline, and whether local main is behind/ahead of origin/main. Never print credentials, tokens, or environment secrets.
3. Diagnose the complete failure path: bridge daemon/liveness, singleton lock and stale PID, GitHub auth/API, queue fetch/decode/order, command execution, receipt publication verification, queue acknowledgement/deletion, command timeout, restart handoff, LLM server startup and API readiness, actual inference, tool-call parsing/execution, and agent retry/turn limits.
4. Apply real fixes for causes found. Do not just create another diagnostic file or only summarize. Preserve uncommitted user work; do not use destructive commands, hard resets, force pushes, or blanket git add of unrelated files. Keep edits scoped to this repair. Prefer complete file replacements for changed scripts.
5. If bridge is absent, start it using python scripts/termux_command_bridge_agent.py. If local LLM is down, inspect setup_local_llm.sh and attempt the documented startup; do not install packages or download large models without confirming they are already intended by project setup. If the model server cannot start, capture the exact reason and continue repairing independent bridge issues.
6. Test Python compilation for every changed Python file. Test local /v1/models and one short /v1/chat/completions inference when server is up. Run the agent with a task that requires at least two genuine function calls (git_status and read_file) and verify corresponding tool-call and tool-result logs. Test queue/receipt code paths without deleting user data. If feasible, enqueue a unique harmless self-check through the existing bridge and verify receipt publication and queue acknowledgement.
7. Inspect git diff and status. Commit only repair files intentionally changed, using a specific message. Do not commit unrelated user work.
8. Write a final structured report to output/termux_root_cause/repair_report.json and update output/termux_root_cause/repair_status.json. Include root causes with evidence, files changed, tests and exact outcomes, remaining blockers, and whether the end-to-end chain actually passed. Keep a readable log in output/termux_root_cause/repair_agent.log.
9. Do not claim a test passed unless its command/output proves it. Do not endlessly retry: at most two attempts per failing stage, then record the blocker and continue to other independent fixes.
10. Finish with a concise Persian summary. The goal is to repair the system, not to wait for ChatGPT to poll receipts. If the LLM itself is unusable, make safe deterministic fixes possible and clearly state what still requires a working model.
"""

def now():
    return datetime.now(timezone.utc).isoformat()

def write_status(state, **extra):
    OUT.mkdir(parents=True, exist_ok=True)
    data = {"state": state, "updated_at": now(), "project": str(ROOT), **extra}
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATUS)

def worker():
    OUT.mkdir(parents=True, exist_ok=True)
    write_status("REPAIR_AGENT_RUNNING", log=str(LOG), task="autonomous root-cause repair")
    with LOG.open("a", encoding="utf-8") as log:
        log.write("\n[" + now() + "] REPAIR_WORKER_START pid=" + str(os.getpid()) + "\n")
        log.flush()
        env = os.environ.copy()
        env.update({
            "OPTIMUSAI_ROOT": str(ROOT),
            "OPTIMUSAI_PROVIDER": "local",
            "OPTIMUSAI_API_BASE": os.environ.get("OPTIMUSAI_API_BASE", "http://127.0.0.1:8080/v1"),
            "OPTIMUSAI_API_KEY": "local",
            "OPTIMUSAI_LLM_MODEL": os.environ.get("OPTIMUSAI_LLM_MODEL", "Qwen/Qwen3-4B-GGUF:Q4_K_M"),
            "OPTIMUSAI_HTTP_TIMEOUT": "240",
            "OPTIMUSAI_MAX_OUTPUT_TOKENS": "1200",
            "OPTIMUSAI_MAX_TURNS": "12",
        })
        try:
            ready = subprocess.run(
                [sys.executable, "-c",
                 "import urllib.request; urllib.request.urlopen('" + env["OPTIMUSAI_API_BASE"] + "/models', timeout=4).read(100)"],
                cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT, timeout=8
            )
            if ready.returncode != 0:
                log.write("\n[" + now() + "] LLM_NOT_READY; attempting configured setup once\n")
                log.flush()
                setup = subprocess.run(
                    ["bash", "scripts/setup_local_llm.sh"], cwd=str(ROOT), env=env,
                    stdout=log, stderr=subprocess.STDOUT, timeout=900
                )
                log.write("\n[" + now() + "] LLM_SETUP_EXIT=" + str(setup.returncode) + "\n")
                log.flush()
            task_env = dict(env)
            task_env["OPTIMUSAI_TASK"] = TASK
            log.write("\n[" + now() + "] STARTING_AUTONOMOUS_AGENT\n")
            log.flush()
            agent = subprocess.run(
                ["bash", "scripts/run_local_agent.sh"], cwd=str(ROOT), env=task_env,
                stdout=log, stderr=subprocess.STDOUT, timeout=5400
            )
            log.write("\n[" + now() + "] AUTONOMOUS_AGENT_EXIT=" + str(agent.returncode) + "\n")
            log.flush()
            state = "REPAIR_AGENT_FINISHED" if agent.returncode == 0 else "REPAIR_AGENT_BLOCKED"
            write_status(state, agent_exit=agent.returncode, log=str(LOG), report=str(OUT / "repair_report.json"))
        except subprocess.TimeoutExpired as exc:
            log.write("\n[" + now() + "] REPAIR_STAGE_TIMEOUT=" + str(exc) + "\n")
            log.flush()
            write_status("REPAIR_AGENT_TIMEOUT", error=str(exc), log=str(LOG))
        except Exception as exc:
            log.write("\n[" + now() + "] REPAIR_AGENT_EXCEPTION=" + type(exc).__name__ + ": " + str(exc) + "\n")
            log.flush()
            write_status("REPAIR_AGENT_ERROR", error=type(exc).__name__ + ": " + str(exc), log=str(LOG))
        finally:
            PID.unlink(missing_ok=True)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        worker()
        return 0
    if PID.exists():
        try:
            old = int(PID.read_text(encoding="utf-8").strip())
            os.kill(old, 0)
            print("REPAIR_AGENT_ALREADY_RUNNING pid=" + str(old))
            return 0
        except Exception:
            PID.unlink(missing_ok=True)
    with LOG.open("a", encoding="utf-8") as log:
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
            cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, close_fds=True, env={**os.environ, "OPTIMUSAI_ROOT": str(ROOT)}
        )
    PID.write_text(str(child.pid), encoding="utf-8")
    write_status("REPAIR_AGENT_LAUNCHED", pid=child.pid, log=str(LOG))
    print("REPAIR_AGENT_LAUNCHED pid=" + str(child.pid))
    print("REPAIR_AGENT_LOG=" + str(LOG))
    print("REPAIR_AGENT_STATUS=" + str(STATUS))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
