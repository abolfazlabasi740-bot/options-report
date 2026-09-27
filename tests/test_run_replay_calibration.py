import json
import tempfile
import unittest
from pathlib import Path

from run_replay_calibration import run


class ReplayCalibrationRuntimeTests(unittest.TestCase):
    def test_runner_writes_hashed_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive = root / "output" / "history" / "tsetmc"
            archive.mkdir(parents=True)
            base = {
                "source_of_truth": "TSETMC",
                "generated_at": "2026-09-26T09:30:00+00:00",
                "observation_retrieved_at": "2026-09-26T09:30:00+00:00",
                "rows": [{
                    "identity": {"instrument_id": "1", "contract_type": "PUT"},
                    "canonical": {
                        "نماد": "X",
                        "آخرین قیمت": 10,
                        "قیمت سهم پایه": 100,
                        "قیمت اعمال": 100,
                        "قیمت پایانی": 10,
                        "حجم معاملات": 100,
                        "ارزش معاملات": 1000,
                        "تاریخ سررسید": "20261007",
                        "تاریخ": "20260926",
                    },
                }],
            }
            for sha, obs, price in [
                ("a", "2026-09-26T09:30:00+00:00", 10),
                ("b", "2026-09-26T10:00:00+00:00", 12),
            ]:
                p = dict(base)
                p["snapshot_sha256"] = sha
                p["generated_at"] = obs
                p["observation_retrieved_at"] = obs
                p["rows"] = [dict(base["rows"][0], canonical=dict(base["rows"][0]["canonical"], **{"آخرین قیمت": price}))]
                (archive / f"{sha}.json").write_text(json.dumps(p), encoding="utf-8")
            output = root / "output" / "calibration" / "replay.json"
            result = run(root, output)
            self.assertTrue(output.exists())
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved["observation_count"], 1)
            self.assertEqual(saved["signal_generation"], saved.get("rules", {}).get("signal_generation")) if "signal_generation" in saved else None
            self.assertEqual(len(result["calibration_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
