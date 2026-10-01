#!/usr/bin/env python3
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
STATE = PROJECT / "PROJECT_FINISHER_STATE.json"

def cmd(*args, timeout=300):
    p = subprocess.run(args, cwd=PROJECT, text=True, capture_output=True, timeout=timeout)
    return p.returncode, p.stdout[-12000:], p.stderr[-12000:]

def write_state(**updates):
    data = json.loads(STATE.read_text(encoding="utf-8"))
    data.update(updates)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def git_record(message):
    rc, out, err = cmd("git", "add", "PROJECT_FINISHER_STATE.json")
    if rc != 0: raise RuntimeError(err or out)
    rc, out, err = cmd("git", "commit", "-m", message)
    if rc != 0 and "nothing to commit" not in (err + out).lower(): raise RuntimeError(err or out)
    rc, out, err = cmd("git", "push", "origin", "main")
    if rc != 0: raise RuntimeError(err or out)

def main():
    write_state(status="RUNNING", blocker=None, next_action="execute canonical V4.1 report")
    git_record("ops: finisher started")
    rc, out, err = cmd(sys.executable, "report_engine.py", "--top", "15", timeout=600)
    if rc == 0:
        write_state(status="REPORT_PASS", current_gate="REPORT_RUNTIME", blocker=None,
                    next_action="inspect report evidence and continue the first still-open authorized gate",
                    last_runtime_stdout=out)
    else:
        write_state(status="REPORT_FAILED", current_gate="REPORT_RUNTIME",
                    blocker=(err or out)[-4000:],
                    next_action="RCA report runtime failure")
    git_record("ops: finisher report checkpoint")
    print(json.dumps({"status": "SUCCESS" if rc == 0 else "FAILED", "exit_code": rc,
                      "state": str(STATE), "stdout": out, "stderr": err}, ensure_ascii=False))

if __name__ == "__main__":
    main()
