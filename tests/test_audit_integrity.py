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


    def test_tsetmc_disabled_best_limits_are_nonblocking(self):
        audit = {
            "audit_version": "AUDIT-INTEGRITY-1.3",
            "source_of_truth": "TSETMC",
            "data_mode": "LIVE_TSETMC_REFRESH",
            "live_refresh_status": "SUCCESS",
            "snapshot_sha256": "snap",
            "row_count": 1,
            "generated_at": "2026-09-26T12:30:00Z",
            "live_movement_claim": "NOT_CLAIMED",
            "scoring_status": "TSETMC_EVIDENCE_RANKING",
            "ranking_status": "TSETMC_EVIDENCE_RANKING",
            "market_watch": {
                "endpoint": "Instrument/GetInstrumentOptionMarketWatch/1",
                "snapshot_sha256": "mw",
                "retrieved_at": "2026-09-26T12:30:00Z",
            },
            "best_limits_evidence": {
                "contract": {
                    "status": "RAW_ONLY_QUARANTINED",
                    "source": "TSETMC",
                    "identity_binding": "instrument_id",
                    "market_watch_binding": "market_watch_snapshot_sha256",
                    "source_timestamp_binding": "source_market_timestamp",
                    "delta_seconds_limit": 2.0,
                    "consumption_status": "NOT_CONSUMED_BY_SCORING_OR_RANKING",
                },
                "rows": [{
                    "instrument_id": "I1",
                    "status": "NOT_REQUESTED",
                    "reason": "AUXILIARY_BEST_LIMITS_DISABLED_BY_DEFAULT",
                    "source": "TSETMC",
                    "endpoint": "BestLimits/{instrument_id}",
                }],
            },
            "market_state": {},
            "report_sha256": "report",
        }
        result = verify_audit(audit)
        self.assertEqual(result["status"], "PASS")
        self.assertNotIn("BEST_LIMITS_REQUEST_FAILED", result["failures"])
        self.assertNotIn("BEST_LIMITS_DELTA_NOT_WITHIN_2_SECONDS", result["failures"])

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


    def test_shadow_analytical_failure_is_explicitly_nonblocking(self):
        audit = self._audit()
        audit["opportunity_shadow"]["status"] = "FAILED"
        audit["replay_verification"] = {
            "status": "SKIPPED_SHADOW_FAILURE",
            "deterministic": False,
        }
        result = verify_audit(audit)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["checks"]["shadow_failure_nonblocking"])

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
