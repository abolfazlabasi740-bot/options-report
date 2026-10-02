import unittest

from economic_validation_evidence_builder import _case_family_diagnostics


class CaseFamilyDiagnosticsTests(unittest.TestCase):
    def test_confusion_counts_use_independent_forward_labels(self):
        observations = []
        rows = [
            (0.01, 100, 10, 1, "OBSERVED_CONFIRMED", True, False),
            (0.02, 200, 20, 2, "OBSERVED_NOT_CONFIRMED", True, False),
            (0.03, 300, 30, 3, "OBSERVED_CONFIRMED", False, True),
            (0.04, 400, 40, 4, "OBSERVED_NOT_CONFIRMED", True, True),
        ]
        for be, value, volume, days, label, context, pair in rows:
            observations.append({
                "entry_snapshot_sha256": "snapshot-a",
                "outcome_label": label,
                "entry_features": {
                    "breakeven_distance": be,
                    "trade_value": value,
                    "volume": volume,
                    "calendar_days": days,
                    "base_breakeven_context_available": context,
                    "call_put_pair_available": pair,
                },
            })

        result = _case_family_diagnostics(observations)
        families = result["supported_case_families"]
        self.assertEqual(families["BREAKEVEN_COMPRESSION_TSETMC_PROXY"]["confusion_counts"],
                         {"TP": 1, "FP": 0, "FN": 1, "TN": 2})
        self.assertEqual(families["LIQUIDITY_CONFIRMED_TSETMC_PROXY"]["confusion_counts"],
                         {"TP": 0, "FP": 1, "FN": 2, "TN": 1})
        self.assertEqual(families["NEAR_EXPIRY_RISK_TSETMC"]["confusion_counts"],
                         {"TP": 1, "FP": 0, "FN": 1, "TN": 2})
        self.assertEqual(result["coverage_only_families"]["BASE_BREAKEVEN_CONTEXT_TSETMC"],
                         {"available": 3, "missing": 1})
        self.assertEqual(result["coverage_only_families"]["CALL_PUT_STRUCTURE_AVAILABLE_TSETMC"],
                         {"paired": 2, "not_paired_or_missing": 2})
        self.assertEqual(result["global_closure"], "VERIFIED")

    def test_missing_features_remain_unresolved(self):
        result = _case_family_diagnostics([{
            "entry_snapshot_sha256": "snapshot-b",
            "outcome_label": "UNRESOLVED",
            "entry_features": {},
        }])
        for details in result["supported_case_families"].values():
            self.assertEqual(details["evaluable_rows"], 0)
            self.assertEqual(details["unresolved_rows"], 1)


if __name__ == "__main__":
    unittest.main()
