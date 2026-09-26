import json
import tempfile
import unittest
from pathlib import Path

from run_calibration import run_calibration


class CalibrationRuntimeTests(unittest.TestCase):
    def test_uses_audited_tsetmc_ranking_and_binds_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            audit = root / "audit.json"
            out = root / "calibration.json"
            audit.write_text(json.dumps({
                "source_of_truth": "TSETMC",
                "snapshot_sha256": "abc123",
                "generated_at": "2026-09-26T12:30:00",
                "row_count": 2,
                "audit_integrity": {"status": "PASS"},
                "ranking": {
                    "ranking_rows": [
                        {"instrument_id": "1", "symbol": "A", "contract_type": "CALL",
                         "rank": 1, "score": 90,
                         "supported_blocks": ["LIQUIDITY"],
                         "features": {"trade_value": 100, "volume": 10}},
                        {"instrument_id": "2", "symbol": "B", "contract_type": "PUT",
                         "rank": 2, "score": 80,
                         "supported_blocks": ["LIQUIDITY"],
                         "features": {"trade_value": 200, "volume": 20}},
                    ]
                },
            }), encoding="utf-8")
            result = run_calibration(audit, out)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["source_snapshot_sha256"], "abc123")
            self.assertEqual(result["ranking_evidence_row_count"], 2)
            self.assertEqual(result["signal_generation"], "FORBIDDEN")
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
