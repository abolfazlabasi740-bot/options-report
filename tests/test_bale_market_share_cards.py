import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bale_market_share_cards as cards


class BaleMarketShareCardsTests(unittest.TestCase):
    def test_market_pages_have_ten_rows_and_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "market.json"
            rows = [
                {"symbol": f"SYM{i:02d}", "final_score": 100 - i, "classification": "A", "evidence_coverage_pct": 90}
                for i in range(25)
            ]
            report.write_text(json.dumps({
                "source_of_truth": "TSETMC",
                "generated_at": "2099-01-01T00:00:00+00:00",
                "latest_history_date": "20990101",
                "rows": rows,
            }), encoding="utf-8")
            with patch.object(cards, "REPORT_PATH", report):
                text, markup, count, page, total_pages = cards.render_page(0)
                self.assertEqual((count, page, total_pages), (25, 0, 3))
                self.assertIn("1. SYM00", text)
                self.assertIn("10. SYM09", text)
                self.assertNotIn("11. SYM10", text)
                self.assertEqual(markup["inline_keyboard"][0][0]["callback_data"], "market_shares_page:1")

                text, markup, count, page, total_pages = cards.render_page(2)
                self.assertIn("21. SYM20", text)
                callbacks = [button["callback_data"] for row in markup["inline_keyboard"] for button in row]
                self.assertIn("market_shares_page:1", callbacks)
                self.assertIn("main_menu", callbacks)

    def test_header_has_jalali_date_time_and_session_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "market.json"
            report.write_text(json.dumps({
                "source_of_truth": "TSETMC",
                "generated_at": "2099-01-01T10:00:00+03:30",
                "latest_history_date": "20990101",
                "latest_history_date_jalali": "1477/10/11",
                "rows": [{"symbol": "SYM", "final_score": 50, "classification": "A",
                          "evidence_coverage_pct": 90,
                          "early_move": {"breakout_above_prior_20_high": True,
                                          "pre_lock_sequence": {"state": "EARLY"}},
                          "range_position_20": 0.9, "atr_14_pct": 2.5,
                          "value_ratio_5_to_20": 1.7}],
            }), encoding="utf-8")
            with patch.object(cards, "REPORT_PATH", report):
                payload = cards._load_report()
                rendered, _, _, _, _ = cards.render_ranked_rows(payload, cards.ranked_rows(payload), 0)
                # Persian date header present
                self.assertIn("📅 تاریخ داده: 1477/10/11", rendered)
                # generation clock present
                self.assertIn("🕒 زمان بازسازی گزارش:", rendered)
                # session status line present (any of the four states)
                self.assertTrue(
                    "ساعت معاملات" in rendered
                    or "بستهٔ امروز" in rendered
                    or "قبل از باز شدن" in rendered
                    or "روز غیرمعاملاتی" in rendered
                )
                # enriched per-symbol evidence present
                self.assertIn("شکست سقف ۲۰ج", rendered)
                self.assertIn("موقعیت کانال 90%", rendered)
                self.assertIn("ATR 2.5%", rendered)

    def test_freshness_uses_history_date_not_wall_clock(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "market.json"
            old_date = (dt.date(dt.date.today().year, 1, 1) - dt.timedelta(days=400)).strftime("%Y%m%d")
            report.write_text(json.dumps({
                "source_of_truth": "TSETMC",
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "latest_history_date": old_date,
                "rows": [],
            }), encoding="utf-8")
            with patch.object(cards, "REPORT_PATH", report):
                payload = cards._load_report()
                # Stale data date => not fresh even though generated_at is now.
                self.assertFalse(cards._report_is_fresh(payload))
                # Fresh data date + recent generated_at => fresh.
                now = dt.datetime.now(cards.TEHRAN)
                cutoff = now.date() if now.time() >= dt.time(13, 30) else now.date() - dt.timedelta(days=1)
                fresh_date = cards._previous_trading_day(cutoff).strftime("%Y%m%d")
                payload["latest_history_date"] = fresh_date
                self.assertTrue(cards._report_is_fresh(payload))


if __name__ == "__main__":
    unittest.main()
