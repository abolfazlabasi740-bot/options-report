#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
import os
import shutil
import subprocess
import time
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
BLOCKED_TOKENS = {
    "rm", "rmdir", "mkfs", "dd", "reboot", "shutdown", "su", "sudo",
    "curl", "wget", "nc", "ncat", "ssh", "scp", "chmod", "chown"
}

BRIDGE_GIT_NAME = "Termux Command Bridge"
BRIDGE_GIT_EMAIL = "termux-command-bridge@users.noreply.github.com"


def run(*args, cwd=None, check=True):
    return subprocess.run(
        list(args),
        cwd=str(cwd or PROJECT),
        text=True,
        capture_output=True,
        check=check,
    )


def ensure_git_auth():
    """Use the user's existing GitHub CLI authentication for Git HTTPS."""
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("GitHub CLI 'gh' is not installed")
    status = run(gh, "auth", "status", check=False)
    if status.returncode != 0:
        raise RuntimeError(
            "GitHub CLI is not authenticated. Run 'gh auth login' once in Termux."
        )
    setup = run(gh, "auth", "setup-git", check=False)
    if setup.returncode != 0:
        raise RuntimeError(
            "GitHub Git credential setup failed: "
            + (setup.stderr.strip() or setup.stdout.strip())
        )


def ensure_commit_identity(repo_dir):
    """Set a repository-local identity so the bridge never depends on global Git config."""
    name = run(
        "git", "config", "user.name", BRIDGE_GIT_NAME,
        cwd=repo_dir, check=False
    )
    if name.returncode != 0:
        raise RuntimeError(
            "setting Git user.name failed: "
            + (name.stderr.strip() or name.stdout.strip())
        )

    email = run(
        "git", "config", "user.email", BRIDGE_GIT_EMAIL,
        cwd=repo_dir, check=False
    )
    if email.returncode != 0:
        raise RuntimeError(
            "setting Git user.email failed: "
            + (email.stderr.strip() or email.stdout.strip())
        )


def sync_branch(branch, dest):
    dest.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        run(
            "git", "clone", "--branch", branch,
            f"https://github.com/{REPO}.git", str(dest), cwd=WORK
        )
    else:
        run("git", "fetch", "origin", branch, cwd=dest)
        run("git", "reset", "--hard", f"origin/{branch}", cwd=dest)


def validate_argv(argv):
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(x, str) for x in argv)
    ):
        raise ValueError("argv must be a non-empty string list")
    if Path(argv[0]).name not in ALLOWED:
        raise ValueError(f"program not allowed: {argv[0]}")
    if any(
        x in argv
        for x in ["&&", "||", ";", "|", ">", ">>", "<", "$(", "BACKTICK"]
    ):
        raise ValueError("shell operators are not allowed")
    tokens = " ".join(argv).lower().split()
    if any(token in tokens for token in BLOCKED_TOKENS):
        raise ValueError("blocked command token")
    return argv


def publish_result(result):
    sync_branch(RESULT_BRANCH, RESULTS)
    ensure_commit_identity(RESULTS)

    path = RESULTS / f"{result['command_id']}.json"
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    run("git", "add", path.name, cwd=RESULTS)
    commit = run(
        "git", "commit", "-m",
        f"bridge: result {result['command_id']}",
        cwd=RESULTS,
        check=False,
    )
    if commit.returncode != 0:
        raise RuntimeError(
            "result commit failed: "
            + (commit.stderr.strip() or commit.stdout.strip())
        )

    push = run("git", "push", "origin", RESULT_BRANCH, cwd=RESULTS, check=False)
    if push.returncode != 0:
        raise RuntimeError(
            "result push failed: "
            + (push.stderr.strip() or push.stdout.strip())
        )


def process_file(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    command_id = str(data["command_id"])
    argv = validate_argv(data["argv"])
    cwd = Path(data.get("cwd", str(PROJECT))).expanduser().resolve()
    project = PROJECT.resolve()

    if cwd != project and project not in cwd.parents:
        raise ValueError("cwd outside project is not allowed")

    started = datetime.now(timezone.utc).isoformat()
    proc = run(*argv, cwd=cwd, check=False)

    result = {
        "command_id": command_id,
        "status": "SUCCESS" if proc.returncode == 0 else "FAILED",
        "exit_code": proc.returncode,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "cwd": str(cwd),
        "argv": argv,
        "stdout": proc.stdout[-20000:],
        "stderr": proc.stderr[-20000:],
        "project_head": run(
            "git", "rev-parse", "HEAD", cwd=PROJECT
        ).stdout.strip(),
    }

    result["result_sha256"] = hashlib.sha256(
        json.dumps(
            result, sort_keys=True, ensure_ascii=False
        ).encode()
    ).hexdigest()

    publish_result(result)
    path.unlink()


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    QUEUE.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)

    ensure_git_auth()
    print("BRIDGE_STATUS=READY", flush=True)
    print(f"BRIDGE_PROJECT={PROJECT}", flush=True)
    print(f"BRIDGE_POLL_SECONDS={POLL_SECONDS}", flush=True)

    while True:
        try:
            sync_branch(QUEUE_BRANCH, QUEUE)
            for path in sorted(QUEUE.glob("*.json")):
                try:
                    process_file(path)
                    print(
                        f"BRIDGE_COMMAND_DONE={path.stem}",
                        flush=True,
                    )
                except Exception as exc:
                    error_result = {
                        "command_id": path.stem,
                        "status": "REJECTED",
                        "error": str(exc),
                        "finished_at": datetime.now(timezone.utc).isoformat(),
                    }
                    publish_result(error_result)
                    path.unlink(missing_ok=True)
                    print(
                        f"BRIDGE_COMMAND_REJECTED={path.stem}",
                        flush=True,
                    )
        except Exception as exc:
            print(f"BRIDGE_LOOP_ERROR: {exc}", flush=True)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
