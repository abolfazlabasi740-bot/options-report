#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Termux/runtime verification evidence generator; never records secret values."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from audit_integrity import verify_audit

ROOT = Path(__file__).resolve().parent

CRITICAL_FILES = [
    "report_engine.py",
    "scoring_engine.py",
    "opportunity_engine.py",
    "tsetmc_adapter.py",
    "tsetmc_mapping.py",
    "canonical_snapshot.py",
    "historical_snapshot.py",
    "historical_pattern_shadow.py",
    "case_lifecycle_shadow.py",
    "replay_engine.py",
    "audit_integrity.py",
    "bale_listener.py",
]


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def _compile(files: list[str]) -> dict[str, str]:
    result = {}
    for name in files:
        path = ROOT / name
        if not path.exists():
            result[name] = "MISSING"
            continue
        try:
            subprocess.check_call(
                [sys.executable, "-m", "py_compile", str(path)],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            result[name] = "OK"
        except Exception:
            result[name] = "COMPILE_ERROR"
    return result


def main() -> None:
    env_presence = {
        "BALE_BOT_TOKEN": bool(os.getenv("BALE_BOT_TOKEN", "").strip()),
        "BALE_CHAT_ID": bool(os.getenv("BALE_CHAT_ID", "").strip()),
        "TSETMC_BASE_URL": bool(os.getenv("TSETMC_BASE_URL", "").strip()),
    }

    audit_path = ROOT / "output" / "latest_audit.json"
    audit_result = None
    if audit_path.exists():
        try:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            audit_result = verify_audit(audit)
        except Exception as exc:
            audit_result = {"status": "ERROR", "error": type(exc).__name__}

    compile_result = _compile(CRITICAL_FILES)
    missing_files = [name for name, status in compile_result.items() if status == "MISSING"]
    compile_failures = [name for name, status in compile_result.items() if status != "OK"]

    result = {
        "status": "PASS" if not missing_files and not compile_failures else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "python": sys.version,
        "platform": platform.platform(),
        "git_sha": _git_sha(),
        "critical_files": compile_result,
        "environment_presence_only": env_presence,
        "latest_audit_integrity": audit_result,
        "secrets_recorded": False,
    }

    out = ROOT / "output" / "runtime_verification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
