import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from last_minute_profit_engine import build_last_minute_ranking

TEHRAN = ZoneInfo("Asia/Tehran")


class LastMinuteProfitTests(unittest.TestCase):
    def row(self, symbol, S, K, P, days=1, typ="CALL"):
        return {
            "canonical": {
                "نماد": symbol,
                "قیمت سهم پایه": S,
                "قیمت اعمال": K,
                "آخرین قیمت": P,
                "روزهای تقویمی": days,
            },
            "identity": {
                "instrument_id": symbol,
                "underlying_symbol": "BASE",
                "contract_type": typ,
            },
        }

    def test_only_one_day_and_itm(self):
        result = build_last_minute_ranking([
            self.row("ITM", 103, 100, 2),
            self.row("OTM", 98, 100, 2),
            self.row("TWO_DAYS", 103, 100, 2, days=2),
        ])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["ranking_rows"][0]["symbol"], "ITM")

    def test_three_percent_underlying_scenario(self):
        result = build_last_minute_ranking([self.row("A", 100, 90, 2)])
        item = result["ranking_rows"][0]
        self.assertAlmostEqual(item["scenario_underlying_price"], 103.0)
        self.assertAlmostEqual(item["scenario_option_value_at_expiry"], 13.0)
        self.assertAlmostEqual(item["scenario_return_pct"], 550.0)

    def test_put_itm(self):
        result = build_last_minute_ranking([
            self.row("P", 90, 100, 2, typ="PUT"),
        ])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["ranking_rows"][0]["contract_type"], "PUT")
        self.assertEqual(result["ranking_rows"][0]["scenario_option_value_at_expiry"], 7.0)

    def test_non_positive_scenario_return_excluded(self):
        result = build_last_minute_ranking([self.row("A", 103, 100, 10)])
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["status"], "NO_ELIGIBLE_OPPORTUNITY")


if __name__ == "__main__":
    unittest.main()
