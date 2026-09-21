import tempfile
import unittest
from pathlib import Path

from historical_snapshot import append_snapshot, build_snapshot, diff_snapshots, field_delta, load_history


class HistoricalSnapshotTests(unittest.TestCase):
    def test_snapshot_is_deterministic_and_append_only(self):
        a = build_snapshot("S1", [{"instrument_id": "A", "FinalScore": 10}], source="test")
        b = build_snapshot("S1", [{"instrument_id": "A", "FinalScore": 10}], source="test")
        self.assertEqual(a["records_hash"], b["records_hash"])

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            self.assertEqual(append_snapshot(path, a)["status"], "APPENDED")
            self.assertEqual(append_snapshot(path, b)["status"], "DUPLICATE")
            self.assertEqual(len(load_history(path)), 1)

    def test_diff_reports_real_field_change_without_threshold(self):
        previous = build_snapshot(
            "S1",
            [{"instrument_id": "A", "FinalScore": 10, "DataConfidence": 80}],
        )
        current = build_snapshot(
            "S2",
            [
                {"instrument_id": "A", "FinalScore": 12, "DataConfidence": 90},
                {"instrument_id": "B", "FinalScore": 1},
            ],
        )
        result = diff_snapshots(previous, current)
        self.assertEqual(result["summary"]["changed"], 1)
        self.assertEqual(result["summary"]["added"], 1)
        change = result["changes"][0]
        self.assertEqual(change["identity"], "A")
        self.assertEqual(change["fields"]["FinalScore"]["direction"], "UP")
        self.assertEqual(change["fields"]["FinalScore"]["delta"], 2)

    def test_percent_change_handles_zero_without_invention(self):
        result = field_delta(0, 5)
        self.assertIsNone(result["percent_change"])
        self.assertEqual(result["direction"], "UP")


if __name__ == "__main__":
    unittest.main()
