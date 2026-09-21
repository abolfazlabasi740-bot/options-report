import unittest

from historical_snapshot import build_snapshot
from historical_pattern_shadow import build_historical_patterns


class HistoricalPatternTests(unittest.TestCase):
    def test_consistent_score_sequence_is_detected_without_trade_semantics(self):
        history = [
            build_snapshot("S1", [{"نماد": "ضتست1", "FinalScore": 40, "last_price": 100, "volume": 100}]),
            build_snapshot("S2", [{"نماد": "ضتست1", "FinalScore": 45, "last_price": 102, "volume": 110}]),
            build_snapshot("S3", [{"نماد": "ضتست1", "FinalScore": 50, "last_price": 104, "volume": 120}]),
            build_snapshot("S4", [{"نماد": "ضتست1", "FinalScore": 55, "last_price": 106, "volume": 130}]),
        ]
        result = build_historical_patterns(history, window=3)
        types = {p["type"] for p in result["patterns"]}
        self.assertIn("FINALSCORE_UP_SEQUENCE", types)
        self.assertIn("PRICE_VOLUME_CONCORDANT", types)
        self.assertIn("SCORE_PRICE_ALIGNED", types)

    def test_missing_history_is_not_invented(self):
        history = [
            build_snapshot("S1", [{"نماد": "ضتست1", "FinalScore": 40}]),
        ]
        result = build_historical_patterns(history, window=3)
        self.assertEqual(result["status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(result["patterns"], [])

    def test_zero_delta_is_stable(self):
        history = [
            build_snapshot("S1", [{"نماد": "ضتست1", "FinalScore": 40}]),
            build_snapshot("S2", [{"نماد": "ضتست1", "FinalScore": 40}]),
            build_snapshot("S3", [{"نماد": "ضتست1", "FinalScore": 40}]),
            build_snapshot("S4", [{"نماد": "ضتست1", "FinalScore": 40}]),
        ]
        result = build_historical_patterns(history, window=3)
        types = {p["type"] for p in result["patterns"]}
        self.assertIn("FINALSCORE_STABLE_SEQUENCE", types)


if __name__ == "__main__":
    unittest.main()
