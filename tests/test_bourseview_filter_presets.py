import unittest

from bourseview_filter_presets import (
    FILTER_PRESETS,
    evaluate_bourseview_preset,
    list_bourseview_presets,
)


class BourseViewPresetTests(unittest.TestCase):
    def test_catalog_has_eight_public_presets(self):
        items = list_bourseview_presets()
        self.assertEqual(len(items), 8)
        self.assertEqual(len(FILTER_PRESETS), 8)
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

    def test_unknown_preset_is_invalid(self):
        result = evaluate_bourseview_preset("BV-UNKNOWN", {})
        self.assertEqual(result["status"], "INVALID_PRESET")

    def test_high_percent_200d_does_not_use_20_day_feature(self):
        rules = FILTER_PRESETS["BV-F08"]["rules"]
        self.assertIn("high_percent_200d", [rule["field"] for rule in rules])
        self.assertNotIn("range_position_20", [rule["field"] for rule in rules])


if __name__ == "__main__":
    unittest.main()
