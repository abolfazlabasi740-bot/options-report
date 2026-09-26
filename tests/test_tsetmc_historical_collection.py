import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from collect_tsetmc_history import collect_once
from tsetmc_outcome_engine import build_observed_outcomes


class TsetmcHistoricalCollectionTests(unittest.TestCase):
    def test_collector_archives_full_universe_with_observation_metadata(self):
        snapshot = {
            "source_of_truth": "TSETMC",
            "snapshot_sha256": "sha-collector",
            "generated_at": "2026-09-26T18:30:00+00:00",
            "data_mode": "LIVE_TSETMC_REFRESH",
            "live_refresh_status": "SUCCESS",
            "rows": [{"identity": {"instrument_id": "1"}, "canonical": {"آخرین قیمت": 10}}],
            "evidence": {
                "market_watch": {
                    "retrieved_at": "2026-09-26T18:29:59+00:00",
                    "snapshot_sha256": "mw-sha",
                    "endpoint": "Instrument/GetInstrumentOptionMarketWatch/1",
                }
            },
        }
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch("collect_tsetmc_history.build_tsetmc_snapshot", return_value=snapshot):
                result = collect_once(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["row_count"], 1)
            path = root / "output" / "history" / "tsetmc" / "sha-collector.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["observation_retrieved_at"], "2026-09-26T18:29:59+00:00")
            self.assertEqual(payload["market_watch_snapshot_sha256"], "mw-sha")
            self.assertEqual(payload["row_count"], 1)

    def test_outcome_uses_observation_time_not_generation_time(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive = root / "output" / "history" / "tsetmc"
            archive.mkdir(parents=True)
            base = {
                "archive_version": "TSETMC-HISTORY-1.1",
                "source_of_truth": "TSETMC",
                "rows": [{
                    "identity": {"instrument_id": "1"},
                    "canonical": {"نماد": "X", "آخرین قیمت": 100, "قیمت سهم پایه": 1000},
                }],
            }
            for sha, gen, obs, price in [
                ("a", "2026-09-26T18:31:00+00:00", "2026-09-26T18:30:00+00:00", 100),
                ("b", "2026-09-26T18:40:00+00:00", "2026-09-26T18:35:00+00:00", 110),
            ]:
                payload = dict(base)
                payload.update({"snapshot_sha256": sha, "generated_at": gen, "observation_retrieved_at": obs})
                payload["rows"] = [dict(base["rows"][0], canonical={"نماد": "X", "آخرین قیمت": price, "قیمت سهم پایه": 1000})]
                (archive / f"{sha}.json").write_text(json.dumps(payload), encoding="utf-8")
            result = build_observed_outcomes(root)
            self.assertEqual(result["transition_count"], 1)
            self.assertAlmostEqual(result["transitions"][0]["elapsed_days"], 5 / 1440)

if __name__ == "__main__":
    unittest.main()
