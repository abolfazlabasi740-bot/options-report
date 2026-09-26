import unittest

from calibration_engine import (
    CALIBRATION_ENGINE_VERSION,
    calibrate_candidates,
    summarize_feature,
)


class CalibrationEngineTests(unittest.TestCase):
    def _candidate(self, value):
        return {
            "evidence": {
                "features": {
                    "trade_value": value,
                    "volume": value * 10,
                }
            }
        }

    def test_feature_summary_is_deterministic(self):
        candidates = [self._candidate(10), self._candidate(20), self._candidate(30)]
        result = summarize_feature(candidates, "trade_value")
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["p50"], 20.0)
        self.assertEqual(result["p05"], 12.0)
        self.assertEqual(result["p95"], 28.0)

    def test_missing_values_are_not_zero_filled(self):
        candidates = [self._candidate(10), {"evidence": {"features": {}}}]
        result = summarize_feature(candidates, "trade_value")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["coverage"], 0.5)
        self.assertEqual(result["min"], 10.0)

    def test_calibration_cannot_generate_signal_or_threshold(self):
        result = calibrate_candidates([self._candidate(10), self._candidate(20)])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["engine_version"], CALIBRATION_ENGINE_VERSION)
        self.assertEqual(result["rules"]["signal_generation"], "FORBIDDEN")
        self.assertEqual(result["rules"]["threshold_generation"], "OBSERVATION_ONLY")
        self.assertEqual(result["rules"]["labels"], "NOT_INFERRED")


if __name__ == "__main__":
    unittest.main()
