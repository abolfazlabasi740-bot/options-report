import json
import tempfile
import unittest
from pathlib import Path

from tsetmc_history import archive_universe_snapshot


class TsetmcHistoryTests(unittest.TestCase):
    def test_archives_by_snapshot_sha_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            snapshot = {
                "snapshot_sha256": "abc123",
                "generated_at": "2026-09-26T12:30:00",
                "data_mode": "LIVE_TSETMC_REFRESH",
                "live_refresh_status": "SUCCESS",
                "market_state": {"status": "OFFMARKET"},
                "universe_rows": [{"identity": {"instrument_id": "1"}}],
            }
            path = archive_universe_snapshot(snapshot, root)
            self.assertTrue(path.exists())
            first = path.read_text(encoding="utf-8")
            snapshot["universe_rows"] = [{"identity": {"instrument_id": "2"}}]
            same = archive_universe_snapshot(snapshot, root)
            self.assertEqual(path, same)
            self.assertEqual(first, path.read_text(encoding="utf-8"))

    def test_missing_identity_data_is_not_archived(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(archive_universe_snapshot({}, Path(d)))

    def test_archive_payload_binds_source_and_row_count(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            snapshot = {
                "snapshot_sha256": "sha789",
                "source_of_truth": "TSETMC",
                "generated_at": "2026-09-26T12:30:00",
                "data_mode": "LIVE_TSETMC_REFRESH",
                "live_refresh_status": "SUCCESS",
                "universe_rows": [
                    {"identity": {"instrument_id": "1"}},
                    {"identity": {"instrument_id": "2"}},
                ],
            }
            path = archive_universe_snapshot(snapshot, root)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["source_of_truth"], "TSETMC")
            self.assertEqual(payload["snapshot_sha256"], "sha789")
            self.assertEqual(payload["row_count"], 2)
            self.assertEqual(len(payload["rows"]), 2)


if __name__ == "__main__":
    unittest.main()
