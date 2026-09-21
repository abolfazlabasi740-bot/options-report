import unittest

from market_feature_shadow import build_market_features


class MarketFeatureTests(unittest.TestCase):
    def _history(self):
        return [{
            "instrument_id": "BASE1",
            "symbol": "فزر",
            "bars": [
                {"timestamp": "1", "close": 100, "high": 102, "low": 98, "volume": 100},
                {"timestamp": "2", "close": 105, "high": 107, "low": 103, "volume": 120},
                {"timestamp": "3", "close": 110, "high": 112, "low": 108, "volume": 150},
            ],
        }]

    def test_features_are_evidence_derived_and_windowed(self):
        result = build_market_features(self._history(), moving_average_windows=[2])
        row = result["rows"][0]
        self.assertEqual(row["bar_count"], 3)
        self.assertEqual(row["sequence_direction"], "UP")
        self.assertEqual(row["features"]["close_vs_sma_2_relation"], "ABOVE")
        self.assertEqual(row["features"]["price_direction_2"], "UP")
        self.assertEqual(row["features"]["volume_direction_2"], "UP")

    def test_missing_history_does_not_create_features(self):
        result = build_market_features(
            [{"instrument_id": "BASE1", "symbol": "فزر", "bars": []}],
            moving_average_windows=[2],
        )
        row = result["rows"][0]
        self.assertEqual(row["bar_count"], 0)
        self.assertIsNone(row["last_close"])
        self.assertEqual(row["features"]["close_vs_sma_2_relation"], "INSUFFICIENT_DATA")

    def test_windows_are_explicit(self):
        with self.assertRaises(ValueError):
            build_market_features(self._history(), moving_average_windows=[])


if __name__ == "__main__":
    unittest.main()
