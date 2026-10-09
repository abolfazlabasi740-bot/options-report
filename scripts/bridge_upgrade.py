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

# Terminate the old bridge before acquiring its singleton lock in the new process.
# A detached delayed starter avoids racing the still-running parent lock.
starter = (
    "import subprocess,sys,time; "
    "time.sleep(3); "
    "subprocess.Popen([sys.executable, 'scripts/termux_command_bridge_agent.py'], "
    "cwd=" + repr(str(PROJECT)) + ", stdin=subprocess.DEVNULL, "
    "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, "
    "start_new_session=True, close_fds=True)"
)
subprocess.Popen(
    [sys.executable, "-c", starter],
    cwd=str(PROJECT),
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
    close_fds=True,
)
try:
    os.kill(parent_pid, signal.SIGTERM)
except ProcessLookupError:
    pass
print("BRIDGE_UPGRADE_SUCCESS")
