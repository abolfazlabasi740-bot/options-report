#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safe Termux deployment + Gate 6 launcher.

The launcher only fast-forwards the checked-out main branch to origin/main,
refuses to continue on tracked local modifications, and then runs the existing
Gate 6 orchestrator. It never handles or prints secrets.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(argv: list[str], capture: bool = True) -> str:
    result = subprocess.run(
        argv,
        cwd=ROOT,
        check=False,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"{' '.join(argv)} failed: {details}")
    return (result.stdout or "").strip()


def main() -> None:
    branch = run(["git", "branch", "--show-current"])
    if branch != "main":
        raise RuntimeError(f"Expected deployed branch 'main', found {branch!r}")

    status = run(["git", "status", "--porcelain"])
    if status:
        raise RuntimeError(
            "Tracked/uncommitted local changes detected; deployment stopped safely."
        )

    run(["git", "fetch", "--prune", "origin"])
    local = run(["git", "rev-parse", "HEAD"])
    remote = run(["git", "rev-parse", "origin/main"])

    if local != remote:
        run(["git", "pull", "--ff-only", "origin", "main"])

    deployed = run(["git", "rev-parse", "HEAD"])
    if deployed != remote:
        raise RuntimeError("Deployed HEAD does not match origin/main after fast-forward")

    result = subprocess.run(
        [sys.executable, "gate6_runtime_verification.py"],
        cwd=ROOT,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    print(f"TERMUX_GATE6_OK COMMIT={deployed}")


if __name__ == "__main__":
    main()
