import unittest

from tsetmc_eligibility import (
    INSUFFICIENT_ACTIVITY_EVIDENCE,
    OPPORTUNITY_CANDIDATE,
    RANKABLE,
    build_opportunity_candidates,
    classify_eligibility,
    classify_universe,
)


def row(volume=None, trades=None, bid=None, ask=None):
    return {
        "canonical": {
            "نماد": "TEST",
            "حجم معاملات": volume,
            "تعداد معاملات": trades,
            "حجم بهترین تقاضا": bid,
            "حجم بهترین عرضه": ask,
        },
        "identity": {"instrument_id": "ID1", "contract_type": "CALL"},
    }


class TsetmcEligibilityTests(unittest.TestCase):
    def test_zero_volume_and_trades_cannot_be_candidate(self):
        result = classify_eligibility(row(volume=0, trades=0, bid=None, ask=None))
        self.assertEqual(result["state"], INSUFFICIENT_ACTIVITY_EVIDENCE)
        self.assertFalse(result["opportunity_eligible"])

    def test_missing_activity_is_not_zero_filled(self):
        result = classify_eligibility(row())
        self.assertEqual(result["state"], INSUFFICIENT_ACTIVITY_EVIDENCE)
        self.assertIsNone(result["activity"]["volume"])
        self.assertIsNone(result["activity"]["trade_count"])

    def test_traded_contract_can_be_candidate(self):
        result = classify_eligibility(row(volume=100, trades=2))
        self.assertEqual(result["state"], OPPORTUNITY_CANDIDATE)

    def test_two_sided_depth_can_be_candidate(self):
        result = classify_eligibility(row(volume=0, trades=0, bid=5, ask=7))
        self.assertEqual(result["state"], OPPORTUNITY_CANDIDATE)

    def test_one_sided_depth_is_not_candidate_by_itself(self):
        result = classify_eligibility(row(volume=0, trades=0, bid=5, ask=0))
        self.assertEqual(result["state"], INSUFFICIENT_ACTIVITY_EVIDENCE)

    def test_nonzero_activity_but_missing_trade_count_is_rankable(self):
        result = classify_eligibility(row(volume=100, trades=None))
        self.assertEqual(result["state"], RANKABLE)

    def test_universe_counts_cover_every_row(self):
        result = classify_universe([
            row(volume=0, trades=0),
            row(volume=10, trades=1),
            row(volume=None, trades=None),
        ])
        self.assertEqual(result["rows_evaluated"], 3)
        self.assertEqual(
            sum(result["counts"].values()),
            3,
        )
        self.assertFalse(result["arbitrary_thresholds"])

    def test_oi_status_classifies_positive_zero_and_unavailable(self):
        positive = row(volume=1, trades=1)
        positive["canonical"]["موقعیت های باز"] = 12
        zero = row(volume=1, trades=1)
        zero["canonical"]["موقعیت های باز"] = 0
        unavailable = row(volume=1, trades=1)

        self.assertEqual(classify_eligibility(positive)["activity"]["oi_status"], "POSITIVE")
        self.assertEqual(classify_eligibility(zero)["activity"]["oi_status"], "ZERO")
        self.assertEqual(classify_eligibility(unavailable)["activity"]["oi_status"], "UNAVAILABLE")

    def test_spread_status_classifies_positive_zero_negative_and_unavailable(self):
        positive = row(volume=1, trades=1, bid=10, ask=12)
        zero = row(volume=1, trades=1, bid=10, ask=10)
        negative = row(volume=1, trades=1, bid=12, ask=10)
        unavailable = row(volume=1, trades=1, bid=None, ask=None)
        one_sided = row(volume=1, trades=1, bid=12, ask=0)
        zero_both = row(volume=1, trades=1, bid=0, ask=0)

        self.assertEqual(classify_eligibility(positive)["activity"]["spread_status"], "POSITIVE")
        self.assertEqual(classify_eligibility(zero)["activity"]["spread_status"], "ZERO")
        self.assertEqual(classify_eligibility(negative)["activity"]["spread_status"], "NEGATIVE")
        self.assertEqual(classify_eligibility(unavailable)["activity"]["spread_status"], "UNAVAILABLE")
        self.assertEqual(classify_eligibility(one_sided)["activity"]["spread_status"], "UNAVAILABLE")
        self.assertIsNone(classify_eligibility(one_sided)["activity"]["spread"])
        self.assertEqual(classify_eligibility(zero_both)["activity"]["spread_status"], "UNAVAILABLE")

    def test_oi_and_spread_status_do_not_change_candidate_gate(self):
        positive = row(volume=1, trades=1, bid=10, ask=12)
        inverted = row(volume=1, trades=1, bid=12, ask=10)
        for candidate in (positive, inverted):
            result = classify_eligibility(candidate)
            self.assertEqual(result["state"], OPPORTUNITY_CANDIDATE)
            self.assertTrue(result["opportunity_eligible"])
            self.assertFalse(result["buy_sell_signal"])

    def test_universe_exposes_oi_and_spread_status_counts(self):
        positive = row(volume=1, trades=1, bid=10, ask=12)
        positive["canonical"]["موقعیت های باز"] = 5
        zero = row(volume=1, trades=1, bid=10, ask=10)
        zero["canonical"]["موقعیت های باز"] = 0
        negative = row(volume=1, trades=1, bid=12, ask=10)
        unavailable = row(volume=1, trades=1, bid=None, ask=None)
        one_sided = row(volume=1, trades=1, bid=12, ask=0)

        result = classify_universe([positive, zero, negative, unavailable, one_sided])
        self.assertEqual(result["rows_evaluated"], 5)
        self.assertEqual(result["counts"][OPPORTUNITY_CANDIDATE], 4)
        items = result["items"]
        self.assertEqual(sum(
            item["activity"]["oi_status"] == "POSITIVE" for item in items
        ), 1)
        self.assertEqual(sum(
            item["activity"]["oi_status"] == "ZERO" for item in items
        ), 1)
        self.assertEqual(sum(
            item["activity"]["oi_status"] == "UNAVAILABLE" for item in items
        ), 2)
        self.assertEqual(sum(
            item["activity"]["spread_status"] == "POSITIVE" for item in items
        ), 1)
        self.assertEqual(sum(
            item["activity"]["spread_status"] == "ZERO" for item in items
        ), 1)
        self.assertEqual(sum(
            item["activity"]["spread_status"] == "NEGATIVE" for item in items
        ), 1)
        self.assertEqual(sum(
            item["activity"]["spread_status"] == "UNAVAILABLE" for item in items
        ), 2)

    def test_no_trade_semantics_are_generated(self):
        result = classify_eligibility(row(volume=10, trades=1))
        self.assertFalse(result["buy_sell_signal"])


    def test_opportunity_candidates_use_only_eligible_rows(self):
        rows = [row(volume=10, trades=1), row(volume=0, trades=0)]
        rows[0]["identity"]["instrument_id"] = "ID1"
        rows[0]["canonical"]["نماد"] = "ACTIVE"
        rows[1]["identity"]["instrument_id"] = "ID2"
        rows[1]["canonical"]["نماد"] = "INACTIVE"
        eligibility = classify_universe(rows)
        ranking = {
            "ranking_rows": [
                {"instrument_id": "ID1", "rank": 1, "score": 80.0,
                 "supported_blocks": ["LIQUIDITY"], "features": {"contract_type": "CALL"}},
                {"instrument_id": "ID2", "rank": 2, "score": 90.0,
                 "supported_blocks": ["LIQUIDITY"], "features": {"contract_type": "CALL"}},
            ]
        }
        result = build_opportunity_candidates(rows, ranking, eligibility)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["cases"][0]["instrument_id"], "ID1")
        self.assertFalse(result["cases"][0]["buy_sell_signal"])

    def test_opportunity_engine_has_no_new_profitability_threshold(self):
        r = row(volume=10, trades=1)
        result = build_opportunity_candidates(
            [r], {"ranking_rows": []}, classify_universe([r])
        )
        self.assertFalse(result["rules"]["new_profitability_threshold"])
        self.assertEqual(result["rules"]["buy_sell_signal"], "NOT_GENERATED")


if __name__ == "__main__":
    unittest.main()
