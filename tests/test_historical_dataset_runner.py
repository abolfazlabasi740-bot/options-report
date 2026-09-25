import json
import tempfile
import unittest
from pathlib import Path

from historical_dataset_runner import run_file


def _snapshot():
    rows = []
    for i in range(4):
        rows.append({
            "identity": {"instrument_id": f"I{i}", "contract_type": "CALL"},
            "canonical": {
                "نماد": f"X{i}",
                "قیمت سهم پایه": 1000 + i,
                "قیمت اعمال": 950,
                "آخرین قیمت": 80 + i,
                "قیمت پایانی": 81 + i,
                "بیشترین قیمت": 85 + i,
                "کمترین قیمت": 78 + i,
                "روزهای تقویمی": 20,
                "حجم معاملات": 100 + i,
                "ارزش معاملات": 1000 + i * 100,
            },
        })
    return {
        "source_of_truth": "TSETMC",
        "snapshot_sha256": "b" * 64,
        "rows": rows,
        "eligibility": {
            "candidate_instrument_ids": [r["identity"]["instrument_id"] for r in rows]
        },
    }


class HistoricalDatasetRunnerTests(unittest.TestCase):
    def test_runner_records_sha_and_tsetmc_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "snapshot.json"
            p.write_text(json.dumps(_snapshot(), ensure_ascii=False), encoding="utf-8")
            result = run_file(p, top_n=2)
            self.assertTrue(result["file_sha256"])
            self.assertEqual(result["status"], "EVIDENCE_ONLY")
            self.assertEqual(result["source_of_truth"], "TSETMC")
            self.assertEqual(result["row_count"], 4)


if __name__ == "__main__":
    unittest.main()
