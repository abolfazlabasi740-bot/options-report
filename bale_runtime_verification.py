#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot Bale runtime delivery verifier.

Sends the already-generated latest_report.txt to the configured Bale chat and
writes a non-secret evidence artifact. It does not run analysis or regenerate
the report.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from bale_transport import send_message


ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "output" / "latest_report.txt"
AUDIT_PATH = ROOT / "output" / "latest_audit.json"
EVIDENCE_PATH = ROOT / "output" / "bale_delivery_verification.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()

    if not token or not chat_id:
        raise RuntimeError("BALE_BOT_TOKEN و BALE_CHAT_ID باید از قبل تنظیم شوند")

    if not REPORT_PATH.exists():
        raise RuntimeError("output/latest_report.txt پیدا نشد؛ ابتدا Report Engine را اجرا کنید")

    report_text = REPORT_PATH.read_text(encoding="utf-8")
    if not report_text.strip():
        raise RuntimeError("output/latest_report.txt خالی است")

    audit = {}
    if AUDIT_PATH.exists():
        try:
            audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError("latest_audit.json قابل خواندن نیست") from exc

    report_sha256 = sha256_file(REPORT_PATH)
    source_sha256 = audit.get("source_sha256")
    source_file = audit.get("source_file")
    audit_status = (audit.get("audit_integrity") or {}).get("status")
    generated_at = audit.get("generated_at")

    if not source_sha256 or not source_file:
        raise RuntimeError("هویت منبع در latest_audit.json موجود نیست")
    if audit_status != "PASS":
        raise RuntimeError("Audit integrity در latest_audit.json باید PASS باشد")

    started_at = datetime.now(timezone.utc).isoformat()
    try:
        receipts = send_message(token, chat_id, report_text, return_receipts=True)
        if (not receipts or any(
            not r.get("message_id")
            or r.get("chat_id") is None
            or str(r.get("chat_id")) != str(chat_id)
            for r in receipts
        )):
            raise RuntimeError("Bale delivery receipt ناقص یا مربوط به مقصد دیگری است")
        chunks = len(receipts)
    except Exception as exc:
        evidence = {
            "status": "FAIL",
            "generated_at_utc": started_at,
            "report_file": REPORT_PATH.name,
            "report_sha256": report_sha256,
            "source_file": source_file,
            "source_sha256": source_sha256,
            "report_generated_at": generated_at,
            "audit_integrity": audit_status,
            "chunks": None,
            "environment_presence_only": {
                "BALE_BOT_TOKEN": True,
                "BALE_CHAT_ID": True,
            },
            "secrets_recorded": False,
            "error_type": type(exc).__name__,
        }
        EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE_PATH.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        raise

    evidence = {
        "status": "SUCCESS",
        "generated_at_utc": started_at,
        "report_file": REPORT_PATH.name,
        "report_sha256": report_sha256,
        "source_file": source_file,
        "source_sha256": source_sha256,
        "report_generated_at": generated_at,
        "audit_integrity": audit_status,
        "chunks": chunks,
        "environment_presence_only": {
            "BALE_BOT_TOKEN": True,
            "BALE_CHAT_ID": True,
        },
        "secrets_recorded": False,
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
