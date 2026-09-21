import unittest

from audit_integrity import verify_audit


class AuditIntegrityTests(unittest.TestCase):
    def _audit(self):
        return {
            "source_file": "x.xlsx",
            "source_sha256": "abc",
            "freshness_status": "UNVERIFIED_SOURCE_TIMESTAMP_MISSING",
            "selected_count": 1,
            "opportunity_shadow": {"snapshot_id": "S1"},
            "historical_snapshot": {
                "snapshot_id": "S1",
                "records_hash": "rh",
            },
            "replay_verification": {
                "status": "REPLAY_MATCH",
                "deterministic": True,
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


if __name__ == "__main__":
    unittest.main()
