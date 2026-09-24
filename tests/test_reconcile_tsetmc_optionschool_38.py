import json, tempfile, unittest
from pathlib import Path
import pandas as pd
from scripts.reconcile_tsetmc_optionschool_38 import reconcile

class TestReconcile(unittest.TestCase):
    def test_no_identity_never_infers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            wb=p/"x.xlsx"; js=p/"t.json"
            pd.DataFrame([{"قیمت اعمال":20000}]).to_excel(wb,index=False)
            js.write_text(json.dumps({"endpoint":"x","snapshot_sha256":"s","retrieved_at":"r",
                "data":{"instrumentOptMarketWatch":[{"insCode_C":"123","uaInsCode":"456",
                "lVal18AFC_C":"ضهرم7050","strikePrice":20000}]}}),encoding="utf-8")
            out=reconcile(wb,js)
            self.assertIsNone(out["explicit_option_id_column"])
            self.assertEqual(out["exact_id_matches"],0)
            self.assertEqual(out["identity_method"],"NO_SAFE_IDENTITY_MATCH")
            self.assertEqual(out["identity_inference"],"DISABLED")

    def test_exact_identity_enables_next_stage(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); wb=p/"x.xlsx"; js=p/"t.json"
            pd.DataFrame([{"نماد":"ضهرم7050","کد نماد":123}]).to_excel(wb,index=False)
            js.write_text(json.dumps({"endpoint":"x","snapshot_sha256":"s","retrieved_at":"r",
                "data":{"instrumentOptMarketWatch":[{"insCode_C":123,"uaInsCode":456,
                "lVal18AFC_C":"ضهرم7050","strikePrice":20000}]}}),encoding="utf-8")
            out=reconcile(wb,js)
            self.assertEqual(out["exact_id_matches"],1)
            self.assertTrue(out["exact_id_match_complete"])
            self.assertEqual(out["identity_method"],"EXACT_ID_MATCH")
            self.assertEqual(out["field_reconciliation"],"IDENTITY_READY_FOR_FIELD_COMPARISON")

    def test_partial_exact_id_does_not_promote(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); wb=p/"x.xlsx"; js=p/"t.json"
            pd.DataFrame([{"نماد":"ضهرم7050","کد نماد":123},{"نماد":"ضهرم7060","کد نماد":999}]).to_excel(wb,index=False)
            js.write_text(json.dumps({"data":{"instrumentOptMarketWatch":[{"insCode_C":123,"lVal18AFC_C":"ضهرم7050"}]}}),encoding="utf-8")
            out=reconcile(wb,js)
            self.assertEqual(out["exact_id_matches"],1)
            self.assertFalse(out["exact_id_match_complete"])
            self.assertEqual(out["identity_method"],"NO_SAFE_IDENTITY_MATCH")

    def test_unique_symbol_identity_enables_next_stage(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); wb=p/"x.xlsx"; js=p/"t.json"
            pd.DataFrame([{"نماد":"ضهرم7050","قیمت اعمال":20000}]).to_excel(wb,index=False)
            js.write_text(json.dumps({"endpoint":"x","snapshot_sha256":"s","retrieved_at":"r",
                "data":{"instrumentOptMarketWatch":[{"insCode_C":123,"uaInsCode":456,
                "lVal18AFC_C":"ضهرم7050","strikePrice":20000}]}}),encoding="utf-8")
            out=reconcile(wb,js)
            self.assertIsNone(out["explicit_option_id_column"])
            self.assertTrue(out["optionschool_symbol_unique"])
            self.assertTrue(out["tsetmc_symbol_unique"])
            self.assertEqual(out["unique_symbol_matches"],1)
            self.assertEqual(out["symbol_match_rate"],1.0)
            self.assertEqual(out["identity_method"],"EXPLICIT_SYMBOL_MATCH")
            self.assertEqual(out["field_reconciliation"],"IDENTITY_READY_FOR_FIELD_COMPARISON")

    def test_duplicate_symbol_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); wb=p/"x.xlsx"; js=p/"t.json"
            pd.DataFrame([{"نماد":"ضهرم7050"},{"نماد":"ضهرم7050"}]).to_excel(wb,index=False)
            js.write_text(json.dumps({"data":{"instrumentOptMarketWatch":[
                {"insCode_C":123,"lVal18AFC_C":"ضهرم7050"},
                {"insCode_P":456,"lVal18AFC_P":"طهرم7050"}]}}),encoding="utf-8")
            out=reconcile(wb,js)
            self.assertFalse(out["optionschool_symbol_unique"])
            self.assertEqual(out["identity_method"],"NO_SAFE_IDENTITY_MATCH")

if __name__=="__main__": unittest.main()
