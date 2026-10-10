import unittest
from datetime import date

from base_share_opportunity_v2_report import _option_quality


class BaseShareOpportunityReportTests(unittest.TestCase):
    def test_option_quality_ignores_expired_and_requires_explicit_activity(self):
        rows = [
            {
                "identity": {"underlying_id": "BASE", "end_date": "20261001"},
                "market_watch_fields": {"volume": 100, "trade_count": 2},
            },
            {
                "identity": {"underlying_id": "BASE", "end_date": "20261020"},
                "market_watch_fields": {"volume": 0, "trade_count": 0},
            },
            {
                "identity": {"underlying_id": "BASE", "end_date": "20261025"},
                "market_watch_fields": {"bid_quantity": 3, "ask_quantity": 4},
            },
        ]
        result = _option_quality(rows, "BASE", date(2026, 10, 10))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["active_contracts"], 2)
        self.assertEqual(result["liquid_contracts"], 1)
        self.assertEqual(result["traded_contracts"], 0)
        self.assertEqual(result["two_sided_contracts"], 1)


if __name__ == "__main__":
    unittest.main()
