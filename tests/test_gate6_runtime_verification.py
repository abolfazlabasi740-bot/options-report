import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import gate6_runtime_verification as gate6


class Gate6RuntimeVerificationTests(unittest.TestCase):
    def test_main_validates_same_report_and_source_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output = root / "output"
            output.mkdir()
            report = output / "latest_report.txt"
            audit = output / "latest_audit.json"
            runtime = output / "runtime_verification.json"
            bale = output / "bale_delivery_verification.json"
            evidence = output / "gate6_runtime_evidence.json"

            report.write_text("REPORT", encoding="utf-8")
            runtime.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
            audit.write_text(json.dumps({
                "source_file": "source.xlsx",
                "source_sha256": "source-sha",
                "audit_integrity": {"status": "PASS"},
            }), encoding="utf-8")
            bale.write_text(json.dumps({
                "status": "SUCCESS",
                "report_sha256": gate6.sha256_file(report),
                "source_sha256": "source-sha",
                "chunks": 1,
                "receipts": [{"message_id": 10, "chat_id": 20}],
            }), encoding="utf-8")

            with (
                patch.object(gate6, "OUTPUT", output),
                patch.object(gate6, "AUDIT", audit),
                patch.object(gate6, "REPORT", report),
                patch.object(gate6, "RUNTIME_EVIDENCE", runtime),
                patch.object(gate6, "BALE_EVIDENCE", bale),
                patch.object(gate6, "GATE6_EVIDENCE", evidence),
                patch.object(gate6, "run_step") as run_step,
            ):
                gate6.main()

            payload = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["source_sha256"], "source-sha")
            self.assertEqual(payload["bale_receipts"], [{"message_id": 10, "chat_id": 20}])
            self.assertEqual(run_step.call_count, 3)

    def test_main_rejects_runtime_verification_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output = root / "output"
            output.mkdir()
            report = output / "latest_report.txt"
            audit = output / "latest_audit.json"
            runtime = output / "runtime_verification.json"
            bale = output / "bale_delivery_verification.json"
            evidence = output / "gate6_runtime_evidence.json"
            report.write_text("REPORT", encoding="utf-8")
            audit.write_text(json.dumps({"source_file": "source.xlsx", "source_sha256": "source-sha", "audit_integrity": {"status": "PASS"}}), encoding="utf-8")
            runtime.write_text(json.dumps({"status": "FAIL"}), encoding="utf-8")
            bale.write_text(json.dumps({"status": "SUCCESS", "report_sha256": gate6.sha256_file(report), "source_sha256": "source-sha", "chunks": 1, "receipts": [{"message_id": 10, "chat_id": 20}]}), encoding="utf-8")
            with (
                patch.object(gate6, "AUDIT", audit),
                patch.object(gate6, "REPORT", report),
                patch.object(gate6, "RUNTIME_EVIDENCE", runtime),
                patch.object(gate6, "BALE_EVIDENCE", bale),
                patch.object(gate6, "GATE6_EVIDENCE", evidence),
                patch.object(gate6, "run_step"),
            ):
                with self.assertRaises(RuntimeError):
                    gate6.main()

    def test_main_rejects_report_sha_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output = root / "output"
            output.mkdir()
            report = output / "latest_report.txt"
            audit = output / "latest_audit.json"
            runtime = output / "runtime_verification.json"
            bale = output / "bale_delivery_verification.json"
            evidence = output / "gate6_runtime_evidence.json"

            report.write_text("REPORT", encoding="utf-8")
            runtime.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
            audit.write_text(json.dumps({
                "source_file": "source.xlsx",
                "source_sha256": "source-sha",
                "audit_integrity": {"status": "PASS"},
            }), encoding="utf-8")
            runtime.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
            bale.write_text(json.dumps({
                "status": "SUCCESS",
                "report_sha256": "wrong",
                "source_sha256": "source-sha",
                "chunks": 1,
                "receipts": [{"message_id": 10, "chat_id": 20}],
            }), encoding="utf-8")

            with (
                patch.object(gate6, "AUDIT", audit),
                patch.object(gate6, "REPORT", report),
                patch.object(gate6, "RUNTIME_EVIDENCE", runtime),
                patch.object(gate6, "BALE_EVIDENCE", bale),
                patch.object(gate6, "GATE6_EVIDENCE", evidence),
                patch.object(gate6, "run_step"),
            ):
                with self.assertRaises(RuntimeError):
                    gate6.main()


if __name__ == "__main__":
    unittest.main()
