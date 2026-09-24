import json, tempfile, unittest
from pathlib import Path
import pandas as pd
from scripts.reconcile_tsetmc_optionschool_38 import reconcile

class TestReconcile(unittest.TestCase):
    def test_no_identity_never_infers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            wb=p/"x.xlsx"; js=p/"t.json"
            pd.DataFrame([{"نماد":"ضهرم7050","قیمت اعمال":20000}]).to_excel(wb,index=False)
            js.write_text(json.dumps({"endpoint":"x","snapshot_sha256":"s","retrieved_at":"r",
                "data":{"instrumentOptMarketWatch":[{"insCode_C":"123","uaInsCode":"456",
                "lVal18AFC_C":"ضهرم7050","strikePrice":20000}]}}),encoding="utf-8")
            out=reconcile(wb,js)
            self.assertIsNone(out["explicit_option_id_column"])
            self.assertEqual(out["exact_id_matches"],0)
            self.assertEqual(out["identity_inference"],"DISABLED")
            self.assertEqual(out["field_reconciliation"],"BLOCKED_UNTIL_EXPLICIT_ID_MATCH")

    def test_exact_identity_enables_next_stage(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); wb=p/"x.xlsx"; js=p/"t.json"
            pd.DataFrame([{"نماد":"ضهرم7050","کد نماد":123}]).to_excel(wb,index=False)
            js.write_text(json.dumps({"endpoint":"x","snapshot_sha256":"s","retrieved_at":"r",
                "data":{"instrumentOptMarketWatch":[{"insCode_C":123,"uaInsCode":456,
                "lVal18AFC_C":"ضهرم7050","strikePrice":20000}]}}),encoding="utf-8")
            out=reconcile(wb,js)
            self.assertEqual(out["explicit_option_id_count"],1)
            self.assertEqual(out["exact_id_matches"],1)
            self.assertEqual(out["field_reconciliation"],"IDENTITY_READY_FOR_FIELD_COMPARISON")

if __name__=="__main__": unittest.main()
