import unittest

from historical_sensitivity_audit import run_snapshot


def _row(i, contract_type="CALL"):
    return {
        "identity": {"instrument_id": f"I{i}", "contract_type": contract_type},
        "canonical": {
            "نماد": f"X{i}",
            "قیمت سهم پایه": 1000 + i,
            "قیمت اعمال": 950 + i,
            "آخرین قیمت": 80 + i,
            "قیمت پایانی": 82 + i,
            "بیشترین قیمت": 85 + i,
            "کمترین قیمت": 78 + i,
            "روزهای تقویمی": 20 + i,
            "حجم معاملات": 1000 + i * 100,
            "ارزش معاملات": 100000 + i * 10000,
        },
    }


def _snapshot():
    rows = [_row(i, "CALL" if i % 2 == 0 else "PUT") for i in range(12)]
    return {
        "source_of_truth": "TSETMC",
        "snapshot_sha256": "a" * 64,
        "generated_at": "2026-09-25T19:00:00+00:00",
        "rows": rows,
        "eligibility": {
            "candidate_instrument_ids": [r["identity"]["instrument_id"] for r in rows]
        },
    }


class HistoricalSensitivityTests(unittest.TestCase):
    def test_sensitivity_is_deterministic_and_evidence_only(self):
        a = run_snapshot(_snapshot(), top_n=5)
        b = run_snapshot(_snapshot(), top_n=5)
        self.assertEqual(a["status"], "EVIDENCE_ONLY")
        self.assertFalse(a["production_mutation"])
        self.assertEqual(a["evidence_hash"], b["evidence_hash"])
        self.assertEqual(len(a["analysis"]["block_ablations"]), 6)
        self.assertEqual(len(a["analysis"]["factor_ablations"]), 9)
        self.assertIn("CALL", a["analysis"]["by_contract_type"])
        self.assertIn("PUT", a["analysis"]["by_contract_type"])


if __name__ == "__main__":
    unittest.main()
