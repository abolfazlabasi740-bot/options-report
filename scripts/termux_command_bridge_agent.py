#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib, json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

REPO = "abolfazlabasi740-bot/options-report"
PROJECT = Path.home() / "OptimusAI_V41_LIVE"
QUEUE_BRANCH = "bridge-commands"
RESULT_BRANCH = "bridge-results"
WORK = Path.home() / ".termux_command_bridge"
QUEUE = WORK / "queue"
RESULTS = WORK / "results"
POLL_SECONDS = int(os.environ.get("BRIDGE_POLL_SECONDS", "20"))
ALLOWED = {"python", "python3", "git", "bash", "sh", "printf", "pwd", "ls"}
BLOCKED_TOKENS = {"rm", "rmdir", "mkfs", "dd", "reboot", "shutdown", "su", "sudo", "curl", "wget", "nc", "ncat", "ssh", "scp", "chmod", "chown"}

def run(*args, cwd=None, check=True):
    return subprocess.run(list(args), cwd=str(cwd or PROJECT), text=True, capture_output=True, check=check)

def sync_branch(branch, dest):
    dest.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        run("git", "clone", "--branch", branch, f"https://github.com/{REPO}.git", str(dest), cwd=WORK)
    else:
        run("git", "fetch", "origin", branch, cwd=dest)
        run("git", "reset", "--hard", f"origin/{branch}", cwd=dest)

def validate_argv(argv):
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv): raise ValueError("argv must be a non-empty string list")
    if Path(argv[0]).name not in ALLOWED: raise ValueError(f"program not allowed: {argv[0]}")
    if any(x in argv for x in ["&&", "||", ";", "|", ">", ">>", "<", "$(", "BACKTICK"]): raise ValueError("shell operators are not allowed")
    if any(token in " ".join(argv).lower().split() for token in BLOCKED_TOKENS): raise ValueError("blocked command token")
    return argv

def publish_result(result):
    sync_branch(RESULT_BRANCH, RESULTS)
    path = RESULTS / f"{result['command_id']}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    run("git", "add", path.name, cwd=RESULTS)
    run("git", "commit", "-m", f"bridge: result {result['command_id']}", cwd=RESULTS, check=False)
    run("git", "push", "origin", RESULT_BRANCH, cwd=RESULTS)

def process_file(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    command_id = str(data["command_id"])
    argv = validate_argv(data["argv"])
    cwd = Path(data.get("cwd", str(PROJECT))).expanduser().resolve()
    project = PROJECT.resolve()
    if cwd != project and project not in cwd.parents: raise ValueError("cwd outside project is not allowed")
    started = datetime.now(timezone.utc).isoformat()
    proc = run(*argv, cwd=cwd, check=False)
    result = {"command_id": command_id, "status": "SUCCESS" if proc.returncode == 0 else "FAILED", "exit_code": proc.returncode, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(), "cwd": str(cwd), "argv": argv, "stdout": proc.stdout[-20000:], "stderr": proc.stderr[-20000:], "project_head": run("git", "rev-parse", "HEAD", cwd=PROJECT).stdout.strip()}
    result["result_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    publish_result(result)
    path.unlink()

def main():
    WORK.mkdir(parents=True, exist_ok=True); QUEUE.mkdir(exist_ok=True); RESULTS.mkdir(exist_ok=True)
    while True:
        try:
            sync_branch(QUEUE_BRANCH, QUEUE)
            for path in sorted(QUEUE.glob("*.json")):
                try: process_file(path)
                except Exception as exc:
                    publish_result({"command_id": path.stem, "status": "REJECTED", "error": str(exc), "finished_at": datetime.now(timezone.utc).isoformat()})
                    path.unlink(missing_ok=True)
        except Exception as exc: print(f"BRIDGE_LOOP_ERROR: {exc}", flush=True)
        time.sleep(POLL_SECONDS)

if __name__ == "__main__": main()
