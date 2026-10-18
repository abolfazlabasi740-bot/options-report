import unittest
from datetime import date

from base_share_opportunity_v2_report import _eligible_underlyings, _option_quality


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


    def test_unverified_and_blocked_underlyings_are_excluded_from_ranking(self):
        rows = [
            {
                "identity": {"underlying_id": "UNKNOWN", "end_date": ""},
                "market_watch_fields": {"volume": 100, "trade_count": 2},
            },
            {
                "identity": {"underlying_id": "BLOCKED", "end_date": "20261020"},
                "market_watch_fields": {"volume": 0, "trade_count": 0},
            },
            {
                "identity": {"underlying_id": "PASS", "end_date": "20261020"},
                "market_watch_fields": {"bid_quantity": 5, "ask_quantity": 7},
            },
        ]
        quality = {
            uid: _option_quality(rows, uid, date(2026, 10, 10))
            for uid in ("UNKNOWN", "BLOCKED", "PASS")
        }
        self.assertEqual(quality["UNKNOWN"]["status"], "UNVERIFIED")
        self.assertEqual(quality["BLOCKED"]["status"], "BLOCKED")
        self.assertEqual(quality["PASS"]["status"], "PASS")

        eligible = _eligible_underlyings(
            {"UNKNOWN": "نماد۱", "BLOCKED": "نماد۲", "PASS": "نماد۳"},
            quality,
        )
        self.assertEqual(eligible, {"PASS": "نماد۳"})


if __name__ == "__main__":
    unittest.main()
