import unittest

from underlying_trend_engine import _board_metrics


class UnderlyingBoardMetricsTests(unittest.TestCase):
    def test_orderbook_depth_and_individual_legal_power(self):
        orderbook = {
            "endpoint": "test://best-limits",
            "retrieved_at": "2026-10-02T01:00:00+00:00",
            "snapshot_sha256": "book-sha",
            "data": [
                {"number": 2, "qTitMeDem": 500, "zOrdMeDem": 2, "pMeDem": 99, "pMeOf": 102, "zOrdMeOf": 1, "qTitMeOf": 400},
                {"number": 1, "qTitMeDem": 1000, "zOrdMeDem": 3, "pMeDem": 100, "pMeOf": 101, "zOrdMeOf": 2, "qTitMeOf": 600},
            ],
        }
        client = {
            "endpoint": "test://client-type",
            "retrieved_at": "2026-10-02T01:00:00+00:00",
            "snapshot_sha256": "client-sha",
            "data": {
                "buy_I_Volume": 1000, "sell_I_Volume": 500,
                "buy_CountI": 10, "sell_CountI": 5,
                "buy_N_Volume": 300, "sell_N_Volume": 600,
                "buy_CountN": 3, "sell_CountN": 3,
            },
        }
        result = _board_metrics(orderbook, client)
        self.assertEqual(result["orderbook_level_count"], 2)
        self.assertEqual(result["bid_depth_volume_5"], 1500)
        self.assertEqual(result["ask_depth_volume_5"], 1000)
        self.assertAlmostEqual(result["bid_ask_volume_ratio_5"], 1.5)
        self.assertAlmostEqual(result["orderbook_imbalance_5"], 0.2)
        self.assertEqual(result["best_bid_price"], 100)
        self.assertEqual(result["best_ask_price"], 101)
        self.assertAlmostEqual(result["best_bid_ask_spread_pct"], 100 * 1 / 100.5)
        self.assertEqual(result["individual_power_ratio"], 1.0)
        self.assertEqual(result["legal_power_ratio"], 0.5)

    def test_empty_client_type_is_not_misread_as_zero_power(self):
        result = _board_metrics({"data": []}, {"data": {
            "buy_I_Volume": 0, "sell_I_Volume": 0,
            "buy_CountI": 0, "sell_CountI": 0,
            "buy_N_Volume": 0, "sell_N_Volume": 0,
            "buy_CountN": 0, "sell_CountN": 0,
        }})
        self.assertEqual(result["client_type_status"], "NO_RECORDED_ACTIVITY")
        self.assertIsNone(result["individual_power_ratio"])
        self.assertEqual(result["orderbook_status"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
