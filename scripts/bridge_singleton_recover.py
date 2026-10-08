#!/usr/bin/env python3
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

pull = subprocess.run(
    ["git", "pull", "--ff-only", "origin", "main"],
    cwd=str(PROJECT), text=True, capture_output=True
)
if pull.returncode != 0:
    print(pull.stdout[-4000:])
    print(pull.stderr[-4000:])
    raise SystemExit(pull.returncode)

procs = subprocess.run(
    ["ps", "-A", "-o", "pid=,args="],
    text=True, capture_output=True
)
targets = []
if procs.returncode == 0:
    for line in procs.stdout.splitlines():
        line = line.strip()
        if "termux_command_bridge_agent.py" in line:
            try:
                pid = int(line.split(None, 1)[0])
                if pid != ME:
                    targets.append(pid)
            except Exception:
                pass

for pid in sorted(set(targets)):
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass

time.sleep(1)

lock_path = WORK / "bridge_agent.lock"
try:
    lock_path.unlink()
except FileNotFoundError:
    pass

subprocess.Popen(
    [sys.executable, str(SCRIPT)],
    cwd=str(PROJECT),
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
    close_fds=True,
)

print("BRIDGE_RECOVERY_STARTED")
