import json
import tempfile
import unittest
from pathlib import Path

from tsetmc_outcome_engine import build_observed_outcomes


class TsetmcOutcomeTests(unittest.TestCase):
    def _write(self, root, sha, generated_at, rows):
        path = root / "output" / "history" / "tsetmc" / f"{sha}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "archive_version": "TSETMC-HISTORY-1.0",
            "source_of_truth": "TSETMC",
            "snapshot_sha256": sha,
            "generated_at": generated_at,
            "rows": rows,
        }), encoding="utf-8")

    def test_matches_only_exact_instrument_id_and_observes_change(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write(root, "sha1", "2026-09-26T10:00:00+00:00", [{
                "identity": {"instrument_id": "100", "contract_type": "CALL", "underlying_symbol": "X"},
                "canonical": {"نماد": "X100", "آخرین قیمت": 100, "قیمت پایانی": 101, "قیمت سهم پایه": 1000, "قیمت اعمال": 1100, "تاریخ سررسید": "2026-10-30"},
            }])
            self._write(root, "sha2", "2026-09-26T11:00:00+00:00", [{
                "identity": {"instrument_id": "100", "contract_type": "CALL", "underlying_symbol": "X"},
                "canonical": {"نماد": "X100", "آخرین قیمت": 125, "قیمت پایانی": 126, "قیمت سهم پایه": 1050, "قیمت اعمال": 1100, "تاریخ سررسید": "2026-10-30"},
            }])
            result = build_observed_outcomes(root)
            self.assertEqual(result["snapshot_count"], 2)
            self.assertEqual(result["transition_count"], 1)
            item = result["transitions"][0]
            self.assertEqual(item["instrument_id"], "100")
            self.assertEqual(item["option_change"], 25.0)
            self.assertAlmostEqual(item["option_change_pct"], 0.25)
            self.assertEqual(item["underlying_change"], 50.0)
            self.assertAlmostEqual(item["underlying_change_pct"], 0.05)
            self.assertAlmostEqual(item["elapsed_days"], 1 / 24)

    def test_missing_price_does_not_become_zero(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write(root, "sha1", "2026-09-26T10:00:00+00:00", [{"identity": {"instrument_id": "100"}, "canonical": {"آخرین قیمت": None, "قیمت سهم پایه": 1000}}])
            self._write(root, "sha2", "2026-09-26T11:00:00+00:00", [{"identity": {"instrument_id": "100"}, "canonical": {"آخرین قیمت": 125, "قیمت سهم پایه": 1050}}])
            item = build_observed_outcomes(root)["transitions"][0]
            self.assertIsNone(item["option_change"])
            self.assertIsNone(item["option_change_pct"])
            self.assertEqual(item["underlying_change"], 50.0)

    def test_no_signal_or_labels_are_generated(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write(root, "sha1", "2026-09-26T10:00:00+00:00", [{"identity": {"instrument_id": "100"}, "canonical": {"آخرین قیمت": 100}}])
            self._write(root, "sha2", "2026-09-26T11:00:00+00:00", [{"identity": {"instrument_id": "100"}, "canonical": {"آخرین قیمت": 90}}])
            result = build_observed_outcomes(root)
            self.assertEqual(result["rules"]["signal_generation"], "FORBIDDEN")
            self.assertEqual(result["rules"]["labels"], "NOT_INFERRED")
            self.assertEqual(result["transitions"][0]["outcome_type"], "OBSERVED_STATE_CHANGE")


if __name__ == "__main__":
    unittest.main()
