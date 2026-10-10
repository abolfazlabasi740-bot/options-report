import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bale_base_share_option_cards as cards


class BaleOptionShareCardsTests(unittest.TestCase):
    def test_filters_market_ranking_preserves_score_and_re_numbers(self):
        market_rows = [
            {"symbol": "TOP", "instrument_id": "M1", "final_score": 99},
            {"symbol": "SHASTA", "instrument_id": "M2", "final_score": 88},
            {"symbol": "OTHER", "instrument_id": "M3", "final_score": 77},
            {"symbol": "FOLD", "instrument_id": "M4", "final_score": 66},
        ]
        snapshot = {
            "source_of_truth": "TSETMC",
            "generated_at": "2099-01-01T00:00:00+00:00",
            "data_mode": "LIVE_TSETMC_REFRESH",
            "snapshot_sha256": "a" * 64,
            "rows": [
                {"identity": {"underlying_id": "M2", "underlying_symbol": "SHASTA"}},
                {"identity": {"underlying_id": "M4", "underlying_symbol": "FOLD"}},
            ],
        }
        base = {"source_of_truth": "TSETMC", "rows": market_rows}
        with patch.object(cards.market, "ranked_rows", return_value=market_rows):
            rows = cards.filter_market_rows(base, snapshot)
        self.assertEqual([row["symbol"] for row in rows], ["SHASTA", "FOLD"])
        self.assertEqual([row["market_rank"] for row in rows], [2, 4])
        self.assertEqual([row["final_score"] for row in rows], [88, 66])

    def test_explicit_underlying_id_does_not_accept_same_symbol_with_wrong_id(self):
        base = {"source_of_truth": "TSETMC", "rows": [{"symbol": "SHASTA", "instrument_id": "WRONG", "final_score": 88}]}
        snapshot = {"source_of_truth": "TSETMC", "rows": [{"identity": {"underlying_id": "RIGHT", "underlying_symbol": "SHASTA"}}]}
        with patch.object(cards.market, "ranked_rows", return_value=base["rows"]):
            self.assertEqual(cards.filter_market_rows(base, snapshot), [])

    def test_render_uses_ten_rows_and_option_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "option.json"
            rows = [{"symbol": f"S{i:02d}", "final_score": 100 - i, "market_rank": i + 1} for i in range(26)]
            report.write_text(json.dumps({"source_of_truth": "TSETMC", "rows": rows}), encoding="utf-8")
            with patch.object(cards, "REPORT_PATH", report):
                text, markup, count, page, total = cards.render_page(1)
            self.assertEqual((count, page, total), (26, 1, 3))
            self.assertIn("11. S10", text)
            self.assertIn("market_rank=11", text)
            callbacks = [button["callback_data"] for row in markup["inline_keyboard"] for button in row]
            self.assertIn("option_shares_page:0", callbacks)
            self.assertIn("option_shares_page:2", callbacks)


if __name__ == "__main__":
    unittest.main()
