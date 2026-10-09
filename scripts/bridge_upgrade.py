#!/usr/bin/env python3
"""Safely update and restart the local Termux bridge without discarding local work."""
from __future__ import annotations

import base64
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path.home() / "OptimusAI_V41_LIVE"
SCRIPT = PROJECT / "scripts" / "termux_command_bridge_agent.py"
REPO = "abolfazlabasi740-bot/options-report"
QUEUE_BRANCH = "bridge-commands"
RESULT_BRANCH = "bridge-results"


def gh_api(endpoint: str, method: str = "GET", payload: dict | None = None):
    args = ["gh", "api", endpoint, "--method", method]
    input_text = None
    if payload is not None:
        args += ["--input", "-"]
        input_text = json.dumps(payload, separators=(",", ":"))
    proc = subprocess.run(args, cwd=str(PROJECT), text=True, input=input_text,
                          capture_output=True, timeout=30)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def finalize(parent_pid: int) -> int:
    """Wait until this command has a published receipt, then remove it and restart."""
    deadline = time.time() + 180
    own_name = None
    while time.time() < deadline:
        try:
            items = gh_api(f"repos/{REPO}/contents/?ref={QUEUE_BRANCH}")
            for item in items if isinstance(items, list) else []:
                name = item.get("name", "")
                if not name.endswith(".json"):
                    continue
                raw = gh_api(f"repos/{REPO}/contents/{name}?ref={QUEUE_BRANCH}")
                encoded = raw.get("content", "")
                if not encoded:
                    continue
                payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
                argv = payload.get("argv", [])
                if isinstance(argv, list) and "scripts/bridge_upgrade.py" in argv:
                    candidate_name = name
                    command_id = str(payload.get("command_id", Path(name).stem))
                    try:
                        receipt = gh_api(
                            f"repos/{REPO}/contents/{command_id}.json?ref={RESULT_BRANCH}"
                        )
                        encoded_result = receipt.get("content", "")
                        if encoded_result:
                            result = json.loads(base64.b64decode(encoded_result).decode("utf-8"))
                            if result.get("status") not in {"SUCCESS", "FAILED", "ERROR", "TIMEOUT"}:
                                raise RuntimeError("receipt has no terminal status")
                            sha = raw.get("sha")
                            if sha:
                                gh_api(
                                    f"repos/{REPO}/contents/{candidate_name}",
                                    "DELETE",
                                    {"message": f"bridge: acknowledge {command_id} after receipt",
                                     "sha": sha, "branch": QUEUE_BRANCH}
                                )
                                own_name = candidate_name
                                print(f"BRIDGE_UPGRADE_QUEUE_ACK={command_id}", flush=True)
                            break
                    except Exception:
                        pass
        except Exception:
            pass
        if own_name:
            try:
                os.kill(parent_pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            time.sleep(3)
            subprocess.Popen(
                [sys.executable, str(SCRIPT)], cwd=str(PROJECT),
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True
            )
            print("BRIDGE_RESTARTED_WITH_UPDATED_CODE", flush=True)
            return 0
        time.sleep(2)
    print("BRIDGE_UPGRADE_FINALIZE_TIMEOUT", flush=True)
    return 124


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--finalize":
        if len(sys.argv) < 3:
            return 64
        return finalize(int(sys.argv[2]))

    parent_pid = os.getppid()
    pull = subprocess.run(
        ["git", "pull", "--ff-only", "origin", "main"],
        cwd=str(PROJECT), text=True, capture_output=True, timeout=120
    )
    if pull.returncode:
        print(pull.stdout[-4000:])
        print(pull.stderr[-4000:])
        return pull.returncode

    log_dir = PROJECT / "output" / "local_llm"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = (log_dir / "bridge_upgrade_finalize.log").open("a", encoding="utf-8")
    child = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--finalize", str(parent_pid)],
        cwd=str(PROJECT), stdin=subprocess.DEVNULL, stdout=log_file,
        stderr=subprocess.STDOUT, start_new_session=True, close_fds=True
    )
    print("BRIDGE_UPGRADE_SCHEDULED")
    print(f"FINALIZER_PID={child.pid}")
    print(pull.stdout[-2000:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
