#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "base_share"
OUT.mkdir(parents=True, exist_ok=True)
log = OUT / "async_run.log"
pid_file = OUT / "async_run.pid"

with log.open("a", encoding="utf-8") as fh:
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "base_share_opportunity_score_v1_report.py")],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=fh,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

pid_file.write_text(str(proc.pid), encoding="utf-8")
print("ASYNC_STARTED")
print("PID=", proc.pid)
print("LOG=", log)
