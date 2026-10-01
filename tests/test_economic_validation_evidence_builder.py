import json
import tempfile
import unittest
from pathlib import Path

import economic_validation_evidence_builder as builder


class EconomicValidationEvidenceBuilderTests(unittest.TestCase):
    def test_empty_archive_is_evidence_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "output" / "history" / "tsetmc").mkdir(parents=True)
            result = builder.build_evidence(root)
            self.assertEqual(result["status"], "EVIDENCE_ONLY")
            self.assertEqual(result["source_snapshot_count"], 0)
            self.assertEqual(result["closure"]["g7_5_status"], "OPEN")

    def test_archive_loader_preserves_snapshot_sha(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "output" / "history" / "tsetmc"
            folder.mkdir(parents=True)
            payload = {
                "source_of_truth": "TSETMC",
                "snapshot_sha256": "abc123",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "rows": [],
            }
            (folder / "abc123.json").write_text(json.dumps(payload), encoding="utf-8")
            loaded = builder._archives(root)
            self.assertEqual(sorted(loaded), ["abc123"])


if __name__ == "__main__":
    unittest.main()
