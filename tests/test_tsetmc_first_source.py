import unittest
from tsetmc_first_source import build_tsetmc_snapshot
class FakeAdapter:
    def option_market_watch_instrument_records(self, flow=1):
        return {"source":"TSETMC","endpoint":"mw","snapshot_sha256":"mwhash","retrieved_at":"t",
                "records":[{"instrument_id":"OTHER","contract_type":"CALL","underlying_id":"UA1",
                "underlying_symbol":"BASE","symbol":"ضOTHER","strike":19000,"end_date":"20261021",
                "remaining_days":28,"identity_source_field":"insCode_C"},
                {"instrument_id":"OPT1","contract_type":"CALL","underlying_id":"UA1",
                "underlying_symbol":"BASE","symbol":"ضTEST","strike":20000,"end_date":"20261021",
                "remaining_days":28,"identity_source_field":"insCode_C"}]}
    def quote(self, ins_code):
        if ins_code=="OPT1":
            return {"source":"TSETMC","endpoint":"quote/OPT1","snapshot_sha256":"qh1","retrieved_at":"t1",
                    "data":{"pDrCotVal":1500,"pClosing":1400,"qTotTran5J":100,"qTotCap":150000,
                            "priceMin":1300,"priceMax":1600,"dEven":20260924,"hEven":101530}}
        return {"source":"TSETMC","endpoint":"quote/UA1","snapshot_sha256":"qh2","retrieved_at":"t2",
                "data":{"pDrCotVal":21000,"pClosing":20500}}
    def instrument_info(self, ins_code):
        return {"source":"TSETMC","endpoint":f"info/{ins_code}","snapshot_sha256":"ih","retrieved_at":"t4",
                "data":{"contractSize":1000}}
    def order_book(self, ins_code):
        return {"source":"TSETMC","endpoint":f"book/{ins_code}","snapshot_sha256":"bh","retrieved_at":"t3","data":[]}
class TsetmcFirstSourceTests(unittest.TestCase):
    def test_tsetmc_is_only_source(self):
        s=build_tsetmc_snapshot(adapter=FakeAdapter(), max_instruments=1); self.assertEqual(s["source_of_truth"],"TSETMC")
        self.assertIsNone(s["external_comparison_source"]); self.assertEqual(s["row_count"],1)
        r=s["rows"][0]
        self.assertEqual(r["identity"]["instrument_id"],"OPT1"); self.assertEqual(r["identity"]["contract_type"],"CALL")
        self.assertEqual(r["canonical"]["نماد"],"ضTEST"); self.assertEqual(r["canonical"]["قیمت اعمال"],20000)
        self.assertEqual(r["canonical"]["آخرین قیمت"],1500); self.assertEqual(r["canonical"]["قیمت سهم پایه"],21000)
        self.assertEqual(r["canonical"]["حجم معاملات"],100); self.assertEqual(r["canonical"]["ارزش معاملات"],150000)
        self.assertEqual(r["canonical"]["روزهای تقویمی"],28)
        self.assertEqual(r["expiry_evidence"]["source_field"],"endDate/remainedDay")
        self.assertEqual(r["source_market_timestamp"],"2026-09-24T10:15:30")
        self.assertEqual(r["source_market_timestamp_status"],"AVAILABLE")
        self.assertEqual(r["orderbook_level_count"], 0)
        self.assertEqual(r["orderbook_raw_levels"], [])
        self.assertIsNone(r["canonical"]["روزهای تقویمی"]); self.assertEqual(r["raw_remaining_days"],28)
    def test_symbol_filter_applies_before_enrichment_bound(self):
        s=build_tsetmc_snapshot(adapter=FakeAdapter(), symbol_prefix="ضTEST", max_instruments=1)
        self.assertEqual(s["row_count"],1)
        self.assertEqual(s["rows"][0]["canonical"]["نماد"],"ضTEST")

    def test_invalid_max_instruments_is_rejected(self):
        with self.assertRaises(ValueError):
            build_tsetmc_snapshot(adapter=FakeAdapter(), max_instruments=0)

    def test_no_guess_when_quote_fails(self):
        class Broken(FakeAdapter):
            def quote(self, ins_code):
                if ins_code=="OPT1": raise RuntimeError("blocked")
                return super().quote(ins_code)
        s=build_tsetmc_snapshot(adapter=Broken(), symbol_prefix="ضTEST"); r=s["rows"][0]
        self.assertIsNone(r["canonical"]["آخرین قیمت"]); self.assertIsNone(r["canonical"]["قیمت پایانی"])
if __name__=="__main__": unittest.main()
