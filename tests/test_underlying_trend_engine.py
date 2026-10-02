import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from underlying_trend_engine import analyze_history


class UnderlyingTrendEngineTests(unittest.TestCase):
    def make_history(self, instrument_id="123", date_offset=0):
        today = datetime.now(ZoneInfo("Asia/Tehran")).date() - timedelta(days=date_offset)
        rows = []
        for i in range(60):
            day = today - timedelta(days=59-i)
            close = 100.0 + i
            rows.append({
                "insCode": instrument_id,
                "dEven": int(day.strftime("%Y%m%d")),
                "hEven": 120000,
                "pClosing": close,
                "pDrCotVal": close,
                "priceMax": close + 1,
                "priceMin": close - 1,
                "qTotTran5J": 1000 + i * 10,
                "qTotCap": 100000 + i * 1000,
            })
        return list(reversed(rows))

    def test_indicators_and_current_limit_headroom(self):
        today = datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y%m%d")
        history = {
            "data": self.make_history(),
            "endpoint": "test://daily",
            "retrieved_at": "2026-10-02T00:00:00+00:00",
            "snapshot_sha256": "test-sha",
        }
        info = {
            "data": {"staticThreshold": {"psGelStaMax": 161.0, "psGelStaMin": 90.0}},
            "endpoint": "test://info",
            "retrieved_at": "2026-10-02T00:00:00+00:00",
            "snapshot_sha256": "info-sha",
        }
        result = analyze_history("123", history, info)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["latest_market_date"], today)
        self.assertEqual(result["trend_state"], "UP_TREND_STRUCTURE")
        self.assertAlmostEqual(result["sma_5"], 157.0)
        self.assertAlmostEqual(result["sma_20"], 149.5)
        self.assertAlmostEqual(result["sma_50"], 134.5)
        self.assertEqual(result["rsi_14"], 100.0)
        self.assertIsNotNone(result["upper_limit_headroom_pct"])
        self.assertFalse(result["touched_upper_limit_today"])

    def test_stale_history_does_not_claim_current_limit_headroom(self):
        history = {
            "data": self.make_history(date_offset=3),
            "endpoint": "test://daily",
            "snapshot_sha256": "test-sha",
        }
        info = {"data": {"staticThreshold": {"psGelStaMax": 161.0}}}
        result = analyze_history("123", history, info)
        self.assertIsNone(result["upper_limit_headroom_pct"])
        self.assertFalse(result["limit_threshold_date_match"])

    def test_exact_instrument_identity_is_required(self):
        history = {"data": self.make_history(instrument_id="other")}
        result = analyze_history("123", history)
        self.assertEqual(result["history_count"], 0)
        self.assertEqual(result["status"], "PARTIAL")


if __name__ == "__main__":
    unittest.main()
