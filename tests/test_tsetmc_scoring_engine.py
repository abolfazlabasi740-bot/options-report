import unittest

from tsetmc_scoring_engine import build_evidence_ranking


class TsetmcEvidenceRankingTests(unittest.TestCase):
    def _row(self, symbol, S, K, P, close, volume, value, days, typ="CALL"):
        return {
            "canonical": {
                "نماد": symbol,
                "قیمت سهم پایه": S,
                "قیمت اعمال": K,
                "آخرین قیمت": P,
                "قیمت پایانی": close,
                "حجم معاملات": volume,
                "ارزش معاملات": value,
                "روزهای تقویمی": days,
                "بیشترین قیمت": (P * 1.05) if P is not None else None,
                "کمترین قیمت": (P * 0.95) if P is not None else None,
            },
            "identity": {
                "instrument_id": symbol,
                "contract_type": typ,
            },
        }

    def test_uses_only_tsetmc_derived_features_and_ranks(self):
        rows = [
            self._row("A", 100, 90, 12, 12, 1000, 12000, 20),
            self._row("B", 100, 100, 20, 20, 100, 2000, 20),
            self._row("C", 100, 110, 8, 8, 500, 4000, 20),
        ]
        result = build_evidence_ranking(rows)
        self.assertEqual(result["mode"], "TSETMC_EVIDENCE_RANKING")
        self.assertEqual(result["source_of_truth"], "TSETMC")
        self.assertEqual(result["ranking_scope"], "OPPORTUNITY_CANDIDATES")
        self.assertEqual(result["ranking_scope_row_count"], 3)
        self.assertNotEqual(result["status"], "NO_RANKABLE_EVIDENCE")
        self.assertTrue(all(x["score"] is not None for x in result["ranking_rows"]))

    def test_missing_values_are_not_zero(self):
        row = self._row("M", 100, 100, None, None, None, None, None)
        result = build_evidence_ranking([row])
        item = result["ranking_rows"][0]
        self.assertIsNone(item["features"]["trade_value"])
        self.assertIsNone(item["features"]["time_value"])
        self.assertIsNone(item["score"])

    def test_greeks_and_iv_are_never_fabricated(self):
        row = self._row("G", 100, 100, 10, 10, 100, 1000, 20)
        result = build_evidence_ranking([row])
        item = result["ranking_rows"][0]
        self.assertIn("GREEKS", item["unavailable_blocks"])
        self.assertEqual(result["rules"]["iv"], "NOT_COMPUTED")
        self.assertEqual(result["rules"]["greeks"], "NOT_COMPUTED")


    def test_call_feature_derivations_are_deterministic(self):
        row = self._row("C1", 100, 90, 15, 14, 100, 1000, 20, "CALL")
        item = build_evidence_ranking([row])["ranking_rows"][0]
        self.assertEqual(item["features"]["time_value"], 5.0)
        self.assertAlmostEqual(item["features"]["breakeven_distance"], 0.05)
        self.assertAlmostEqual(item["features"]["leverage"], 100 / 15)
        self.assertAlmostEqual(item["features"]["moneyness"], 1 / 9)
        self.assertAlmostEqual(item["features"]["last_vs_close"], 1 / 14)
        self.assertAlmostEqual(item["features"]["intraday_range"], 1.5 / 15)

    def test_put_feature_derivations_are_deterministic(self):
        row = self._row("P1", 100, 110, 15, 15, 100, 1000, 20, "PUT")
        item = build_evidence_ranking([row])["ranking_rows"][0]
        self.assertEqual(item["features"]["time_value"], 5.0)
        self.assertAlmostEqual(item["features"]["breakeven_distance"], 0.05)
        self.assertAlmostEqual(item["features"]["moneyness"], 1 / 11)

    def test_invalid_denominators_remain_unavailable(self):
        row = self._row("Z", 100, 100, 0, 0, 0, 0, None, "CALL")
        item = build_evidence_ranking([row])["ranking_rows"][0]
        self.assertIsNone(item["features"]["leverage"])
        self.assertIsNone(item["features"]["last_vs_close"])
        self.assertIsNone(item["features"]["intraday_range"])
        self.assertIsNone(item["features"]["calendar_days"])

    def test_missing_high_low_keeps_intraday_range_unavailable(self):
        row = self._row("R", 100, 100, 10, 10, 100, 1000, 20)
        row["canonical"]["بیشترین قیمت"] = None
        row["canonical"]["کمترین قیمت"] = None
        item = build_evidence_ranking([row])["ranking_rows"][0]
        self.assertIsNone(item["features"]["intraday_range"])

    def test_time_value_is_never_negative(self):
        row = self._row("TV", 100, 80, 10, 10, 100, 1000, 20, "CALL")
        item = build_evidence_ranking([row])["ranking_rows"][0]
        self.assertEqual(item["features"]["time_value"], 0.0)

    def test_valuation_uses_lower_premium_burden(self):
        rows = [
            self._row("CHEAP", 100, 100, 10, 10, 100, 1000, 20),
            self._row("EXPENSIVE", 100, 100, 20, 20, 100, 2000, 20),
        ]
        result = build_evidence_ranking(
            rows,
            disabled_blocks={"LIQUIDITY", "PAYOFF", "TIME", "GREEKS", "MARKET"},
        )
        by_id = {x["instrument_id"]: x for x in result["ranking_rows"]}
        self.assertAlmostEqual(by_id["CHEAP"]["features"]["time_value_ratio"], 0.10)
        self.assertAlmostEqual(by_id["EXPENSIVE"]["features"]["time_value_ratio"], 0.20)
        self.assertGreater(by_id["CHEAP"]["score"], by_id["EXPENSIVE"]["score"])

    def test_percentile_direction_is_deterministic(self):
        rows = [
            self._row("LOW", 100, 100, 10, 10, 10, 100, 20),
            self._row("HIGH", 100, 100, 20, 20, 100, 1000, 20),
        ]
        result = build_evidence_ranking(
            rows,
            disabled_blocks={"VALUATION", "PAYOFF", "TIME", "GREEKS", "MARKET"},
        )
        by_id = {x["instrument_id"]: x for x in result["ranking_rows"]}
        self.assertGreater(by_id["HIGH"]["features"]["trade_value"], by_id["LOW"]["features"]["trade_value"])
        self.assertGreater(by_id["HIGH"]["score"], by_id["LOW"]["score"])

    def test_calendar_days_direction_matches_established_time_policy(self):
        rows = [
            self._row("NEAR", 100, 100, 10, 10, 100, 1000, 2),
            self._row("FAR", 100, 100, 10, 10, 100, 1000, 20),
        ]
        result = build_evidence_ranking(
            rows,
            disabled_blocks={"LIQUIDITY", "VALUATION", "PAYOFF", "GREEKS", "MARKET"},
        )
        by_id = {x["instrument_id"]: x for x in result["ranking_rows"]}
        self.assertGreater(by_id["NEAR"]["score"], by_id["FAR"]["score"])

    def test_unavailable_factor_removes_only_its_block_for_that_row(self):
        rows = [
            self._row("A", 100, 100, 10, 10, 100, 1000, 20),
            self._row("B", 100, 100, None, None, 100, 1000, 20),
        ]
        result = build_evidence_ranking(rows)
        a = next(x for x in result["ranking_rows"] if x["instrument_id"] == "A")
        b = next(x for x in result["ranking_rows"] if x["instrument_id"] == "B")
        self.assertIsNone(b["features"]["time_value"])
        self.assertIsNone(b["block_scores"]["VALUATION"])
        self.assertIn("VALUATION", a["supported_blocks"])
        self.assertNotIn("VALUATION", b["supported_blocks"])


if __name__ == "__main__":
    unittest.main()
