import json, tempfile, unittest
from pathlib import Path
import pandas as pd
from scripts.reconcile_tsetmc_optionschool_fields import main

class TestFieldReconciliation(unittest.TestCase):
    def test_raw_fields_are_reported_without_formula_inference(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            wb=p/"x.xlsx"; rec=p/"r.json"; raw=p/"t.json"; out=p/"o.json"
            pd.DataFrame([{
                "نماد":"ضهرم7050","قیمت اعمال":20000,
                "تاریخ سررسید":"1405/07/29","روزهای تقویمی":28
            }]).to_excel(wb,index=False)
            rec.write_text(json.dumps({
                "row_mappings":[{
                    "optionschool_row":1,"symbol":"ضهرم7050",
                    "mapping_status":"EXACT_UNIQUE_SYMBOL_MATCH"
                }]
            }),encoding="utf-8")
            raw.write_text(json.dumps({
                "snapshot_sha256":"s",
                "data":{"instrumentOptMarketWatch":[{
                    "insCode_C":"624","uaInsCode":"179",
                    "lVal18AFC_C":"ضهرم7050","strikePrice":20000,
                    "endDate":20261021,"remainedDay":28,
                    "lval30_UA":"اهرم"
                }]}}
            ),encoding="utf-8")
            import sys
            old=sys.argv
            sys.argv=["x","--optionschool",str(wb),"--reconciliation",str(rec),
                      "--tsetmc",str(raw),"--output",str(out)]
            try: main()
            finally: sys.argv=old
            data=json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["row_count_compared"],1)
            checks=data["rows"][0]["checks"]
            self.assertEqual(checks["field_1_symbol"]["result"],"MATCH")
            self.assertEqual(checks["field_2_strike"]["result"],"MATCH")
            self.assertEqual(checks["field_6_calendar_days"]["result"],"SOURCE_CONVENTION_NOT_PROVEN")
            self.assertFalse(data["formula_inference"]!="DISABLED")

if __name__=="__main__":
    unittest.main()
