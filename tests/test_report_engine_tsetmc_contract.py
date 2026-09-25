import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import report_engine


class ReportEngineTsetmcContractTests(unittest.TestCase):
    def test_save_publishes_gate6_canonical_artifacts(self):
        snapshot = {
            "status": "SUCCESS",
            "source_of_truth": "TSETMC",
            "snapshot_sha256": "a" * 64,
            "row_count": 1,
            "generated_at": "2026-09-25T10:00:00+03:30",
            "data_mode": "LAST_KNOWN_TSETMC_SNAPSHOT",
            "live_refresh_status": "UNAVAILABLE",
            "fallback_reason": "NETWORK_UNAVAILABLE",
            "market_state": {"latest_source_market_timestamp": "2026-09-24T12:29:00+03:30"},
            "evidence": {"market_watch": {"record_count": 1}},
        }
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch.object(report_engine, "ROOT", root):
                report_path = report_engine.save_tsetmc_report("REPORT\n", snapshot)

            canonical_report = root / "output" / "latest_report.txt"
            canonical_audit = root / "output" / "latest_audit.json"
            self.assertEqual(report_path, canonical_report)
            self.assertTrue(canonical_report.exists())
            self.assertTrue(canonical_audit.exists())

            audit = json.loads(canonical_audit.read_text(encoding="utf-8"))
            self.assertEqual(audit["source_of_truth"], "TSETMC")
            self.assertEqual(audit["data_mode"], "LAST_KNOWN_TSETMC_SNAPSHOT")
            self.assertEqual(audit["live_movement_claim"], "NOT_CLAIMED")
            self.assertEqual(audit["audit_integrity"]["status"], "PASS")
            self.assertEqual(
                audit["report_sha256"],
                hashlib.sha256(b"REPORT\n").hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
