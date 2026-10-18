import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bale_option_market_cards as cards


def option_row(i, premium, volume, value, days=20, kind="CALL"):
    return {
        "canonical": {
            "نماد": f"OPT{i}",
            "قیمت اعمال": 100,
            "قیمت سهم پایه": 100,
            "تاریخ سررسید": "20990120",
            "روزهای تقویمی": days,
            "آخرین قیمت": premium,
            "قیمت پایانی": premium,
            "حجم معاملات": volume,
            "ارزش معاملات": value,
            "تعداد معاملات": 10,
            "بیشترین قیمت": premium * 1.1,
            "کمترین قیمت": premium * 0.9,
        },
        "identity": {
            "instrument_id": f"I{i}",
            "underlying_id": f"U{i}",
            "underlying_symbol": f"BASE{i}",
            "contract_type": kind,
        },
    }


class BaleOptionMarketCardsTests(unittest.TestCase):
    def test_uses_six_block_ranker_and_exactly_eleven_columns(self):
        snapshot = {
            "source_of_truth": "TSETMC",
            "generated_at": "2099-01-01T00:00:00+00:00",
            "data_mode": "LIVE_TSETMC_REFRESH",
            "snapshot_sha256": "s" * 64,
            "rows": [option_row(1, 10, 1000, 10000), option_row(2, 20, 10, 100)],
        }
        payload = cards.rank_snapshot(snapshot)
        self.assertEqual(payload["mode"], "TSETMC_EVIDENCE_RANKING")
        self.assertEqual(len(payload["columns"]), 11)
        self.assertEqual(tuple(payload["columns"]), cards.OPTION_COLUMNS)
        self.assertEqual(len(payload["rows"]), 2)
        self.assertTrue(all(row["امتیاز شش‌بلوک"] is not None for row in payload["rows"]))
        self.assertIn("LIQUIDITY", payload["rows"][0]["block_scores"])

    def test_pages_have_ten_rows_and_option_market_callbacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "option_market.json"
            rows = [
                {"نماد": f"O{i:02d}", "نوع قرارداد": "CALL", "سهم پایه": f"B{i:02d}",
                 "اعمال": 100, "آخرین قیمت": 10, "قیمت سهم پایه": 100,
                 "سربه‌سر": 110, "فاصله سربه‌سر": 10, "تاریخ سررسید": "20990120",
                 "روزهای باقی‌مانده": 20, "امتیاز شش‌بلوک": 90 - i, "block_scores": {}}
                for i in range(23)
            ]
            report.write_text(json.dumps({"source_of_truth": "TSETMC", "columns": list(cards.OPTION_COLUMNS), "rows": rows}), encoding="utf-8")
            with patch.object(cards, "REPORT_PATH", report):
                text, markup, count, page, total = cards.render_page(1)
            self.assertEqual((count, page, total), (23, 1, 3))
            self.assertIn("11. O10", text)
            callbacks = [button["callback_data"] for row in markup["inline_keyboard"] for button in row]
            self.assertIn("option_market_page:0", callbacks)
            self.assertIn("option_market_page:2", callbacks)


if __name__ == "__main__":
    unittest.main()
