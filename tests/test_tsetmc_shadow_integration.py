#!/usr/bin/env python3
import os
import unittest
import pandas as pd

from tsetmc_shadow_integration import enrich_shadow_with_tsetmc


class FakeAdapter:
    def canonical_instrument(self, ins_code):
        return {"underlying_id": "BASE1", "source_refs": {"snapshot_sha256": "opt"}}

    def quote(self, ins_code):
        return {"snapshot_sha256": "base", "data": {"pDrCotVal": 90, "pClosing": 100}}


class TsetmcShadowIntegrationTests(unittest.TestCase):
    def test_disabled_is_network_independent(self):
        shadow = pd.DataFrame({"نماد": ["ضX"]})
        source = pd.DataFrame({"نماد": ["ضX"]})
        out, meta = enrich_shadow_with_tsetmc(shadow, source, enabled=False)
        self.assertEqual(meta["status"], "DISABLED")
        self.assertEqual(out["underlying_context_status"].iloc[0], "INSUFFICIENT_DATA")

    def test_exact_id_attaches_underlying_context(self):
        shadow = pd.DataFrame({"نماد": ["ضX"]})
        source = pd.DataFrame({"insCode": ["OPT1"]})
        out, meta = enrich_shadow_with_tsetmc(
            shadow, source, enabled=True, adapter=FakeAdapter()
        )
        self.assertEqual(meta["status"], "SUCCESS")
        self.assertEqual(out["underlying_last_price"].iloc[0], 90.0)
        self.assertEqual(out["underlying_close_price"].iloc[0], 100.0)
        self.assertEqual(out["underlying_context_status"].iloc[0], "EXACT_UNDERLYING_QUOTE")

    def test_no_option_id_does_not_infer_from_symbol(self):
        shadow = pd.DataFrame({"نماد": ["ضهرم7060"]})
        source = pd.DataFrame({"نماد": ["ضهرم7060"]})
        out, meta = enrich_shadow_with_tsetmc(
            shadow, source, enabled=True, adapter=FakeAdapter()
        )
        self.assertEqual(meta["status"], "NO_EXPLICIT_OPTION_ID")
        self.assertTrue(pd.isna(out["underlying_last_price"].iloc[0]))

if __name__ == "__main__":
    unittest.main()
