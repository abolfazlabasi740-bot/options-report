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


if __name__ == "__main__":
    unittest.main()
