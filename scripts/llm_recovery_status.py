#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print durable local LLM recovery status and the last log lines."""
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("OPTIMUSAI_ROOT", Path.home() / "OptimusAI_V41_LIVE")).expanduser().resolve()
OUT = ROOT / "output" / "local_llm"
STATUS = OUT / "recovery_status.json"
LOG = OUT / "recovery_worker.log"
PID = OUT / "recovery_worker.pid"

if not STATUS.exists():
    print(json.dumps({
        "state": "STATUS_NOT_CREATED",
        "project_root": str(ROOT),
        "status_file": str(STATUS),
        "log_file_exists": LOG.exists(),
        "worker_pid_file_exists": PID.exists(),
    }, ensure_ascii=False, indent=2))
    raise SystemExit(2)

try:
    data = json.loads(STATUS.read_text(encoding="utf-8"))
except Exception as exc:
    print(json.dumps({"state": "STATUS_READ_ERROR", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False, indent=2))
    raise SystemExit(3)

if PID.exists():
    try:
        data["worker_pid"] = int(PID.read_text(encoding="utf-8").strip())
    except Exception:
        data["worker_pid"] = "invalid"
else:
    data["worker_pid"] = None

if LOG.exists():
    data["log_tail"] = "\n".join(LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-100:])
print(json.dumps(data, ensure_ascii=False, indent=2))
