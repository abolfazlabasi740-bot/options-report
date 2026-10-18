# -*- coding: utf-8 -*-
"""تست لایه-overlay زندهٔ بازار — قیمت امروز بدون دست‌زدن به امتیازها"""
import unittest
from unittest.mock import patch

import live_market_overlay as lmo


def _feed_record(ins="111", symbol="TEST", pdv=1000.0, pcl=990.0, py=950.0,
                 qtj=5000.0, qtc=5_000_000.0, ztt=12.0, heven="121500"):
    return {
        "instrument_id": ins,
        "symbol": symbol,
        "raw": {"lva": symbol, "pdv": pdv, "pcl": pcl, "py": py,
                "qtj": qtj, "qtc": qtc, "ztt": ztt, "hEven": heven},
    }


class LiveMarketOverlayTests(unittest.TestCase):
    def test_apply_overlay_attaches_live_fields_by_id(self):
        overlay = {"111": {"live_last_price": 1000.0, "live_close_price": 990.0,
                           "live_prev_close": 950.0, "live_change_pct": 5.26,
                           "live_time": "12:15:00", "live_symbol": "TEST"}}
        rows = [
            {"instrument_id": "111", "symbol": "TEST", "final_score": 80},
            {"instrument_id": "222", "symbol": "OTHER", "final_score": 70},
        ]
        lmo.apply_live_overlay(rows, overlay)
        self.assertEqual(rows[0]["live_status"], "LIVE_TODAY")
        self.assertEqual(rows[0]["live_last_price"], 1000.0)
        self.assertIs(rows[0].get("final_score"), 80)  # score untouched
        self.assertEqual(rows[1]["live_status"], "EOD_ONLY")
        self.assertNotIn("live_last_price", rows[1])

    def test_apply_overlay_symbol_fallback_when_id_missing(self):
        overlay = {"999": {"live_symbol": "فولاد", "live_last_price": 4450.0}}
        rows = [{"instrument_id": None, "symbol": "فولاد", "final_score": 50}]
        lmo.apply_live_overlay(rows, overlay)
        self.assertEqual(rows[0]["live_status"], "LIVE_TODAY")
        self.assertEqual(rows[0]["live_last_price"], 4450.0)

    def test_apply_overlay_noop_when_empty(self):
        rows = [{"instrument_id": "1", "final_score": 5}]
        lmo.apply_live_overlay(rows, {})
        self.assertNotIn("live_status", rows[0])

    def test_fetch_overlay_normalizes_and_skips_dead_records(self):
        universe = {
            "endpoint": "x", "retrieved_at": "t", "snapshot_sha256": "s",
            "records": [
                _feed_record(ins="111", symbol="ومعلم"),
                # dead record: everything zero → must be excluded
                _feed_record(ins="222", symbol="DEAD", pdv=0.0, pcl=0.0,
                             qtj=0.0, qtc=0.0),
            ],
        }
        class FakeAdapter:
            def market_watch_universe_raw(self, with_best_limits=False):
                return universe
        with patch.object(lmo, "session_state", return_value="CLOSED_TODAY"):
            overlay = lmo.fetch_live_overlay(FakeAdapter(), force=True)
        self.assertIn("111", overlay)
        self.assertNotIn("222", overlay)
        live = overlay["111"]
        self.assertEqual(live["live_last_price"], 1000.0)
        self.assertEqual(live["live_close_price"], 990.0)
        self.assertEqual(live["live_change_pct"], 5.26)
        self.assertEqual(live["live_time"], "12:15:00")
        self.assertEqual(live["live_symbol"], "ومعلم")

    def test_session_state_non_trading_day(self):
        import datetime as dt
        from zoneinfo import ZoneInfo
        thu = dt.datetime(2026, 10, 15, 15, 0, tzinfo=ZoneInfo("Asia/Tehran"))
        self.assertEqual(lmo.session_state(thu), "NON_TRADING_DAY")
        sun_pre = dt.datetime(2026, 10, 18, 7, 30, tzinfo=ZoneInfo("Asia/Tehran"))
        self.assertEqual(lmo.session_state(sun_pre), "PRE_OPEN")
        sun_open = dt.datetime(2026, 10, 18, 10, 0, tzinfo=ZoneInfo("Asia/Tehran"))
        self.assertEqual(lmo.session_state(sun_open), "OPEN")
        sun_post = dt.datetime(2026, 10, 18, 14, 0, tzinfo=ZoneInfo("Asia/Tehran"))
        self.assertEqual(lmo.session_state(sun_post), "CLOSED_TODAY")

    def test_no_overlay_before_open_or_non_trading(self):
        with patch.object(lmo, "session_state", return_value="PRE_OPEN"):
            self.assertIsNone(lmo.fetch_live_overlay(force=True))
        with patch.object(lmo, "session_state", return_value="NON_TRADING_DAY"):
            self.assertIsNone(lmo.fetch_live_overlay(force=True))


if __name__ == "__main__":
    unittest.main()
