#!/usr/bin/env python3
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path.home() / "OptimusAI_V41_LIVE"
SCRIPT = PROJECT / "scripts" / "termux_command_bridge_agent.py"
parent_pid = os.getppid()

pull = subprocess.run(
    ["git", "pull", "--ff-only", "origin", "main"],
    cwd=str(PROJECT),
    text=True,
    capture_output=True,
)
if pull.returncode != 0:
    print(pull.stdout[-4000:])
    print(pull.stderr[-4000:])
    raise SystemExit(pull.returncode)

subprocess.Popen(
    [sys.executable, str(SCRIPT)],
    cwd=str(PROJECT),
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
    close_fds=True,
)
time.sleep(1)
try:
    os.kill(parent_pid, signal.SIGTERM)
except ProcessLookupError:
    pass
print("BRIDGE_UPGRADE_SUCCESS")
