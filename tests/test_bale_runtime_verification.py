import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bale_runtime_verification as verifier


class BaleRuntimeVerificationTests(unittest.TestCase):
    def test_success_records_report_and_source_identity_without_secret(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            report = root / "latest_report.txt"
            audit = root / "latest_audit.json"
            evidence = root / "bale_delivery_verification.json"
            report.write_text("REPORT\n", encoding="utf-8")
            audit.write_text(
                json.dumps(
                    {
                        "source_file": "optionschool_test.xlsx",
                        "source_sha256": "source-hash",
                        "generated_at": "2026-09-22T10:00:00+03:30",
                        "audit_integrity": {"status": "PASS"},
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch.object(verifier, "REPORT_PATH", report),
                patch.object(verifier, "AUDIT_PATH", audit),
                patch.object(verifier, "EVIDENCE_PATH", evidence),
                patch.dict(
                    verifier.os.environ,
                    {"BALE_BOT_TOKEN": "SECRET-TOKEN", "BALE_CHAT_ID": "123"},
                    clear=False,
                ),
                patch.object(verifier, "send_message", return_value=2) as send,
            ):
                verifier.main()

            payload = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "SUCCESS")
            self.assertEqual(payload["chunks"], 2)
            self.assertEqual(payload["source_sha256"], "source-hash")
            self.assertFalse(payload["secrets_recorded"])
            self.assertNotIn("SECRET-TOKEN", evidence.read_text(encoding="utf-8"))
            send.assert_called_once_with("SECRET-TOKEN", "123", "REPORT\n")

    def test_fails_before_send_without_pass_audit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            report = root / "latest_report.txt"
            audit = root / "latest_audit.json"
            evidence = root / "bale_delivery_verification.json"
            report.write_text("REPORT\n", encoding="utf-8")
            audit.write_text(
                json.dumps(
                    {
                        "source_file": "optionschool_test.xlsx",
                        "source_sha256": "source-hash",
                        "audit_integrity": {"status": "FAIL"},
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch.object(verifier, "REPORT_PATH", report),
                patch.object(verifier, "AUDIT_PATH", audit),
                patch.object(verifier, "EVIDENCE_PATH", evidence),
                patch.dict(
                    verifier.os.environ,
                    {"BALE_BOT_TOKEN": "SECRET-TOKEN", "BALE_CHAT_ID": "123"},
                    clear=False,
                ),
                patch.object(verifier, "send_message") as send,
            ):
                with self.assertRaises(RuntimeError):
                    verifier.main()

            send.assert_not_called()
            self.assertFalse(evidence.exists())


if __name__ == "__main__":
    unittest.main()
