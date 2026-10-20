import unittest

from bourseview_filter_presets import (
    FILTER_PRESETS,
    evaluate_bourseview_preset,
    list_bourseview_presets,
)


class BourseViewPresetTests(unittest.TestCase):
    def test_catalog_has_ten_public_presets(self):
        items = list_bourseview_presets()
        self.assertEqual(len(items), 10)
        self.assertEqual(len(FILTER_PRESETS), 10)
        self.assertTrue(all(x["production_gate"] == "OFF" for x in items))

    def test_unusual_value_requires_both_conditions(self):
        record = {
            "today_value_to_avg_traded_value_30_sessions_ratio": 5.1,
            "avg_traded_value_30_sessions_irr": 10_000_000_001,
        }
        self.assertEqual(evaluate_bourseview_preset("BV-F01", record)["status"], "MATCH")
        record["today_value_to_avg_traded_value_30_sessions_ratio"] = 5.0
        self.assertEqual(evaluate_bourseview_preset("BV-F01", record)["status"], "NO_MATCH")

    def test_missing_input_fails_closed(self):
        result = evaluate_bourseview_preset("BV-F07", {"rsi_14": 25})
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertFalse(result["matched"])
        self.assertFalse(result["data_freshness_checked"])

    def test_rsi_screen_matches_only_when_both_conditions_pass(self):
        record = {"rsi_14": 29.9, "avg_value_30d_irr": 30_000_000_001}
        self.assertEqual(evaluate_bourseview_preset("BV-F07", record)["status"], "MATCH")
        record["rsi_14"] = 30
        self.assertEqual(evaluate_bourseview_preset("BV-F07", record)["status"], "NO_MATCH")

    def test_p_nav_requires_investment_company_and_trade(self):
        record = {"is_investment_company": True, "traded_today": True, "p_nav": 0.9}
        self.assertEqual(evaluate_bourseview_preset("BV-F02", record)["status"], "MATCH")
        record["traded_today"] = False
        self.assertEqual(evaluate_bourseview_preset("BV-F02", record)["status"], "NO_MATCH")

    def test_monthly_revenue_filter_uses_distinct_differences(self):
        record = {
            "revenue_growth_1m_minus_arithmetic_avg_growth_3m_pct": 2.0,
            "revenue_growth_1m_minus_growth_1y_pct": 1.0,
            "avg_value_30d_irr": 30_000_000_001,
            "revenue_arithmetic_average_growth_rate_3m_pct": 0.1,
        }
        self.assertEqual(evaluate_bourseview_preset("BV-F03", record)["status"], "MATCH")
        record["revenue_growth_1m_minus_growth_1y_pct"] = 0
        self.assertEqual(evaluate_bourseview_preset("BV-F03", record)["status"], "NO_MATCH")

    def test_quarterly_revenue_growth_screen(self):
        record = {
            "revenue_growth_rate_qoq_pct": 10.1,
            "revenue_growth_rate_yoy_pct": 100.1,
            "avg_value_30d_irr": 30_000_000_001,
        }
        self.assertEqual(evaluate_bourseview_preset("BV-F04", record)["status"], "MATCH")
        record["revenue_growth_rate_yoy_pct"] = 100
        self.assertEqual(evaluate_bourseview_preset("BV-F04", record)["status"], "NO_MATCH")

    def test_operating_margin_screen(self):
        record = {
            "operating_profit_margin_mrq_growth_rate_qoq_pct": 0.1,
            "operating_profit_margin_mrq_growth_rate_yoy_pct": 0.2,
            "avg_value_30d_irr": 30_000_000_001,
            "operating_profit_margin_ttm_pct": 30.1,
        }
        self.assertEqual(evaluate_bourseview_preset("BV-F05", record)["status"], "MATCH")
        record["operating_profit_margin_ttm_pct"] = 30
        self.assertEqual(evaluate_bourseview_preset("BV-F05", record)["status"], "NO_MATCH")

    def test_monthly_ps_screen(self):
        record = {
            "revenue_year_to_year_growth_rate_1m_pct": 40.1,
            "revenue_growth_1m_minus_growth_3m_pct": 0.1,
            "revenue_growth_1m_minus_growth_1y_pct": 0.1,
            "p_to_s_monthly": 2.49,
            "avg_value_30d_irr": 10_000_000_001,
        }
        self.assertEqual(evaluate_bourseview_preset("BV-F06", record)["status"], "MATCH")
        record["p_to_s_monthly"] = 2.5
        self.assertEqual(evaluate_bourseview_preset("BV-F06", record)["status"], "NO_MATCH")

    def test_low_pe_growth_screen_uses_documented_description_thresholds(self):
        record = {
            "p_to_e_ttm": 7.9,
            "revenue_growth_1m_pct": 11,
            "revenue_growth_3m_pct": 12,
            "revenue_growth_5m_pct": 13,
            "revenue_yoy_growth_1m_pct": 14,
        }
        result = evaluate_bourseview_preset("BV-F09", record)
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["provenance"], "PUBLICLY_DESCRIBED_SCREEN_RULE_DETAILS_PARTIAL")

    def test_low_pe_interest_coverage_is_risk_screen(self):
        record = {"p_to_e_ttm": 7.5, "interest_coverage_ratio": 2.9}
        self.assertEqual(evaluate_bourseview_preset("BV-F10", record)["status"], "MATCH")
        record["interest_coverage_ratio"] = 3.0
        self.assertEqual(evaluate_bourseview_preset("BV-F10", record)["status"], "NO_MATCH")

    def test_unknown_preset_is_invalid(self):
        result = evaluate_bourseview_preset("BV-UNKNOWN", {})
        self.assertEqual(result["status"], "INVALID_PRESET")

    def test_high_percent_200d_does_not_use_20_day_feature(self):
        rules = FILTER_PRESETS["BV-F08"]["rules"]
        self.assertIn("high_percent_200d", [rule["field"] for rule in rules])
        self.assertNotIn("range_position_20", [rule["field"] for rule in rules])


if __name__ == "__main__":
    unittest.main()
