#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
LOCAL_EVIDENCE = OUTPUT / "github_evidence"
QUEUE = LOCAL_EVIDENCE / "_queue"
REMOTE = "https://github.com/abolfazlabasi740-bot/options-report.git"
REMOTE_BRANCH = "runtime-evidence"

ARTIFACTS = (
    OUTPUT / "latest_report.txt",
    OUTPUT / "latest_audit.json",
    OUTPUT / "tsetmc_first" / "latest_snapshot.json",
    OUTPUT / "tsetmc_first" / "latest_universe_snapshot.json",
    OUTPUT / "tsetmc_first" / "latest_source_audit.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd or ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def build_evidence() -> tuple[Path, dict]:
    audit_path = OUTPUT / "latest_audit.json"
    report_path = OUTPUT / "latest_report.txt"
    if not audit_path.exists() or not report_path.exists():
        raise RuntimeError("LATEST_REPORT_EVIDENCE_MISSING")

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    snapshot_sha = str(audit.get("snapshot_sha256") or "").strip()
    report_sha = str(audit.get("report_sha256") or "").strip()
    if not snapshot_sha or not report_sha:
        raise RuntimeError("AUDIT_SHA_MISSING")

    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%S%fZ")
    target = LOCAL_EVIDENCE / now.strftime("%Y-%m-%d") / f"{run_id}_{snapshot_sha[:12]}"
    target.mkdir(parents=True, exist_ok=True)

    manifest = {
        "publisher_version": "GITHUB-RUNTIME-EVIDENCE-1.0",
        "status": "READY",
        "published_at": now.isoformat(),
        "run_id": run_id,
        "snapshot_sha256": snapshot_sha,
        "report_sha256": report_sha,
        "source_of_truth": audit.get("source_of_truth"),
        "data_mode": audit.get("data_mode"),
        "live_refresh_status": audit.get("live_refresh_status"),
        "ranking_status": audit.get("ranking_status"),
        "scoring_status": audit.get("scoring_status"),
        "artifacts": [],
    }

    for source in ARTIFACTS:
        if not source.exists():
            continue
        destination = target / source.name
        shutil.copy2(source, destination)
        manifest["artifacts"].append(
            {
                "file": source.name,
                "sha256": sha256_file(destination),
                "bytes": destination.stat().st_size,
            }
        )

    if len(manifest["artifacts"]) < 2:
        raise RuntimeError("INSUFFICIENT_REPORT_EVIDENCE")

    manifest_path = target / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target, manifest


def publish(target: Path, manifest: dict) -> str:
    with tempfile.TemporaryDirectory(prefix="optimusai_github_") as tmp:
        worktree = Path(tmp) / "repo"
        git("clone", "--quiet", "--depth", "1", REMOTE, str(worktree))

        branch_exists = bool(
            git(
                "ls-remote",
                "--heads",
                "origin",
                REMOTE_BRANCH,
                cwd=worktree,
                check=False,
            ).stdout.strip()
        )

        if branch_exists:
            git("fetch", "--quiet", "origin", REMOTE_BRANCH, cwd=worktree)
            git("checkout", "--quiet", "-B", REMOTE_BRANCH, "FETCH_HEAD", cwd=worktree)
        else:
            git("checkout", "--quiet", "-b", REMOTE_BRANCH, cwd=worktree)

        destination = worktree / "runtime_evidence" / target.relative_to(LOCAL_EVIDENCE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(target, destination)

        git("add", str(destination.relative_to(worktree)), cwd=worktree)
        status = git("status", "--porcelain", cwd=worktree).stdout.strip()
        if not status:
            return "ALREADY_PRESENT"

        git(
            "-c", "user.name=OptimusAI Runtime",
            "-c", "user.email=optimusai-runtime@users.noreply.github.com",
            "commit", "-m",
            f"runtime evidence: {manifest['snapshot_sha256'][:12]}",
            cwd=worktree,
        )
        push = git("push", "origin", f"HEAD:{REMOTE_BRANCH}", cwd=worktree, check=False)
        if push.returncode != 0:
            raise RuntimeError("GITHUB_PUSH_FAILED")
        return "PUBLISHED"


def publish_latest_evidence() -> int:
    return main()


def main() -> int:
    try:
        target, manifest = build_evidence()
        try:
            result = publish(target, manifest)
        except Exception as exc:
            QUEUE.mkdir(parents=True, exist_ok=True)
            marker = QUEUE / f"{manifest['run_id']}.json"
            marker.write_text(
                json.dumps(
                    {
                        "status": "PENDING_RETRY",
                        "run_id": manifest["run_id"],
                        "snapshot_sha256": manifest["snapshot_sha256"],
                        "report_sha256": manifest["report_sha256"],
                        "error": type(exc).__name__,
                        "evidence_path": str(target),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            print("GITHUB_EVIDENCE_STATUS=PENDING_RETRY")
            print("GITHUB_EVIDENCE_ERROR=", type(exc).__name__)
            return 0

        print("GITHUB_EVIDENCE_STATUS=", result)
        print("GITHUB_EVIDENCE_SNAPSHOT_SHA=", manifest["snapshot_sha256"])
        print("GITHUB_EVIDENCE_REPORT_SHA=", manifest["report_sha256"])
        return 0
    except Exception as exc:
        print("GITHUB_EVIDENCE_STATUS=LOCAL_CAPTURE_FAILED")
        print("GITHUB_EVIDENCE_ERROR=", type(exc).__name__)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
