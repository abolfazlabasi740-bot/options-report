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


if __name__ == "__main__":
    unittest.main()
