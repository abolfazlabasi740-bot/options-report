import unittest

from attention_allocation_shadow import allocate_attention


class AttentionAllocationTests(unittest.TestCase):
    def test_red_team_takes_priority_over_other_routes(self):
        case = {"case_id": "C1", "symbol": "ضتست1", "status": "CONFIRMED"}
        result = allocate_attention(
            [case],
            red_team={"cases": [{"case_id": "C1", "challenges": [{"code": "X"}]}]},
        )
        self.assertEqual(result["allocations"][0]["route"], "RED_TEAM_REVIEW")

    def test_confirmed_case_with_history_routes_to_cross_snapshot_review(self):
        case = {"case_id": "C1", "symbol": "ضتست1", "status": "CONFIRMED"}
        patterns = {"patterns": [{"identity": "ضتست1", "type": "FINALSCORE_UP_SEQUENCE"}]}
        result = allocate_attention([case], historical_patterns=patterns)
        self.assertEqual(result["allocations"][0]["route"], "CROSS_SNAPSHOT_REVIEW")

    def test_missing_data_is_not_treated_as_rejected(self):
        case = {"case_id": "C1", "symbol": "ضتست1", "status": "INSUFFICIENT_DATA"}
        result = allocate_attention([case])
        self.assertEqual(result["allocations"][0]["route"], "DATA_COMPLETION")


if __name__ == "__main__":
    unittest.main()
