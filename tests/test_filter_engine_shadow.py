import unittest

from filter_engine_shadow import evaluate_filter, evaluate_rule


class FilterEngineTests(unittest.TestCase):
    def test_explicit_rule_matches_nested_feature(self):
        record = {"features": {"close_vs_sma_5_relation": "ABOVE"}}
        result = evaluate_rule(
            record,
            {"field": "features.close_vs_sma_5_relation", "operator": "EQ", "value": "ABOVE"},
        )
        self.assertEqual(result["status"], "MATCH")

    def test_missing_input_is_not_false_zero(self):
        result = evaluate_rule(
            {},
            {"field": "features.close_vs_sma_5_pct", "operator": "GT", "value": 0},
        )
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")

    def test_all_and_any_are_explicit(self):
        record = {"a": 3, "b": "UP"}
        rules = [
            {"field": "a", "operator": "GTE", "value": 3},
            {"field": "b", "operator": "EQ", "value": "UP"},
        ]
        self.assertEqual(evaluate_filter(record, rules, mode="ALL")["status"], "MATCH")
        self.assertEqual(evaluate_filter(record, rules, mode="ANY")["status"], "MATCH")

    def test_unsupported_operator_is_invalid(self):
        result = evaluate_rule({"a": 1}, {"field": "a", "operator": "RANDOM", "value": 1})
        self.assertEqual(result["status"], "INVALID_RULE")


if __name__ == "__main__":
    unittest.main()
