#!/usr/bin/env python3
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path.home() / "OptimusAI_V41_LIVE"
SCRIPT = PROJECT / "scripts" / "termux_command_bridge_agent.py"
ME = os.getpid()

procs = subprocess.run(
    ["python", "-c",
     "import subprocess; print(subprocess.check_output(['ps','-A','-o','pid=,args='],text=True))"],
    text=True,
    capture_output=True,
)
targets = []
if procs.returncode == 0:
    for line in procs.stdout.splitlines():
        line = line.strip()
        if "termux_command_bridge_agent.py" in line and "bridge_singleton_recover.py" not in line:
            try:
                pid = int(line.split(None, 1)[0])
                if pid != ME:
                    targets.append(pid)
            except Exception:
                pass

for pid in sorted(set(targets)):
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except PermissionError:
        pass

time.sleep(1)

subprocess.Popen(
    [sys.executable, str(SCRIPT)],
    cwd=str(PROJECT),
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
    close_fds=True,
)

print("BRIDGE_SINGLETON_RECOVERED")
