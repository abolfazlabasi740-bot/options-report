import json
import tempfile
import unittest
from pathlib import Path

from signal_replay_engine import (
    build_replay_observations,
    calibrate_rule_candidates,
    build_replay_calibration,
)


class SignalReplayCalibrationTests(unittest.TestCase):
    def _write_snapshot(self, root, sha, obs, price, underlying=100):
        path = root / "output" / "history" / "tsetmc"
        path.mkdir(parents=True, exist_ok=True)
        payload = {
            "source_of_truth": "TSETMC",
            "snapshot_sha256": sha,
            "generated_at": obs,
            "observation_retrieved_at": obs,
            "rows": [{
                "identity": {
                    "instrument_id": "1",
                    "contract_type": "CALL",
                },
                "canonical": {
                    "نماد": "TEST",
                    "آخرین قیمت": price,
                    "قیمت پایانی": price,
                    "قیمت سهم پایه": underlying,
                    "قیمت اعمال": 100,
                    "حجم معاملات": 1000,
                    "ارزش معاملات": 100000,
                    "تاریخ سررسید": "20261007",
                    "تاریخ": "20260926",
                },
            }],
        }
        (path / f"{sha}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def test_exact_id_replay_and_observed_return(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write_snapshot(root, "a", "2026-09-26T09:30:00+00:00", 10)
            self._write_snapshot(root, "b", "2026-09-26T10:00:00+00:00", 12)
            rows = build_replay_observations(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["instrument_id"], "1")
            self.assertAlmostEqual(rows[0]["option_return_pct"], 0.2)
            self.assertEqual(rows[0]["observed_outcome"], "POSITIVE_OPTION_RETURN")

    def test_missing_values_are_excluded_not_zero_filled(self):
        observations = [{
            "option_return_pct": 0.1,
            "entry_features": {
                "time_value_ratio": None,
                "breakeven_distance": 0.1,
            },
        }]
        rules = calibrate_rule_candidates(observations)
        self.assertTrue(rules)
        self.assertFalse(any(r["feature"] == "time_value_ratio" for r in rules))

    def test_thresholds_are_empirical_and_signal_generation_forbidden(self):
        observations = []
        for i, value in enumerate([0.01, 0.02, 0.03, 0.04]):
            observations.append({
                "option_return_pct": [0.10, 0.05, -0.02, -0.05][i],
                "entry_features": {"time_value_ratio": value},
            })
        rules = calibrate_rule_candidates(observations)
        tvr = [r for r in rules if r["feature"] == "time_value_ratio"]
        self.assertTrue(tvr)
        self.assertTrue(all(r["threshold_source"] in {"P25", "P50", "P75"} for r in tvr))

    def test_runtime_output_is_deterministic_and_binds_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write_snapshot(root, "a", "2026-09-26T09:30:00+00:00", 10)
            self._write_snapshot(root, "b", "2026-09-26T10:00:00+00:00", 11)
            a = build_replay_calibration(root)
            b = build_replay_calibration(root)
            self.assertEqual(a, b)
            self.assertEqual(a["source_of_truth"], "TSETMC")
            self.assertEqual(a["rules"]["signal_generation"], "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
