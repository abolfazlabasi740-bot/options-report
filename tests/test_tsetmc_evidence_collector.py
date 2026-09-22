#!/usr/bin/env python3
import unittest

from tsetmc_evidence_collector import collect_underlying_evidence


class FakeAdapter:
    def __init__(self, option_map=None, quote_map=None, fail=False):
        self.option_map = option_map or {}
        self.quote_map = quote_map or {}
        self.fail = fail

    def canonical_instrument(self, ins_code):
        if self.fail:
            raise RuntimeError("should be wrapped only as supported source errors")
        return self.option_map[ins_code]

    def quote(self, ins_code):
        return self.quote_map[ins_code]


class TsetmcEvidenceCollectorTests(unittest.TestCase):
    def test_exact_option_to_underlying_quote(self):
        adapter = FakeAdapter(
            option_map={
                "OPT1": {
                    "underlying_id": "BASE1",
                    "source_refs": {"identity": {"snapshot_sha256": "opt-hash"}},
                }
            },
            quote_map={
                "BASE1": {
                    "source": "TSETMC",
                    "endpoint": "https://example/base1",
                    "retrieved_at": "2026-09-22T01:00:00Z",
                    "snapshot_sha256": "base-hash",
                    "data": {"pDrCotVal": 90, "pClosing": 100},
                }
            },
        )
        result = collect_underlying_evidence(["OPT1"], adapter=adapter)
        rec = result["records"][0]
        self.assertEqual(rec["status"], "EXACT_UNDERLYING_QUOTE")
        self.assertEqual(rec["underlying_id"], "BASE1")
        self.assertEqual(rec["underlying_last_price"], 90.0)
        self.assertEqual(rec["underlying_close_price"], 100.0)
        self.assertEqual(rec["underlying_quote_evidence"]["snapshot_sha256"], "base-hash")
        self.assertTrue(rec["evidence_sha256"])

    def test_missing_underlying_does_not_infer_from_option_id(self):
        adapter = FakeAdapter(option_map={"OPT1": {"underlying_id": None}})
        result = collect_underlying_evidence(["OPT1"], adapter=adapter)
        rec = result["records"][0]
        self.assertEqual(rec["status"], "NO_EXPLICIT_UNDERLYING_ID")
        self.assertIsNone(rec["underlying_id"])

    def test_insufficient_underlying_quote_is_not_zero_filled(self):
        adapter = FakeAdapter(
            option_map={"OPT1": {"underlying_id": "BASE1"}},
            quote_map={"BASE1": {"data": {"pDrCotVal": 90}}},
        )
        result = collect_underlying_evidence(["OPT1"], adapter=adapter)
        rec = result["records"][0]
        self.assertEqual(rec["status"], "UNDERLYING_QUOTE_INSUFFICIENT")
        self.assertNotIn("underlying_close_price", rec)

    def test_duplicate_option_ids_are_collected_once(self):
        adapter = FakeAdapter(
            option_map={"OPT1": {"underlying_id": None}}
        )
        result = collect_underlying_evidence(["OPT1", "OPT1"], adapter=adapter)
        self.assertEqual(result["summary"]["requested"], 1)

if __name__ == "__main__":
    unittest.main()
