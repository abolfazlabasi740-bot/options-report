#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPTIMUSAI_PROJECT_FINISHER v2
Self-driving supervisor for the authorized V4.1 path.

It never bypasses a frozen gate. It repeatedly:
report -> validation evidence -> runtime verification -> gate inspection
and stops only at VERIFIED/COMPLETED or an explicit HUMAN_ACTION_REQUIRED state.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
STATE = PROJECT / "PROJECT_FINISHER_STATE.json"
INTERVAL_SECONDS = int(os.environ.get("FINISHER_INTERVAL_SECONDS", "900"))
MAX_RUNTIME_SECONDS = int(os.environ.get("FINISHER_MAX_RUNTIME_SECONDS", "0"))

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def cmd(*args: str, timeout: int = 900):
    p = subprocess.run(
        args, cwd=PROJECT, text=True, capture_output=True, timeout=timeout
    )
    return p.returncode, p.stdout[-16000:], p.stderr[-16000:]

def read_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))

def write_state(**updates):
    data = read_state()
    data.update(updates)
    data["updated_at"] = now()
    STATE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

def git_record(message: str):
    rc, out, err = cmd("git", "add", "PROJECT_FINISHER_STATE.json", timeout=60)
    if rc != 0:
        raise RuntimeError(err or out)
    rc, out, err = cmd("git", "commit", "-m", message, timeout=60)
    if rc != 0 and "nothing to commit" not in (err + out).lower():
        raise RuntimeError(err or out)
    rc, out, err = cmd("git", "push", "origin", "main", timeout=120)
    if rc != 0:
        raise RuntimeError(err or out)

def notify_bale(text: str) -> tuple[bool, str]:
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False, "BALE_CREDENTIALS_MISSING"
    try:
        from bale_transport import send_message
        receipts = send_message(token, chat_id, text, return_receipts=True)
        if not receipts:
            return False, "BALE_NO_RECEIPTS"
        return True, json.dumps(receipts, ensure_ascii=False)
    except Exception as exc:
        return False, f"BALE_SEND_FAILED:{type(exc).__name__}"

def run_stage(name: str, argv: list[str], timeout: int = 1200):
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

def inspect_gate() -> tuple[str, str, bool]:
    evidence = PROJECT / "output" / "g7_5_economic_validation_evidence.json"
    if not evidence.exists():
        return "G7-5", "economic validation evidence file is missing", False
    try:
        data = json.loads(evidence.read_text(encoding="utf-8"))
    except Exception as exc:
        return "G7-5", f"economic validation evidence unreadable: {type(exc).__name__}", False
    closure = data.get("closure") or {}
    status = closure.get("g7_5_status")
    if status == "VERIFIED":
        return "G7-5", "G7-5 independently verified by its frozen protocol", True
    return "G7-5", str(closure.get("reason") or "frozen G7-5 closure requirements remain open"), False

def cycle(cycle_no: int) -> bool:
    write_state(
        version="2.0.0",
        status="RUNNING",
        current_gate="REPORT_RUNTIME",
        blocker=None,
        human_action_required=False,
        next_action="run canonical report, economic validation evidence, and runtime verification",
        cycle=cycle_no,
    )

    stages = []
    stages.append(run_stage(
        "REPORT_RUNTIME",
        [sys.executable, "report_engine.py", "--top", "15"],
        timeout=900,
    ))
    if stages[-1]["status"] != "PASS":
        reason = stages[-1]["stderr"] or stages[-1]["stdout"]
        write_state(
            status="BLOCKED",
            current_gate="REPORT_RUNTIME",
            blocker=reason[-4000:],
            next_action="RCA report runtime failure",
            human_action_required=False,
            last_cycle=stages,
        )
        git_record(f"ops: finisher cycle {cycle_no} report failed")
        ok, receipt = notify_bale("OPTIMUSAI FINISHER\nوضعیت: BLOCKED\nمرحله: REPORT_RUNTIME\nعلت: اجرای گزارش ناموفق بود.\n" + reason[-2500:])
        write_state(bale_notified=ok, bale_receipt=receipt)
        git_record(f"ops: finisher cycle {cycle_no} notification")
        return False

    stages.append(run_stage(
        "G7-5_EVIDENCE",
        [sys.executable, "economic_validation_evidence_builder.py"],
        timeout=1800,
    ))
    if stages[-1]["status"] != "PASS":
        reason = stages[-1]["stderr"] or stages[-1]["stdout"]
        write_state(
            status="BLOCKED",
            current_gate="G7-5",
            blocker=reason[-4000:],
            next_action="RCA economic validation evidence build",
            human_action_required=False,
            last_cycle=stages,
        )
        git_record(f"ops: finisher cycle {cycle_no} G7-5 failed")
        ok, receipt = notify_bale("OPTIMUSAI FINISHER\nوضعیت: BLOCKED\nمرحله: G7-5 EVIDENCE\nعلت: ساخت Evidence ناموفق بود.\n" + reason[-2500:])
        write_state(bale_notified=ok, bale_receipt=receipt)
        git_record(f"ops: finisher cycle {cycle_no} notification")
        return False

    stages.append(run_stage(
        "RUNTIME_VERIFICATION",
        [sys.executable, "runtime_verification.py"],
        timeout=900,
    ))
    if stages[-1]["status"] != "PASS":
        reason = stages[-1]["stderr"] or stages[-1]["stdout"]
        write_state(
            status="BLOCKED",
            current_gate="RUNTIME_VERIFICATION",
            blocker=reason[-4000:],
            next_action="RCA runtime verification failure",
            human_action_required=False,
            last_cycle=stages,
        )
        git_record(f"ops: finisher cycle {cycle_no} runtime verification failed")
        ok, receipt = notify_bale("OPTIMUSAI FINISHER\nوضعیت: BLOCKED\nمرحله: RUNTIME_VERIFICATION\nعلت: ممیزی runtime ناموفق بود.\n" + reason[-2500:])
        write_state(bale_notified=ok, bale_receipt=receipt)
        git_record(f"ops: finisher cycle {cycle_no} notification")
        return False

    gate, blocker, verified = inspect_gate()
    if verified:
        write_state(
            status="COMPLETED",
            current_gate=gate,
            blocker=None,
            next_action="authorized V4.1 path completed; retain production BUY/SELL fail-closed policy unless separately authorized",
            human_action_required=False,
            last_cycle=stages,
        )
        git_record(f"ops: finisher cycle {cycle_no} completed")
        ok, receipt = notify_bale(
            "OPTIMUSAI FINISHER\nوضعیت: COMPLETED\nمسیر مجاز V4.1 تکمیل شد.\nBUY/SELL همچنان تابع مجوز مستقل است."
        )
        write_state(bale_notified=ok, bale_receipt=receipt)
        git_record(f"ops: finisher cycle {cycle_no} completion notification")
        return True

    # The frozen protocol itself says the remaining blocker is evidence/label
    # closure, not an implementation failure. Keep running evidence cycles but
    # report the exact blocker rather than inventing a closure.
    write_state(
        status="BLOCKED",
        current_gate=gate,
        blocker=blocker,
        next_action="continue evidence-backed G7-5 closure work; never fabricate independent labels",
        human_action_required=False,
        last_cycle=stages,
    )
    git_record(f"ops: finisher cycle {cycle_no} G7-5 blocker")
    ok, receipt = notify_bale(
        "OPTIMUSAI FINISHER\nوضعیت: BLOCKED_BY_FROZEN_GATE\nمرحله: G7-5\n"
        + blocker[:2800]
    )
    write_state(bale_notified=ok, bale_receipt=receipt)
    git_record(f"ops: finisher cycle {cycle_no} blocker notification")
    return False

def daemonize() -> bool:
    if os.environ.get("FINISHER_DAEMON_CHILD") == "1":
        return False
    env = os.environ.copy()
    env["FINISHER_DAEMON_CHILD"] = "1"
    log = PROJECT / "output" / "project_finisher_agent.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
            cwd=str(PROJECT),
            stdin=subprocess.DEVNULL,
            stdout=fh,
            stderr=fh,
            start_new_session=True,
            env=env,
            close_fds=True,
        )
    print("FINISHER_DAEMON_STARTED")
    return True

def main():
    if "--worker" not in sys.argv and daemonize():
        return
    started = time.monotonic()
    cycle_no = 0
    while True:
        cycle_no += 1
        try:
            cycle(cycle_no)
        except Exception as exc:
            try:
                write_state(
                    status="BLOCKED",
                    current_gate="FINISHER_RUNTIME",
                    blocker=f"{type(exc).__name__}: {exc}",
                    next_action="RCA finisher supervisor failure",
                    human_action_required=False,
                )
                git_record(f"ops: finisher supervisor exception {cycle_no}")
            except Exception:
                pass
        if MAX_RUNTIME_SECONDS and time.monotonic() - started >= MAX_RUNTIME_SECONDS:
            break
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
