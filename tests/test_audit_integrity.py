import unittest

from audit_integrity import verify_audit


class AuditIntegrityTests(unittest.TestCase):
    def _audit(self):
        return {
            "source_file": "x.xlsx",
            "source_sha256": "abc",
            "source_sha256_recomputed": "abc",
            "report_sha256": "report",
            "freshness_status": "UNVERIFIED_SOURCE_TIMESTAMP_MISSING",
            "selected_count": 1,
            "selected": [{"نماد": "ضتست1"}],
            "opportunity_shadow": {"snapshot_id": "S1"},
            "historical_snapshot": {
                "snapshot_id": "S1",
                "records_hash": "rh",
            },
            "replay_verification": {
                "status": "REPLAY_MATCH",
                "deterministic": True,
                "baseline_hash": "a",
                "first_hash": "a",
                "second_hash": "a",
            },
        }

    def test_valid_audit_passes(self):
        self.assertEqual(verify_audit(self._audit())["status"], "PASS")

    def test_replay_mismatch_fails_closed(self):
        audit = self._audit()
        audit["replay_verification"]["status"] = "REPLAY_MISMATCH"
        result = verify_audit(audit)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("REPLAY_NOT_VERIFIED", result["failures"])

    def test_snapshot_mismatch_is_detected(self):
        audit = self._audit()
        audit["opportunity_shadow"]["snapshot_id"] = "S2"
        result = verify_audit(audit)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("SNAPSHOT_ID_MISMATCH", result["failures"])


    def test_source_hash_mismatch_fails_closed(self):
        audit = self._audit()
        audit["source_sha256_recomputed"] = "different"
        result = verify_audit(audit)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("SOURCE_HASH_MISMATCH", result["failures"])

    def test_selected_count_mismatch_fails_closed(self):
        audit = self._audit()
        audit["selected_count"] = 2
        result = verify_audit(audit)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("SELECTED_COUNT_MISMATCH", result["failures"])

    def test_missing_replay_baseline_fails_closed(self):
        audit = self._audit()
        del audit["replay_verification"]["baseline_hash"]
        result = verify_audit(audit)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("REPLAY_BASELINE_HASH_MISSING", result["failures"])


if __name__ == "__main__":
    unittest.main()
