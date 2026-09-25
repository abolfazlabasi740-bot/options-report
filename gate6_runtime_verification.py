#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end Gate 6 runner for the deployed Termux runtime.

This script intentionally orchestrates the existing production components:
Report Engine -> Runtime Verification -> Bale Delivery Verification.
It does not implement a second analysis engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
AUDIT = OUTPUT / "latest_audit.json"
REPORT = OUTPUT / "latest_report.txt"
BALE_EVIDENCE = OUTPUT / "bale_delivery_verification.json"
RUNTIME_EVIDENCE = OUTPUT / "runtime_verification.json"
GATE6_EVIDENCE = OUTPUT / "gate6_runtime_evidence.json"


def run_step(name: str, argv: list[str]) -> None:
    result = subprocess.run(
        argv,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if len(detail) > 1200:
            detail = detail[-1200:]
        raise RuntimeError(
            f"{name} failed with exit code {result.returncode}"
            + (f": {detail}" if detail else "")
        )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def main() -> None:
    started = datetime.now(timezone.utc).isoformat()

    run_step("REPORT_ENGINE", [sys.executable, "report_engine.py"])
    run_step("RUNTIME_VERIFICATION", [sys.executable, "runtime_verification.py"])
    run_step("BALE_DELIVERY_VERIFICATION", [sys.executable, "bale_runtime_verification.py"])

    if not AUDIT.exists() or not REPORT.exists() or not RUNTIME_EVIDENCE.exists() or not BALE_EVIDENCE.exists():
        raise RuntimeError("Gate 6 evidence artifacts are incomplete")

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME_EVIDENCE.read_text(encoding="utf-8"))
    bale = json.loads(BALE_EVIDENCE.read_text(encoding="utf-8"))

    runtime_git_sha = runtime.get("git_sha")
    repository_git_sha = current_git_sha()
    if runtime.get("status") != "PASS":
        raise RuntimeError("runtime_verification.json is not PASS")
    if not runtime_git_sha or not repository_git_sha or runtime_git_sha != repository_git_sha:
        raise RuntimeError("Runtime Git SHA does not match deployed repository HEAD")
    if (audit.get("audit_integrity") or {}).get("status") != "PASS":
        raise RuntimeError("latest_audit.json is not PASS")
    if audit.get("source_of_truth") == "TSETMC":
        if audit.get("data_mode") not in {"LIVE_TSETMC_REFRESH", "LAST_KNOWN_TSETMC_SNAPSHOT"}:
            raise RuntimeError("TSETMC data mode is invalid")
        if audit.get("live_movement_claim") != "NOT_CLAIMED":
            raise RuntimeError("TSETMC live movement claim must remain NOT_CLAIMED")
    if bale.get("status") != "SUCCESS":
        raise RuntimeError("Bale delivery verification is not SUCCESS")
    if bale.get("report_sha256") != sha256_file(REPORT):
        raise RuntimeError("Report SHA-256 mismatch")
    if audit.get("source_of_truth") == "TSETMC":
        if bale.get("source_sha256") != audit.get("snapshot_sha256"):
            raise RuntimeError("TSETMC Snapshot SHA-256 mismatch between Audit and Bale evidence")
    elif bale.get("source_sha256") != audit.get("source_sha256"):
        raise RuntimeError("Source SHA-256 mismatch between Audit and Bale evidence")
    if not bale.get("receipts"):
        raise RuntimeError("Bale receipts are missing")

    evidence = {
        "status": "PASS",
        "engine_version": "GATE6-RUNTIME-SHADOW-1.0",
        "generated_at_utc": started,
        "report_file": REPORT.name,
        "report_sha256": sha256_file(REPORT),
        "source_file": audit.get("source_file"),
        "source_sha256": audit.get("source_sha256"),
        "audit_integrity": (audit.get("audit_integrity") or {}).get("status"),
        "runtime_git_sha": runtime_git_sha,
        "bale_delivery_status": bale.get("status"),
        "bale_chunks": bale.get("chunks"),
        "bale_receipts": bale.get("receipts"),
        "secrets_recorded": False,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    GATE6_EVIDENCE.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
