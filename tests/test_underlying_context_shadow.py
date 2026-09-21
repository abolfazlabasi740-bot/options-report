import unittest
import pandas as pd

from underlying_context_shadow import (
    ENGINE_VERSION,
    attach_underlying_context,
    build_underlying_index,
)


class UnderlyingContextShadowTests(unittest.TestCase):
    def test_exact_underlying_id_attaches_prices(self):
        canonical = pd.DataFrame([{"instrument_id": "OPT1", "underlying_id": "BASE1"}])
        records = [{
            "instrument_id": "BASE1",
            "last_price": 90,
            "close_price": 100,
            "source_refs": {
                "endpoint": "tsetmc://quote/BASE1",
                "snapshot_sha256": "abc",
            },
        }]
        out, meta = attach_underlying_context(canonical, records)
        self.assertEqual(meta["engine_version"], ENGINE_VERSION)
        self.assertEqual(meta["exact_attached"], 1)
        self.assertEqual(out.iloc[0]["underlying_context_status"], "EXACT_UNDERLYING_ID")
        self.assertEqual(float(out.iloc[0]["underlying_last_price"]), 90.0)
        self.assertEqual(float(out.iloc[0]["underlying_close_price"]), 100.0)

    def test_missing_underlying_id_is_not_inferred(self):
        canonical = pd.DataFrame([{"instrument_id": "OPT1", "symbol": "ضهرم", "underlying_id": None}])
        records = [{"instrument_id": "BASE1", "symbol": "هرم", "last_price": 90, "close_price": 100}]
        out, meta = attach_underlying_context(canonical, records)
        self.assertEqual(meta["exact_attached"], 0)
        self.assertEqual(out.iloc[0]["underlying_context_status"], "INSUFFICIENT_DATA")
        self.assertTrue(pd.isna(out.iloc[0]["underlying_last_price"]))

    def test_ambiguous_underlying_id_is_not_overwritten(self):
        canonical = pd.DataFrame([{"instrument_id": "OPT1", "underlying_id": "BASE1"}])
        records = [
            {"instrument_id": "BASE1", "last_price": 90, "close_price": 100},
            {"instrument_id": "BASE1", "last_price": 91, "close_price": 100},
        ]
        out, meta = attach_underlying_context(canonical, records)
        self.assertEqual(meta["ambiguous"], 1)
        self.assertEqual(out.iloc[0]["underlying_context_status"], "AMBIGUOUS")
        self.assertTrue(pd.isna(out.iloc[0]["underlying_last_price"]))

    def test_source_ref_is_preserved(self):
        canonical = pd.DataFrame([{"instrument_id": "OPT1", "underlying_id": "BASE1"}])
        records = [{
            "instrument_id": "BASE1", "last_price": 90, "close_price": 100,
            "source": "TSETMC", "endpoint": "x", "retrieved_at": "t",
            "snapshot_sha256": "hash",
        }]
        out, _ = attach_underlying_context(canonical, records)
        ref = out.iloc[0]["underlying_source_ref"]
        self.assertEqual(ref["snapshot_sha256"], "hash")

    def test_index_requires_explicit_instrument_id(self):
        index = build_underlying_index([{"symbol": "هرم", "last_price": 90, "close_price": 100}])
        self.assertEqual(index, {})


if __name__ == "__main__":
    unittest.main()
