import json, tempfile, unittest
from pathlib import Path
import pandas as pd
from scripts.analyze_unmatched_optionschool_symbols import main

class TestUnmatched(unittest.TestCase):
    def test_absence_is_not_expiry(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            wb=p/"x.xlsx"; js=p/"t.json"; out=p/"o.json"
            pd.DataFrame([{"نماد":"A"},{"نماد":"B"}]).to_excel(wb,index=False)
            js.write_text(json.dumps({"snapshot_sha256":"s","data":{"instrumentOptMarketWatch":[
                {"insCode_C":1,"lVal18AFC_C":"A"}]}}),encoding="utf-8")
            import sys
            old=sys.argv
            sys.argv=["x","--optionschool",str(wb),"--tsetmc",str(js),"--output",str(out)]
            try: main()
            finally: sys.argv=old
            data=json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["unmatched_count"],1)
            self.assertEqual(data["unmatched"][0]["symbol"],"B")
            self.assertFalse(data["unmatched"][0]["closed_or_expired_proven"])
            self.assertEqual(data["unmatched"][0]["classification"],"NOT_IN_CURRENT_TSETMC_SNAPSHOT")

if __name__=="__main__": unittest.main()


    def test_expiry_is_promoted_only_with_explicit_snapshot_time(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            wb=p/"x.xlsx"; js=p/"t.json"; out=p/"o.json"
            pd.DataFrame([
                {"نماد":"A","تاریخ سررسید":"2026-09-20"},
                {"نماد":"B","تاریخ سررسید":"2026-10-20"},
            ]).to_excel(wb,index=False)
            js.write_text(json.dumps({"snapshot_sha256":"s","data":{"instrumentOptMarketWatch":[]}}),encoding="utf-8")
            import sys
            old=sys.argv
            sys.argv=["x","--optionschool",str(wb),"--tsetmc",str(js),"--output",str(out),
                      "--snapshot-retrieved-at","2026-09-23T17:17:58.479447+00:00"]
            try: main()
            finally: sys.argv=old
            data=json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["unmatched_count"],2)
            self.assertEqual(data["unmatched"][0]["classification"],"EXPIRED_BEFORE_SNAPSHOT")
            self.assertTrue(data["unmatched"][0]["closed_or_expired_proven"])
            self.assertEqual(data["unmatched"][1]["classification"],"NOT_IN_CURRENT_TSETMC_SNAPSHOT")
            self.assertFalse(data["unmatched"][1]["closed_or_expired_proven"])
