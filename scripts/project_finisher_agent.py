#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OPTIMUSAI_PROJECT_FINISHER 2.1 — evidence-driven V4.1 supervisor."""
from __future__ import annotations

import json
import os
import hashlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

STATE = PROJECT / "PROJECT_FINISHER_STATE.json"
OUTPUT = PROJECT / "output"
PID_FILE = OUTPUT / "project_finisher_agent.pid"
LOG_FILE = OUTPUT / "project_finisher_agent.log"
INTERVAL_SECONDS = max(60, int(os.environ.get("FINISHER_INTERVAL_SECONDS", "900")))
MAX_RUNTIME_SECONDS = max(0, int(os.environ.get("FINISHER_MAX_RUNTIME_SECONDS", "0")))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def cmd(*args: str, timeout: int = 900):
    p = subprocess.run(args, cwd=PROJECT, text=True, capture_output=True, timeout=timeout)
    return p.returncode, p.stdout[-16000:], p.stderr[-16000:]


def read_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_state(**updates):
    data = read_state()
    data.update(updates)
    data["updated_at"] = now()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temp = STATE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, STATE)


def _rebase_main():
    rc, out, err = cmd("git", "fetch", "origin", "main", timeout=120)
    if rc:
        raise RuntimeError(err or out)
    rc, out, err = cmd("git", "rebase", "origin/main", timeout=180)
    if rc:
        cmd("git", "rebase", "--abort", timeout=60)
        raise RuntimeError("state rebase failed: " + (err or out)[-3000:])


def git_record(message: str):
    rc, out, err = cmd("git", "add", "PROJECT_FINISHER_STATE.json", timeout=60)
    if rc:
        raise RuntimeError(err or out)
    rc, out, err = cmd("git", "commit", "-m", message, timeout=60)
    if rc and "nothing to commit" not in (err + out).lower():
        raise RuntimeError(err or out)

    # ChatGPT may update code/docs on main while the Termux worker is running.
    # Rebase the state-only commit onto the latest main before pushing.
    for attempt in range(2):
        _rebase_main()
        rc, out, err = cmd("git", "push", "origin", "HEAD:main", timeout=120)
        if rc == 0:
            return
        if attempt == 0 and ("fetch first" in (err + out).lower() or "non-fast-forward" in (err + out).lower()):
            continue
        raise RuntimeError(err or out)


def notify_bale(message: str) -> tuple[bool, str]:
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False, "BALE_CREDENTIALS_MISSING"
    try:
        from bale_transport import send_message
        receipts = send_message(token, chat_id, message, return_receipts=True)
        if not receipts:
            return False, "BALE_NO_RECEIPTS"
        return True, json.dumps(receipts, ensure_ascii=False)
    except Exception as exc:
        return False, f"BALE_SEND_FAILED:{type(exc).__name__}:{str(exc)[:500]}"


def notify_on_change(key: str, message: str):
    state = read_state()
    if state.get("last_bale_notification_key") == key and state.get("bale_notified"):
        return True, state.get("bale_receipt", "PREVIOUS_RECEIPT_RETAINED")
    ok, receipt = notify_bale(message)
    updates = {"bale_notified": ok, "bale_receipt": receipt}
    if ok:
        updates["last_bale_notification_key"] = key
    write_state(**updates)
    return ok, receipt


def run_stage(name: str, argv: list[str], timeout: int):
    started = now()
    rc, out, err = cmd(*argv, timeout=timeout)
    return {
        "stage": name,
        "status": "PASS" if rc == 0 else "FAIL",
        "exit_code": rc,
        "started_at": started,
        "finished_at": now(),
        "stdout": out,
        "stderr": err,
    }


def cycle(cycle_no: int) -> bool:
    # Preserve the already-reached gate when a new 15-minute cycle starts.
    # A new cycle must not regress the canonical state back to Track A.
    previous = read_state()
    previous_g7 = previous.get("g7_5_status")
    previous_track_a = previous.get("track_a_release_status") == "RELEASED"
    if previous_track_a and previous_g7 == "VERIFIED":
        cycle_gate = "TRACK_CDE_RELEASE"
        cycle_action = "continue approved Track C/D/E/F completion checks; production BUY/SELL remains forbidden"
    elif previous_track_a:
        cycle_gate = "TRACK_B_VALIDATION"
        cycle_action = "continue G7-5 validation and verify runtime/audit"
    else:
        cycle_gate = "TRACK_A_RUNTIME"
        cycle_action = "run report, rebuild G7-5 diagnostics, and verify runtime/audit"

    write_state(
        version="2.1.0",
        status="RUNNING",
        current_gate=cycle_gate,
        blocker=None,
        human_action_required=False,
        next_action=cycle_action,
        cycle=cycle_no,
    )
    stages = []
    stages.append(run_stage("PROJECT_COMPLETION_AUDIT", [sys.executable, "project_completion_audit.py"], 120))
    stages.append(run_stage("REPORT_RUNTIME", [sys.executable, "report_engine.py", "--top", "15"], 900))
    if stages[-1]["status"] == "PASS":
        stages.append(run_stage("G7-5_EVIDENCE", [sys.executable, "economic_validation_evidence_builder.py"], 2400))
    if stages and stages[-1]["status"] == "PASS":
        stages.append(run_stage("RUNTIME_VERIFICATION", [sys.executable, "runtime_verification.py"], 900))

    completion_audit = load_json(OUTPUT / "project_completion_audit.json")
    failed = next((stage for stage in stages if stage["status"] != "PASS"), None)
    if failed:
        reason = (failed["stderr"] or failed["stdout"] or "stage failed")[-4000:]
        write_state(
            status="BLOCKED",
            current_gate=failed["stage"],
            blocker=reason,
            next_action=f"RCA and repair {failed['stage']}",
            human_action_required=False,
            last_cycle=stages,
            production_buy_sell=False,
            fail_closed=True,
        )
        git_record(f"ops: finisher cycle {cycle_no} failed {failed['stage']}")
        key = f"FAIL:{failed['stage']}:{hash(reason)}"
        notify_on_change(key, "OPTIMUSAI FINISHER\nوضعیت: BLOCKED\nمرحله: " + failed["stage"] + "\n" + reason[:2500])
        git_record(f"ops: finisher cycle {cycle_no} failure notification checkpoint")
        return False

    evidence_path = OUTPUT / "g7_5_economic_validation_evidence.json"
    runtime_path = OUTPUT / "runtime_verification.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    runtime = json.loads(runtime_path.read_text(encoding="utf-8")) if runtime_path.exists() else {}
    diagnostics = evidence.get("case_family_diagnostics") or {}
    families = diagnostics.get("supported_case_families") or {}
    family_counts = {
        name: item.get("confusion_counts")
        for name, item in families.items()
    }
    closure = evidence.get("closure") or {}
    gate_status = closure.get("g7_5_status", "OPEN")
    blocker = closure.get("reason") or "G7-5 closure evidence is unavailable."

    report_pass = bool(stages and stages[0].get("status") == "PASS")
    runtime_pass = runtime.get("status") == "PASS"
    if report_pass and runtime_pass:
        milestone_key = "MILESTONE:TRACK_A_SCREENING"
        previous = read_state()
        already_released = previous.get("track_a_release_status") == "RELEASED"
        write_state(
            status="MILESTONE_COMPLETE",
            current_gate="TRACK_B_VALIDATION" if gate_status != "VERIFIED" else "TRACK_CDE_RELEASE",
            blocker=None if gate_status == "VERIFIED" else blocker,
            track_a_release_status="RELEASED",
            full_project_status="IN_PROGRESS",
            next_action=(
                "G7-5 VERIFIED. Continue approved Track C/D/E/F completion checks; "
                "full project is not complete and production BUY/SELL remains forbidden."
                if gate_status == "VERIFIED"
                else "Track A screening delivered. Continue G7-5 validation and remaining approved scope tracks."
            ),
            last_cycle=stages,
            last_evidence_sha=evidence.get("evidence_sha256"),
            case_family_confusion_counts=family_counts,
            case_family_mapping_status=diagnostics.get("status"),
            unsupported_case_families=diagnostics.get("unsupported_case_families"),
            g7_5_status=gate_status,
            runtime_status=runtime.get("status"),
            production_buy_sell=False,
            fail_closed=True,
            completion_audit_status=completion_audit.get("status"),
            completion_audit_blockers=completion_audit.get("blockers"),
        )
        if completion_audit.get("status") == "COMPLETE":
            write_state(full_project_status="COMPLETE", current_gate="PROJECT_COMPLETE", blocker=None, next_action="project completion evidence verified; production BUY/SELL remains forbidden")
        git_record(f"ops: finisher cycle {cycle_no} Track A screening milestone")
        if gate_status == "VERIFIED":
            try:
                rc, git_head, git_err = cmd("git", "rev-parse", "HEAD", timeout=30)
                if rc == 0:
                    write_state(last_verified_commit=git_head.strip())
                    git_record(f"ops: finisher cycle {cycle_no} verified runtime commit")
            except Exception:
                pass
        if not already_released:
            notify_on_change(
                milestone_key,
                "OPTIMUSAI FINISHER\nوضعیت: TRACK_A_SCREENING_MILESTONE_COMPLETE\nگزارش TSETMC، فیلتر سررسید، روند پایه‌ها، ممیزی و Runtime تأیید شدند.\nاعتبارسنجی کامل G7-5 و مسیرهای بنیادی/اخبار/ریسک همچنان باز هستند؛ این پیام اعلام پایان کل پروژه یا مجوز BUY/SELL نیست."
            )
            git_record(f"ops: finisher cycle {cycle_no} milestone notification")
        return True

    write_state(
        status="IN_PROGRESS",
        current_gate="G7-5",
        blocker=blocker,
        next_action="continue family-level validation; then complete remaining approved market-context and risk tracks",
        last_cycle=stages,
        last_evidence_sha=evidence.get("evidence_sha256"),
        case_family_confusion_counts=family_counts,
        case_family_mapping_status=diagnostics.get("status"),
        unsupported_case_families=diagnostics.get("unsupported_case_families"),
        runtime_status=runtime.get("status"),
        production_buy_sell=False,
        fail_closed=True,
        human_action_required=False,
    )
    git_record(f"ops: finisher cycle {cycle_no} G7-5 progress")
    notification_state = {
        "status": "IN_PROGRESS",
        "gate": "G7-5",
        "mapping_status": diagnostics.get("status"),
        "blocker": blocker,
        "unsupported_families": sorted((diagnostics.get("unsupported_case_families") or {}).keys()),
    }
    key = "G7-5-STATE:" + hashlib.sha256(
        json.dumps(notification_state, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    message = (
        "OPTIMUSAI FINISHER\nوضعیت: IN_PROGRESS\n"
        f"چرخه: {cycle_no}\n"
        f"شواهد: {evidence.get('evidence_sha256', 'MISSING')}\n"
        f"تعداد خانواده‌های تشخیصی: {len(families)}\n"
        "G7-5 هنوز OPEN است؛ این پیام اعلام پایان پروژه نیست.\n"
        + blocker[:2200]
    )
    notify_on_change(key, message)
    git_record(f"ops: finisher cycle {cycle_no} progress notification")
    return False


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def daemonize() -> bool:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text(encoding="utf-8").strip())
            if _pid_alive(old_pid):
                print(f"FINISHER_ALREADY_RUNNING pid={old_pid}")
                return True
        except (ValueError, OSError):
            pass
    env = os.environ.copy()
    env["FINISHER_DAEMON_CHILD"] = "1"
    with LOG_FILE.open("a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
            cwd=str(PROJECT),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
            env=env,
            close_fds=True,
        )
    print("FINISHER_DAEMON_STARTED")
    return True


def worker():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    started = time.monotonic()
    cycle_no = int(read_state().get("cycle", 0))
    try:
        while True:
            cycle_no += 1
            try:
                cycle(cycle_no)
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                try:
                    write_state(
                        status="BLOCKED",
                        current_gate="FINISHER_RUNTIME",
                        blocker=reason,
                        next_action="RCA supervisor runtime failure",
                        human_action_required=False,
                        production_buy_sell=False,
                        fail_closed=True,
                    )
                    git_record(f"ops: finisher supervisor exception {cycle_no}")
                    notify_on_change("FINISHER_RUNTIME:" + reason, "OPTIMUSAI FINISHER\nوضعیت: BLOCKED\n" + reason)
                    git_record(f"ops: finisher supervisor notification {cycle_no}")
                except Exception:
                    pass
            if MAX_RUNTIME_SECONDS and time.monotonic() - started >= MAX_RUNTIME_SECONDS:
                break
            time.sleep(INTERVAL_SECONDS)
    finally:
        try:
            PID_FILE.unlink()
        except OSError:
            pass


def main():
    if "--once" in sys.argv:
        cycle(int(read_state().get("cycle", 0)) + 1)
        return
    if "--worker" in sys.argv:
        worker()
        return
    if os.environ.get("FINISHER_DAEMON_CHILD") == "1":
        worker()
        return
    daemonize()


if __name__ == "__main__":
    main()
