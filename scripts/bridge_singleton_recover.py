#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hard reset and restart the single Termux Command Bridge daemon."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path.home() / "OptimusAI_V41_LIVE"
SCRIPT = PROJECT / "scripts" / "termux_command_bridge_agent.py"
WORK = Path.home() / ".termux_command_bridge"
ME = os.getpid()


def run(*args, check=False):
    return subprocess.run(list(args), cwd=str(PROJECT), text=True,
                          capture_output=True, check=check)


def main():
    pull = run("git", "fetch", "origin", "main")
    if pull.returncode != 0:
        print(pull.stdout[-4000:])
        print(pull.stderr[-4000:])
        raise SystemExit(pull.returncode)

    reset = run("git", "reset", "--hard", "origin/main")
    if reset.returncode != 0:
        print(reset.stdout[-4000:])
        print(reset.stderr[-4000:])
        raise SystemExit(reset.returncode)

    ps = subprocess.run(["ps", "-A", "-o", "pid=,args="],
                        text=True, capture_output=True)
    targets = []
    if ps.returncode == 0:
        for line in ps.stdout.splitlines():
            line = line.strip()
            if "termux_command_bridge_agent.py" not in line:
                continue
            try:
                pid = int(line.split(None, 1)[0])
            except Exception:
                continue
            if pid != ME:
                targets.append(pid)

    for pid in sorted(set(targets)):
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass

    time.sleep(2)

    WORK.mkdir(parents=True, exist_ok=True)
    log_path = WORK / "bridge_agent.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n[{time.strftime('%Y-%m-%dT%H:%M:%S%z')}] RECOVERY_RESTART\n")

    subprocess.Popen(
        [sys.executable, str(SCRIPT)],
        cwd=str(PROJECT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )

    time.sleep(4)
    print("BRIDGE_REBUILD_RESTARTED")
    print("BRIDGE_HEAD=" + run("git", "rev-parse", "HEAD").stdout.strip())
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        print("\n".join(lines[-60:]))


if __name__ == "__main__":
    main()
