#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Asynchronous local LLM bootstrap plus real agent tool-call verification."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("OPTIMUSAI_ROOT", Path.home() / "OptimusAI_V41_LIVE")).expanduser().resolve()
OUT = ROOT / "output" / "local_llm"
LOG = OUT / "recovery_worker.log"
STATUS = OUT / "recovery_status.json"
PID = OUT / "recovery_worker.pid"
API = os.environ.get("OPTIMUSAI_API_BASE", "http://127.0.0.1:8080/v1").rstrip("/")
MODEL = os.environ.get("OPTIMUSAI_LLM_MODEL", "Qwen/Qwen3-4B-GGUF:Q4_K_M")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(state: str, **extra) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"state": state, "updated_at": now(), "api_base": API, "model": MODEL, **extra}
    temp = STATUS.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATUS)
    print("LLM_RECOVERY_STATE=" + state, flush=True)


def api_ready() -> bool:
    try:
        import requests
        response = requests.get(API + "/models", timeout=8)
        return response.ok
    except Exception:
        return False


def worker() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as log:
        log.write(f"\n[{now()}] WORKER_START pid={os.getpid()}\n")
        log.flush()
        env = os.environ.copy()
        env.update({
            "OPTIMUSAI_ROOT": str(ROOT),
            "OPTIMUSAI_PROVIDER": "local",
            "OPTIMUSAI_API_BASE": API,
            "OPTIMUSAI_API_KEY": "local",
            "OPTIMUSAI_LLM_MODEL": MODEL,
            "OPTIMUSAI_HTTP_TIMEOUT": "300",
            "OPTIMUSAI_MAX_OUTPUT_TOKENS": "512",
            "OPTIMUSAI_MAX_TURNS": "5",
        })
        try:
            if not api_ready():
                write_status("BOOTSTRAPPING_SERVER", log=str(LOG))
                setup = subprocess.run(
                    ["bash", "scripts/setup_local_llm.sh"],
                    cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT,
                    text=True, check=False
                )
                log.write(f"\n[{now()}] SETUP_EXIT={setup.returncode}\n")
                log.flush()
                if setup.returncode != 0:
                    write_status("SETUP_FAILED", setup_exit=setup.returncode, log=str(LOG))
                    return setup.returncode
            if not api_ready():
                write_status("API_UNREACHABLE_AFTER_SETUP", log=str(LOG))
                return 20

            write_status("SERVER_READY_TESTING_INFERENCE", log=str(LOG))
            import requests
            response = requests.post(
                API + "/chat/completions",
                headers={"Authorization": "Bearer local", "Content-Type": "application/json"},
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a local inference smoke test. Reply with exactly LLM_READY."},
                        {"role": "user", "content": "Reply with exactly LLM_READY."}
                    ],
                    "temperature": 0,
                    "max_tokens": 16
                },
                timeout=300
            )
            response.raise_for_status()
            inference = response.json()
            answer = str(inference.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
            log.write(f"\n[{now()}] INFERENCE_HTTP={response.status_code} ANSWER={answer[:500]!r}\n")
            log.flush()
            if not answer:
                write_status("INFERENCE_EMPTY", inference_response=inference, log=str(LOG))
                return 21
            write_status("INFERENCE_OK_TESTING_AGENT_TOOLS", inference_answer=answer, log=str(LOG))

            task = (
                "Use the git_status tool to inspect the local repository, then use read_file "
                "to read lines 1 through 20 of docs/BASE_SHARE_OPPORTUNITY_SCORING_MODEL_V1.md. "
                "Do not write, edit, commit, or delete any file. After both real tool calls, "
                "report the tool results and any errors concisely."
            )
            agent = subprocess.run(
                ["bash", "scripts/run_local_agent.sh"],
                cwd=str(ROOT), env={**env, "OPTIMUSAI_TASK": task},
                stdout=log, stderr=subprocess.STDOUT, text=True, check=False,
                timeout=1200
            )
            log.write(f"\n[{now()}] AGENT_TOOL_TEST_EXIT={agent.returncode}\n")
            log.flush()
            tail = LOG.read_text(encoding="utf-8", errors="replace")[-12000:]
            if agent.returncode == 0 and "LLM_TOOL_CALL=git_status" in tail and "LLM_TOOL_CALL=read_file" in tail and tail.count("LLM_TOOL_RESULT=") >= 2:
                write_status("LLM_AND_AGENT_TOOL_CALLS_VERIFIED", agent_exit=agent.returncode, inference_answer=answer, log=str(LOG), evidence_tail=tail[-6000:])
                return 0
            write_status("AGENT_TOOL_TEST_FAILED", agent_exit=agent.returncode, inference_answer=answer, log=str(LOG), evidence_tail=tail[-6000:])
            return 22
        except subprocess.TimeoutExpired as exc:
            log.write(f"\n[{now()}] WORKER_TIMEOUT: {exc}\n")
            log.flush()
            write_status("WORKER_TIMEOUT", error=str(exc), log=str(LOG))
            return 124
        except Exception as exc:
            log.write(f"\n[{now()}] WORKER_ERROR={type(exc).__name__}: {exc}\n")
            log.flush()
            write_status("WORKER_ERROR", error=f"{type(exc).__name__}: {exc}", log=str(LOG))
            return 1


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        code = worker()
        PID.unlink(missing_ok=True)
        return code

    if PID.exists():
        try:
            old_pid = int(PID.read_text(encoding="utf-8").strip())
            os.kill(old_pid, 0)
            print(f"LLM_RECOVERY_ALREADY_RUNNING pid={old_pid}")
            return 0
        except (ValueError, ProcessLookupError, PermissionError):
            PID.unlink(missing_ok=True)

    write_status("WORKER_LAUNCHING", log=str(LOG))
    with LOG.open("a", encoding="utf-8") as log:
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
            cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, close_fds=True,
            env={**os.environ, "OPTIMUSAI_ROOT": str(ROOT)}
        )
    PID.write_text(str(child.pid), encoding="utf-8")
    print(f"LLM_RECOVERY_STARTED pid={child.pid}")
    print(f"LLM_RECOVERY_LOG={LOG}")
    print(f"LLM_RECOVERY_STATUS={STATUS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
