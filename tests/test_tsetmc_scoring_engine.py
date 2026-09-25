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


if __name__ == "__main__":
    unittest.main()
