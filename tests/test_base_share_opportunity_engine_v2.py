import unittest

from base_share_opportunity_engine_v2 import score_opportunity


class BaseShareOpportunityEngineV2Tests(unittest.TestCase):
    def test_low_evidence_coverage_cannot_be_class_a(self):
        result = score_opportunity({
            "trend_state": "UP_TREND_STRUCTURE",
            "rsi_14": 60,
        })
        self.assertLess(result["evidence_coverage_pct"], 70.0)
        self.assertEqual(result["classification"], "C")
        self.assertIn("PARTIAL_EVIDENCE_COVERAGE", result["warnings"])

    def test_stale_history_is_flagged_and_capped(self):
        result = score_opportunity({
            "trend_state": "UP_TREND_STRUCTURE",
            "rsi_14": 60,
            "freshness_status": "STALE",
        })
        self.assertEqual(result["classification"], "C")
        self.assertIn("STALE_HISTORY", result["warnings"])


if __name__ == "__main__":
    unittest.main()
