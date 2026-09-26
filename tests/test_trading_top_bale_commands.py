import unittest
from unittest.mock import patch

import bale_listener
import report_engine


class TradingTopReportTests(unittest.TestCase):
    def test_trading_rank_uses_explicit_trade_value_then_volume_and_count(self):
        rows = [
            {
                "identity": {"instrument_id": "A", "underlying_symbol": "وبملت"},
                "canonical": {"ارزش معاملات": 100, "حجم معاملات": 900, "تعداد معاملات": 2},
            },
            {
                "identity": {"instrument_id": "B", "underlying_symbol": "وبملت"},
                "canonical": {"ارزش معاملات": 200, "حجم معاملات": 100, "تعداد معاملات": 1},
            },
            {
                "identity": {"instrument_id": "C", "underlying_symbol": "وبملت"},
                "canonical": {"ارزش معاملات": 200, "حجم معاملات": 200, "تعداد معاملات": 1},
            },
        ]
        ranked = report_engine._trading_rank_rows(rows)
        self.assertEqual([r["identity"]["instrument_id"] for r in ranked], ["C", "B", "A"])

    def test_trading_rank_puts_missing_trade_value_after_observed_values(self):
        rows = [
            {
                "identity": {"instrument_id": "M"},
                "canonical": {"ارزش معاملات": None, "حجم معاملات": 9999, "تعداد معاملات": 99},
            },
            {
                "identity": {"instrument_id": "V"},
                "canonical": {"ارزش معاملات": 1, "حجم معاملات": 1, "تعداد معاملات": 1},
            },
        ]
        ranked = report_engine._trading_rank_rows(rows)
        self.assertEqual([r["identity"]["instrument_id"] for r in ranked], ["V", "M"])

    def test_bale_generate_report_uses_underlying_symbol_for_symbol_command(self):
        with patch.object(
            bale_listener,
            "build_tsetmc_report",
            return_value=("REPORT", {"report_mode": "RANKED"}),
        ) as builder, patch.object(
            bale_listener,
            "save_tsetmc_report",
        ):
            result = bale_listener.generate_report("وبملت")
        self.assertEqual(result, "REPORT")
        builder.assert_called_once_with(
            top_count=5,
            underlying_symbol="وبملت",
            flow=None,
            report_mode="RANKED",
        )

    def test_bale_generate_report_uses_six_block_ranking_for_report_command(self):
        with patch.object(
            bale_listener,
            "build_tsetmc_report",
            return_value=("REPORT", {"report_mode": "RANKED"}),
        ) as builder, patch.object(
            bale_listener,
            "save_tsetmc_report",
        ):
            result = bale_listener.generate_report("گزارش")
        self.assertEqual(result, "REPORT")
        builder.assert_called_once_with(
            top_count=15,
            flow=None,
            report_mode="RANKED",
        )

    def test_bale_generate_report_uses_trading_activity_only_for_explicit_activity_command(self):
        with patch.object(
            bale_listener,
            "build_tsetmc_report",
            return_value=("REPORT", {"report_mode": "TRADING_ACTIVITY"}),
        ) as builder, patch.object(
            bale_listener,
            "save_tsetmc_report",
        ):
            result = bale_listener.generate_report("فعالیت")
        self.assertEqual(result, "REPORT")
        builder.assert_called_once_with(
            top_count=15,
            flow=None,
            report_mode="TRADING_ACTIVITY",
        )


if __name__ == "__main__":
    unittest.main()
