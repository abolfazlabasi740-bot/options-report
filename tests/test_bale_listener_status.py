import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bale_listener


class BaleListenerStatusTests(unittest.TestCase):
    def test_system_status_reads_latest_audit_without_regenerating_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            audit = {
                "status": "PASS",
                "source_of_truth": "TSETMC",
                "data_mode": "LIVE_TSETMC_REFRESH",
                "live_refresh_status": "SUCCESS",
                "scoring_status": "TSETMC_EVIDENCE_RANKING",
                "ranking_status": "TSETMC_EVIDENCE_RANKING",
                "snapshot_sha256": "snapshot-sha",
                "report_sha256": "report-sha",
                "audit_integrity": {
                    "status": "PASS",
                    "failures": [],
                    "missing_fields": [],
                },
            }
            (output / "latest_audit.json").write_text(
                json.dumps(audit, ensure_ascii=False),
                encoding="utf-8",
            )
            (output / "latest_report.txt").write_text("REPORT", encoding="utf-8")

            with patch.object(bale_listener, "OUTPUT", output):
                result = bale_listener.system_status()

            self.assertIn("Audit: PASS", result)
            self.assertIn("Source: TSETMC", result)
            self.assertIn("Data Mode: LIVE_TSETMC_REFRESH", result)
            self.assertIn("Refresh: SUCCESS", result)
            self.assertIn("Audit Failures: 0", result)
            self.assertIn("Audit Missing Fields: 0", result)
            self.assertIn("Report File: READY", result)


if __name__ == "__main__":
    unittest.main()
