#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resilient OptimusAI Termux Command Bridge."""
import base64
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = "abolfazlabasi740-bot/options-report"
PROJECT = Path.home() / "OptimusAI_V41_LIVE"
QUEUE_BRANCH = "bridge-commands"
RESULT_BRANCH = "bridge-results"
WORK = Path.home() / ".termux_command_bridge"
QUEUE_REPO = WORK / "queue"
QUEUE = QUEUE_REPO / QUEUE_BRANCH
POLL_SECONDS = int(os.environ.get("BRIDGE_POLL_SECONDS", "5"))
COMMAND_TIMEOUT_SECONDS = int(os.environ.get("BRIDGE_COMMAND_TIMEOUT_SECONDS", "120"))
GH_TIMEOUT_SECONDS = int(os.environ.get("BRIDGE_GH_TIMEOUT_SECONDS", "60"))
MAX_OUTPUT = 20000

ALLOWED = {"python", "python3", "git", "bash", "sh", "printf", "pwd", "ls"}
BLOCKED_TOKENS = {
    "rm", "rmdir", "mkfs", "dd", "reboot", "shutdown",
    "su", "sudo", "curl", "wget", "nc", "ncat", "ssh", "scp",
    "chmod", "chown"
}
BRIDGE_GIT_NAME = "Termux Command Bridge"
BRIDGE_GIT_EMAIL = "termux-command-bridge@users.noreply.github.com"
_LOCK_FD = None


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def log(message):
    print(message, flush=True)


def run(*args, cwd=None, check=True, timeout=None, input_text=None):
    return subprocess.run(
        list(args), cwd=str(cwd or PROJECT), text=True,
        input=input_text, capture_output=True, check=check, timeout=timeout
    )


def ensure_git_auth():
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("GitHub CLI is not installed")
    status = run(gh, "auth", "status", check=False, timeout=30)
    if status.returncode != 0:
        raise RuntimeError("GitHub CLI authentication failed: " +
                           (status.stderr.strip() or status.stdout.strip()))
    setup = run(gh, "auth", "setup-git", check=False, timeout=30)
    if setup.returncode != 0:
        raise RuntimeError("Git credential setup failed: " +
                           (setup.stderr.strip() or setup.stdout.strip()))


def gh_api(endpoint, method="GET", payload=None):
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("gh executable not found")
    args = [gh, "api", endpoint, "--method", method]
    input_text = None
    if payload is not None:
        args += ["--input", "-"]
        input_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    proc = run(*args, check=False, timeout=GH_TIMEOUT_SECONDS, input_text=input_text)
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh api {method} {endpoint} failed: " +
            (proc.stderr.strip() or proc.stdout.strip() or "unknown error")
        )
    if not proc.stdout.strip():
        return {}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"GitHub API returned invalid JSON: {exc}") from exc


def gh_get_file(path, branch):
    return gh_api(f"repos/{REPO}/contents/{path}?ref={branch}")


def gh_put_file(path, branch, content, message):
    existing = None
    try:
        existing = gh_get_file(path, branch)
    except Exception as exc:
        if "404" not in str(exc):
            raise
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
        "committer": {"name": BRIDGE_GIT_NAME, "email": BRIDGE_GIT_EMAIL},
    }
    if existing and existing.get("sha"):
        payload["sha"] = existing["sha"]
    return gh_api(f"repos/{REPO}/contents/{path}", "PUT", payload)


def gh_delete_file(path, branch, message):
    existing = gh_get_file(path, branch)
    sha = existing.get("sha")
    if not sha:
        raise RuntimeError(f"GitHub file SHA unavailable for {path}")
    payload = {
        "message": message, "sha": sha, "branch": branch,
        "committer": {"name": BRIDGE_GIT_NAME, "email": BRIDGE_GIT_EMAIL},
    }
    return gh_api(f"repos/{REPO}/contents/{path}", "DELETE", payload)


def sync_queue():
    # Read the queue directly from GitHub API. This avoids stale/misaligned
    # local queue clones and makes the bridge authoritative on QUEUE_BRANCH.
    QUEUE.mkdir(parents=True, exist_ok=True)
    remote = gh_api(f"repos/{REPO}/contents/?ref={QUEUE_BRANCH}")
    remote_names = set()
    for item in remote if isinstance(remote, list) else []:
        if item.get("type") != "file" or not item.get("name", "").endswith(".json"):
            continue
        name = item["name"]
        remote_names.add(name)
        raw = gh_api(f"repos/{REPO}/contents/{name}?ref={QUEUE_BRANCH}")
        encoded = raw.get("content", "")
        if not encoded:
            continue
        try:
            content = base64.b64decode(encoded.replace("\\n", "").encode("ascii")).decode("utf-8")
        except Exception as exc:
            raise RuntimeError(f"queue decode failed for {name}: {exc}")
        (QUEUE / name).write_text(content, encoding="utf-8")
    for local in QUEUE.glob("*.json"):
        if local.name not in remote_names:
            local.unlink(missing_ok=True)


def validate_argv(argv):
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise ValueError("argv must be a non-empty string list")
    if Path(argv[0]).name not in ALLOWED:
        raise ValueError(f"program not allowed: {argv[0]}")
    if any(op in " ".join(argv) for op in ("&&", "||", ";", "|", ">", ">>", "<", "$(", chr(96))):
        raise ValueError("shell operators are not allowed")
    if any(token in " ".join(argv).lower().split() for token in BLOCKED_TOKENS):
        raise ValueError("blocked command token")
    return argv


def safe_project_head():
    try:
        return run("git", "rev-parse", "HEAD", cwd=PROJECT, check=False).stdout.strip()
    except Exception:
        return ""


def publish_result(result):
    rel = f"{result['command_id']}.json"
    content = json.dumps(result, ensure_ascii=False, indent=2)
    last_error = None
    for attempt in range(1, 4):
        try:
            gh_put_file(rel, RESULT_BRANCH, content,
                        f"bridge: result {result['command_id']}")
            verify = gh_get_file(f"{RESULT_BRANCH}/{rel}", RESULT_BRANCH)
            if verify.get("sha"):
                log(f"BRIDGE_RESULT_PUBLISHED={result['command_id']}")
                return
            raise RuntimeError("result verification returned no sha")
        except Exception as exc:
            last_error = exc
            log(f"BRIDGE_RESULT_RETRY={result['command_id']} attempt={attempt}: {type(exc).__name__}: {exc}")
            if attempt < 3:
                time.sleep(2)
    raise RuntimeError(f"result publish failed: {last_error}")


def acknowledge_queue(path):
    # Queue JSON files live at the root of the bridge-commands branch.
    # path.relative_to(QUEUE_REPO) incorrectly prepends "bridge-commands/"
    # and causes every acknowledgement to 404, replaying old commands forever.
    rel = path.name
    last = None
    for attempt in range(1, 4):
        try:
            gh_delete_file(rel, QUEUE_BRANCH, f"bridge: acknowledge {path.stem}")
            log(f"BRIDGE_QUEUE_ACK={path.stem}")
            return
        except Exception as exc:
            last = exc
            log(f"BRIDGE_ACK_RETRY={path.stem} attempt={attempt}: {type(exc).__name__}: {exc}")
            if attempt < 3:
                time.sleep(2)
    raise RuntimeError(f"queue acknowledgement failed: {last}")


def build_invalid_result(path, error):
    raw = path.read_text(encoding="utf-8", errors="replace")
    result = {
        "command_id": path.stem,
        "status": "INVALID_COMMAND",
        "exit_code": 65,
        "started_at": utc_now(),
        "finished_at": utc_now(),
        "cwd": str(PROJECT),
        "argv": [],
        "stdout": "",
        "stderr": str(error),
        "timeout_seconds": COMMAND_TIMEOUT_SECONDS,
        "queue_path": path.relative_to(QUEUE_REPO).as_posix(),
        "project_head": safe_project_head(),
        "raw_queue_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }
    result["result_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return result


def process_file(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("queue item must be a JSON object")
        command_id = str(data["command_id"])
        argv = validate_argv(data["argv"])
        cwd = Path(data.get("cwd", str(PROJECT))).expanduser().resolve()
        project = PROJECT.resolve()
        if cwd != project and project not in cwd.parents:
            raise ValueError("cwd outside project is not allowed")
    except Exception as exc:
        result = build_invalid_result(path, f"{type(exc).__name__}: {exc}")
        publish_result(result)
        acknowledge_queue(path)
        return

    started = utc_now()
    log(f"BRIDGE_EXECUTE={command_id}")
    try:
        proc = run(*argv, cwd=cwd, check=False, timeout=COMMAND_TIMEOUT_SECONDS)
        status = "SUCCESS" if proc.returncode == 0 else "FAILED"
        exit_code = proc.returncode
        stdout = (proc.stdout or "")[-MAX_OUTPUT:]
        stderr = (proc.stderr or "")[-MAX_OUTPUT:]
    except subprocess.TimeoutExpired as exc:
        status = "TIMEOUT"
        exit_code = 124
        stdout = (exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes)
                  else (exc.stdout or ""))[-MAX_OUTPUT:]
        stderr = "command timeout\n" + (
            exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )[-MAX_OUTPUT:]
    except Exception as exc:
        status = "ERROR"
        exit_code = 1
        stdout = ""
        stderr = f"{type(exc).__name__}: {exc}"

    result = {
        "command_id": command_id,
        "status": status,
        "exit_code": exit_code,
        "started_at": started,
        "finished_at": utc_now(),
        "cwd": str(cwd),
        "argv": argv,
        "stdout": stdout,
        "stderr": stderr,
        "timeout_seconds": COMMAND_TIMEOUT_SECONDS,
        "queue_path": path.relative_to(QUEUE_REPO).as_posix(),
        "project_head": safe_project_head(),
    }
    result["result_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    # Result MUST be visible on GitHub before queue acknowledgement.
    publish_result(result)
    acknowledge_queue(path)


def _daemonize():
    if os.environ.get("BRIDGE_DAEMON_CHILD") == "1":
        return False
    WORK.mkdir(parents=True, exist_ok=True)
    log_path = WORK / "bridge_agent.log"
    env = os.environ.copy()
    env["BRIDGE_DAEMON_CHILD"] = "1"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n[{utc_now()}] BRIDGE_DAEMON_SPAWN\n")
        f.flush()
        subprocess.Popen([sys.executable, str(Path(__file__).resolve())],
                         cwd=str(PROJECT), stdin=subprocess.DEVNULL,
                         stdout=f, stderr=f, start_new_session=True,
                         env=env, close_fds=True)
    print("BRIDGE_DAEMON_STARTED", flush=True)
    print(f"BRIDGE_LOG={log_path}", flush=True)
    return True


def acquire_singleton():
    global _LOCK_FD
    WORK.mkdir(parents=True, exist_ok=True)
    _LOCK_FD = (WORK / "bridge_agent.lock").open("a+")
    try:
        fcntl.flock(_LOCK_FD.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("BRIDGE_ALREADY_RUNNING")
        return False
    _LOCK_FD.seek(0)
    _LOCK_FD.truncate()
    _LOCK_FD.write(str(os.getpid()))
    _LOCK_FD.flush()
    return True


def main():
    if _daemonize():
        return
    if not acquire_singleton():
        return

    QUEUE_REPO.mkdir(parents=True, exist_ok=True)
    log("BRIDGE_STATUS=STARTING")
    log(f"BRIDGE_PROJECT={PROJECT}")
    log(f"BRIDGE_QUEUE_REPO={QUEUE_REPO}")
    log(f"BRIDGE_QUEUE={QUEUE}")
    log(f"BRIDGE_RESULT_BRANCH={RESULT_BRANCH}")
    log(f"BRIDGE_POLL_SECONDS={POLL_SECONDS}")
    log(f"BRIDGE_COMMAND_TIMEOUT_SECONDS={COMMAND_TIMEOUT_SECONDS}")

    try:
        ensure_git_auth()
        log("BRIDGE_AUTH=OK")
    except Exception as exc:
        log(f"BRIDGE_FATAL_AUTH={type(exc).__name__}: {exc}")
        return

    log("BRIDGE_STATUS=READY")
    while True:
        try:
            log("BRIDGE_LOOP_TICK")
            sync_queue()
            log("BRIDGE_QUEUE_SYNCED")
            items = sorted(QUEUE.glob("*.json"))
            log(f"BRIDGE_QUEUE_ITEMS={len(items)}")
            for path in items:
                if not path.exists():
                    continue
                try:
                    log(f"BRIDGE_COMMAND_START={path.stem}")
                    process_file(path)
                    log(f"BRIDGE_COMMAND_DONE={path.stem}")
                except Exception as exc:
                    log(f"BRIDGE_COMMAND_ERROR={path.stem}: {type(exc).__name__}: {exc}")
        except Exception as exc:
            log(f"BRIDGE_LOOP_ERROR={type(exc).__name__}: {exc}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
