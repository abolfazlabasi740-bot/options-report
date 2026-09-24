import json, tempfile, unittest
from pathlib import Path
import pandas as pd

from scripts.reconcile_combined_tsetmc_identity import reconcile


class TestCombinedIdentity(unittest.TestCase):
    def _write(self, p, rows, mw_rows, search_evidence):
        wb = p / "x.xlsx"
        mw = p / "mw.json"
        sr = p / "search.json"
        pd.DataFrame(rows).to_excel(wb, index=False)
        mw.write_text(json.dumps({
            "tsetmc_snapshot_sha256": "mwsha",
            "tsetmc_endpoint": "mwendpoint",
            "tsetmc_retrieved_at": "2026-09-23T17:17:58Z",
            "row_mappings": mw_rows,
        }, ensure_ascii=False), encoding="utf-8")
        sr.write_text(json.dumps({"evidence": search_evidence}), encoding="utf-8")
        return wb, mw, sr

    def test_disjoint_sources_combine(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            wb, mw, sr = self._write(
                p,
                [{"نماد": "A"}, {"نماد": "B"}, {"نماد": "C"}],
                [{"symbol": "A", "mapping_status": "EXACT_UNIQUE_SYMBOL_MATCH", "tsetmc_instrument_id": "1"}],
                [{"symbol": "B", "status": "EXACT_SYMBOL_MATCH",
                  "retrieved_at": "r", "endpoint": "e", "snapshot_sha256": "s",
                  "exact_matches": [{"lVal18AFC": "B", "insCode": "2"}]}],
            )
            out = reconcile(wb, mw, sr)
            self.assertEqual(out["combined_exact_unique_symbols"], 2)
            self.assertEqual(out["unresolved_symbols"], 1)
            self.assertEqual(out["source_overlap_symbols"], 0)
            self.assertFalse(out["promotion_ready"])

    def test_overlap_same_id_counts_once(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            wb, mw, sr = self._write(
                p,
                [{"نماد": "A"}],
                [{"symbol": "A", "mapping_status": "EXACT_UNIQUE_SYMBOL_MATCH", "tsetmc_instrument_id": "1"}],
                [{"symbol": "A", "status": "EXACT_SYMBOL_MATCH",
                  "exact_matches": [{"lVal18AFC": "A", "insCode": "1"}]}],
            )
            out = reconcile(wb, mw, sr)
            self.assertEqual(out["combined_exact_unique_symbols"], 1)
            self.assertEqual(out["source_overlap_symbols"], 1)
            self.assertEqual(out["identity_conflicts"], 0)
            self.assertTrue(out["promotion_ready"])

    def test_conflicting_ids_block(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            wb, mw, sr = self._write(
                p,
                [{"نماد": "A"}],
                [{"symbol": "A", "mapping_status": "EXACT_UNIQUE_SYMBOL_MATCH", "tsetmc_instrument_id": "1"}],
                [{"symbol": "A", "status": "EXACT_SYMBOL_MATCH",
                  "exact_matches": [{"lVal18AFC": "A", "insCode": "9"}]}],
            )
            out = reconcile(wb, mw, sr)
            self.assertEqual(out["identity_conflicts"], 1)
            self.assertEqual(out["row_mappings"][0]["identity_status"], "IDENTITY_CONFLICT")
            self.assertFalse(out["promotion_ready"])


if __name__ == "__main__":
    unittest.main()
