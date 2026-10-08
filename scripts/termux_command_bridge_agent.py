#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
RESULTS = WORK / "results"
POLL_SECONDS = int(os.environ.get("BRIDGE_POLL_SECONDS", "5"))
COMMAND_TIMEOUT_SECONDS = int(os.environ.get("BRIDGE_COMMAND_TIMEOUT_SECONDS", "120"))

ALLOWED = {"python", "python3", "git", "bash", "sh", "printf", "pwd", "ls"}
BLOCKED_TOKENS = {
    "r" + "m", "rmdir", "mkfs", "dd", "reboot", "shutdown",
    "su", "sudo", "curl", "wget", "nc", "ncat", "ssh", "scp",
    "ch" + "mod", "ch" + "own"
}
BRIDGE_GIT_NAME = "Termux Command Bridge"
BRIDGE_GIT_EMAIL = "termux-command-bridge@users.noreply.github.com"

def run(*args, cwd=None, check=True, timeout=None):
    return subprocess.run(list(args), cwd=str(cwd or PROJECT),
                          text=True, capture_output=True,
                          check=check, timeout=timeout)

def log(message):
    print(message, flush=True)

def ensure_git_auth():
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("GitHub CLI is not installed")
    status = run(gh, "auth", "status", check=False)
    if status.returncode != 0:
        raise RuntimeError("GitHub CLI authentication failed")
    setup = run(gh, "auth", "setup-git", check=False)
    if setup.returncode != 0:
        raise RuntimeError("Git credential setup failed: " +
                           (setup.stderr.strip() or setup.stdout.strip()))

def ensure_commit_identity(repo_dir):
    for key, value in (("user.name", BRIDGE_GIT_NAME),
                        ("user.email", BRIDGE_GIT_EMAIL)):
        result = run("git", "config", key, value, cwd=repo_dir, check=False)
        if result.returncode != 0:
            raise RuntimeError("Git identity setup failed")

def sync_branch(branch, dest):
    dest.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        run("git", "clone", "--branch", branch,
            f"https://github.com/{REPO}.git", str(dest),
            cwd=WORK, timeout=90)
        return
    run("git", "fetch", "--prune", "origin", branch,
        cwd=dest, timeout=90)
    run("git", "reset", "--hard", f"origin/{branch}",
        cwd=dest, timeout=30)
    run("git", "clean", "-fd", cwd=dest, timeout=30)

def validate_argv(argv):
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise ValueError("argv must be a non-empty string list")
    if Path(argv[0]).name not in ALLOWED:
        raise ValueError(f"program not allowed: {argv[0]}")
    if any(x in argv for x in ["&&", "||", ";", "|", ">", ">>", "<", "$(", "BACKTICK"]):
        raise ValueError("shell operators are not allowed")
    tokens = " ".join(argv).lower().split()
    if any(token in tokens for token in BLOCKED_TOKENS):
        raise ValueError("blocked command token")
    return argv

def publish_result(result):
    sync_branch(RESULT_BRANCH, RESULTS)
    ensure_commit_identity(RESULTS)
    rel = f"{result['command_id']}.json"
    path = RESULTS / rel
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    run("git", "add", "--", rel, cwd=RESULTS)
    commit = run("git", "commit", "-m",
                 f"bridge: result {result['command_id']}",
                 cwd=RESULTS, check=False)
    if commit.returncode != 0:
        raise RuntimeError("result commit failed")
    last = "unknown"
    for attempt in range(4):
        push = run("git", "push", "--atomic", "origin",
                   f"{RESULT_BRANCH}:{RESULT_BRANCH}",
                   cwd=RESULTS, check=False, timeout=90)
        if push.returncode == 0:
            verify = run("git", "fetch", "origin", RESULT_BRANCH,
                         cwd=RESULTS, check=False, timeout=90)
            if verify.returncode == 0:
                tree = run("git", "ls-tree", "-r", "--name-only",
                           f"origin/{RESULT_BRANCH}", "--", rel,
                           cwd=RESULTS, check=False, timeout=30)
                if tree.returncode == 0 and rel in tree.stdout.splitlines():
                    return
            last = "remote verification failed"
        else:
            last = push.stderr.strip() or push.stdout.strip() or "push failed"
        if attempt < 3:
            sync_branch(RESULT_BRANCH, RESULTS)
            ensure_commit_identity(RESULTS)
            path = RESULTS / rel
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            run("git", "add", "--", rel, cwd=RESULTS)
            retry = run("git", "commit", "-m",
                        f"bridge: result {result['command_id']}",
                        cwd=RESULTS, check=False)
            if retry.returncode != 0:
                last = retry.stderr.strip() or retry.stdout.strip() or "retry commit failed"
    raise RuntimeError("result publish failed: " + last)

def consume_queue_item(path):
    if not path.exists():
        return
    rel = path.relative_to(QUEUE_REPO).as_posix()
    ensure_commit_identity(QUEUE_REPO)
    path.unlink()
    run("git", "add", "-u", "--", rel, cwd=QUEUE_REPO)
    commit = run("git", "commit", "-m",
                 f"bridge: consume {path.stem}",
                 cwd=QUEUE_REPO, check=False)
    if commit.returncode != 0:
        raise RuntimeError("queue consume commit failed")
    last = "push failed"
    for attempt in range(4):
        push = run("git", "push", "--atomic", "origin",
                   f"{QUEUE_BRANCH}:{QUEUE_BRANCH}",
                   cwd=QUEUE_REPO, check=False, timeout=90)
        if push.returncode == 0:
            return
        last = push.stderr.strip() or push.stdout.strip() or last
        if attempt < 3:
            sync_branch(QUEUE_BRANCH, QUEUE_REPO)
            if not path.exists():
                return
            ensure_commit_identity(QUEUE_REPO)
            path.unlink()
            run("git", "add", "-u", "--", rel, cwd=QUEUE_REPO)
            retry = run("git", "commit", "-m",
                        f"bridge: consume {path.stem}",
                        cwd=QUEUE_REPO, check=False)
            if retry.returncode != 0:
                last = retry.stderr.strip() or retry.stdout.strip() or "retry commit failed"
    raise RuntimeError("queue consume failed: " + last)

def process_file(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    command_id = str(data["command_id"])
    argv = validate_argv(data["argv"])
    cwd = Path(data.get("cwd", str(PROJECT))).expanduser().resolve()
    project = PROJECT.resolve()
    if cwd != project and project not in cwd.parents:
        raise ValueError("cwd outside project is not allowed")
    started = datetime.now(timezone.utc).isoformat()
    try:
        proc = run(*argv, cwd=cwd, check=False, timeout=COMMAND_TIMEOUT_SECONDS)
        status = "SUCCESS" if proc.returncode == 0 else "FAILED"
        exit_code = proc.returncode
        stdout = proc.stdout[-20000:]
        stderr = proc.stderr[-20000:]
    except subprocess.TimeoutExpired as exc:
        status = "TIMEOUT"
        exit_code = 124
        stdout = exc.stdout[-20000:] if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr[-20000:] if isinstance(exc.stderr, str) else "command timeout"
    result = {
        "command_id": command_id,
        "status": status,
        "exit_code": exit_code,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "cwd": str(cwd),
        "argv": argv,
        "stdout": stdout,
        "stderr": stderr,
        "timeout_seconds": COMMAND_TIMEOUT_SECONDS,
        "queue_path": path.relative_to(QUEUE_REPO).as_posix(),
        "project_head": run("git", "rev-parse", "HEAD", cwd=PROJECT).stdout.strip(),
    }
    result["result_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    publish_result(result)
    consume_queue_item(path)

def _daemonize():
    if os.environ.get("BRIDGE_DAEMON_CHILD") == "1":
        return False
    WORK.mkdir(parents=True, exist_ok=True)
    log_path = WORK / "bridge_agent.log"
    env = os.environ.copy()
    env["BRIDGE_DAEMON_CHILD"] = "1"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now(timezone.utc).isoformat()}] BRIDGE_DAEMON_SPAWN\n")
        f.flush()
        subprocess.Popen([sys.executable, str(Path(__file__).resolve())],
                         cwd=str(PROJECT), stdin=subprocess.DEVNULL,
                         stdout=f, stderr=f, start_new_session=True,
                         env=env, close_fds=True)
    print("BRIDGE_DAEMON_STARTED", flush=True)
    print(f"BRIDGE_LOG={log_path}", flush=True)
    return True

def main():
    if _daemonize():
        return
    WORK.mkdir(parents=True, exist_ok=True)
    QUEUE_REPO.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    log("BRIDGE_STATUS=STARTING")
    log(f"BRIDGE_PROJECT={PROJECT}")
    log(f"BRIDGE_QUEUE_REPO={QUEUE_REPO}")
    log(f"BRIDGE_QUEUE={QUEUE}")
    log(f"BRIDGE_RESULTS={RESULTS}")
    log(f"BRIDGE_POLL_SECONDS={POLL_SECONDS}")
    try:
        ensure_git_auth()
        log("BRIDGE_AUTH=OK")
    except Exception as exc:
        log(f"BRIDGE_FATAL_AUTH={type(exc).__name__}: {exc}")
        raise
    log("BRIDGE_STATUS=READY")
    while True:
        try:
            log("BRIDGE_LOOP_TICK")
            sync_branch(QUEUE_BRANCH, QUEUE_REPO)
            log("BRIDGE_QUEUE_SYNCED")
            for path in sorted(QUEUE.glob("*.json")):
                try:
                    log(f"BRIDGE_COMMAND_START={path.stem}")
                    process_file(path)
                    log(f"BRIDGE_COMMAND_DONE={path.stem}")
                except Exception as exc:
                    log(f"BRIDGE_COMMAND_ERROR={path.stem}: {type(exc).__name__}: {exc}")
        except Exception as exc:
            log(f"BRIDGE_LOOP_ERROR: {type(exc).__name__}: {exc}")
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
