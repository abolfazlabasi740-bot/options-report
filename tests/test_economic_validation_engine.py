import unittest

from economic_validation_engine import validate_walk_forward


class EconomicValidationTests(unittest.TestCase):
    def _rows(self):
        rows = []
        times = ["2026-09-26T09:30:00+00:00", "2026-09-26T10:00:00+00:00", "2026-09-26T10:30:00+00:00", "2026-09-26T11:00:00+00:00"]
        returns = [0.10, -0.05, 0.20, -0.02]
        values = [0.01, 0.02, 0.03, 0.04]
        for i, t in enumerate(times):
            rows.append({
                "instrument_id": str(i),
                "entry_observation_time": t,
                "option_return_pct": returns[i],
                "entry_features": {"time_value_ratio": values[i]},
            })
        return rows

    def test_walk_forward_never_uses_future_rows_for_threshold(self):
        result = validate_walk_forward(self._rows())
        self.assertEqual(result["method"]["split"], "CHRONOLOGICAL_WALK_FORWARD")
        self.assertEqual(result["entry_snapshot_count"], 4)
        self.assertEqual(result["validation_window_count"], 2)
        self.assertTrue(result["results"])
        first = [r for r in result["results"] if r["test_entry_snapshot"] == "2026-09-26T10:30:00+00:00" and r["threshold_source"] == "P50" and r["operator"] == "LE"][0]
        self.assertAlmostEqual(first["threshold"], 0.015)

    def test_signal_generation_is_forbidden(self):
        result = validate_walk_forward(self._rows())
        self.assertEqual(result["method"]["signal_generation"], "FORBIDDEN")
        self.assertEqual(result["source_of_truth"], "TSETMC")


if __name__ == "__main__":
    unittest.main()
