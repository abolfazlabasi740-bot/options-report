import unittest
from tsetmc_first_source import build_tsetmc_snapshot
class FakeAdapter:
    quote_calls = 0
    def option_market_watch_instrument_records(self, flow=1):
        return {"source":"TSETMC","endpoint":"mw","snapshot_sha256":"mwhash","retrieved_at":"t",
                "records":[{"instrument_id":"OTHER","contract_type":"CALL","underlying_id":"UA1",
                "underlying_symbol":"BASE","symbol":"ضOTHER","strike":19000,"end_date":"20261021",
                "remaining_days":28,"identity_source_field":"insCode_C",
                "contract_size":1000,
                "market_watch_fields":{"last_price":1500,"close_price":1400,"volume":100,
                "trade_value":150000,"open_interest":10,"bid_price":1400,"ask_price":1500,
                "bid_quantity":1,"ask_quantity":2},
                "underlying_market_watch_fields":{"last_price":21000,"close_price":20500}},
                {"instrument_id":"OPT1","contract_type":"CALL","underlying_id":"UA1",
                "underlying_symbol":"BASE","symbol":"ضTEST","strike":20000,"end_date":"20261021",
                "remaining_days":28,"identity_source_field":"insCode_C",
                "contract_size":1000,
                "market_watch_fields":{"last_price":1500,"close_price":1400,"volume":100,
                "trade_value":150000,"open_interest":10,"bid_price":1400,"ask_price":1500,
                "bid_quantity":1,"ask_quantity":2},
                "underlying_market_watch_fields":{"last_price":21000,"close_price":20500}}]}
    def quote(self, ins_code):
        self.quote_calls += 1
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
        s=build_tsetmc_snapshot(adapter=FakeAdapter(), symbol_prefix="ضTEST", max_instruments=1); self.assertEqual(s["source_of_truth"],"TSETMC")
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
        self.assertEqual(r["canonical"]["روزهای تقویمی"],28); self.assertEqual(r["raw_remaining_days"],28)
    def test_symbol_filter_applies_before_enrichment_bound(self):
        s=build_tsetmc_snapshot(adapter=FakeAdapter(), symbol_prefix="ضTEST", max_instruments=1)
        self.assertEqual(s["row_count"],1)
        self.assertEqual(s["rows"][0]["canonical"]["نماد"],"ضTEST")


    def test_empty_market_watch_uses_last_known_tsetmc_snapshot(self):
        from pathlib import Path
        from unittest.mock import patch

        class Empty(FakeAdapter):
            def option_market_watch_instrument_records(self, flow=1):
                return {"source": "TSETMC", "endpoint": "mw", "records": []}

        cached = {
            "status": "SUCCESS",
            "source_of_truth": "TSETMC",
            "row_count": 1,
            "rows": [{"canonical": {"نماد": "ضCACHED"}, "source_market_timestamp": "2026-09-24T12:29:00"}],
            "evidence": {"market_watch": {"record_count": 1}},
            "snapshot_sha256": "cachedhash",
            "generated_at": "2026-09-24T12:29:01+00:00",
        }
        with patch("tsetmc_first_source.CACHE_PATH", Path("tests/.tmp_last_known_snapshot.json")):
            cache_path = Path("tests/.tmp_last_known_snapshot.json")
            try:
                cache_path.write_text(__import__("json").dumps(cached), encoding="utf-8")
                s = build_tsetmc_snapshot(adapter=Empty())
                self.assertEqual(s["data_mode"], "LAST_KNOWN_TSETMC_SNAPSHOT")
                self.assertEqual(s["live_refresh_status"], "UNAVAILABLE")
                self.assertEqual(s["fallback_reason"], "TSETMC_MARKET_WATCH_EMPTY")
                self.assertEqual(s["rows"][0]["canonical"]["نماد"], "ضCACHED")
            finally:
                if cache_path.exists():
                    cache_path.unlink()

    def test_refresh_exception_uses_last_known_tsetmc_snapshot(self):
        from pathlib import Path
        from unittest.mock import patch

        class BrokenRefresh(FakeAdapter):
            def option_market_watch_instrument_records(self, flow=1):
                raise TimeoutError("TSETMC unavailable")

        cached = {
            "status": "SUCCESS",
            "source_of_truth": "TSETMC",
            "row_count": 1,
            "rows": [{"canonical": {"نماد": "ضCACHED2"}, "source_market_timestamp": "2026-09-24T12:28:00"}],
            "evidence": {"market_watch": {"record_count": 1}},
            "snapshot_sha256": "cachedhash2",
            "generated_at": "2026-09-24T12:28:01+00:00",
        }
        with patch("tsetmc_first_source.CACHE_PATH", Path("tests/.tmp_last_known_snapshot.json")):
            cache_path = Path("tests/.tmp_last_known_snapshot.json")
            try:
                cache_path.write_text(__import__("json").dumps(cached), encoding="utf-8")
                s = build_tsetmc_snapshot(adapter=BrokenRefresh())
                self.assertEqual(s["data_mode"], "LAST_KNOWN_TSETMC_SNAPSHOT")
                self.assertEqual(s["live_refresh_status"], "UNAVAILABLE")
                self.assertEqual(s["fallback_reason"], "TimeoutError")
            finally:
                if cache_path.exists():
                    cache_path.unlink()

    def test_invalid_max_instruments_is_rejected(self):
        with self.assertRaises(ValueError):
            build_tsetmc_snapshot(adapter=FakeAdapter(), max_instruments=0)

    def test_market_watch_is_canonical_and_quote_is_not_called(self):
        adapter = FakeAdapter()
        s=build_tsetmc_snapshot(adapter=adapter, symbol_prefix="ضTEST")
        r=s["rows"][0]
        self.assertEqual(adapter.quote_calls, 0)
        self.assertEqual(r["quote_status"], "SUCCESS")
        self.assertEqual(r["canonical"]["آخرین قیمت"], 1500)
        self.assertEqual(r["canonical"]["قیمت پایانی"], 1400)
        self.assertEqual(r["canonical"]["قیمت سهم پایه"], 21000)
        self.assertEqual(r["canonical"]["حجم معاملات"], 100)
        self.assertEqual(r["canonical"]["ارزش معاملات"], 150000)
        self.assertEqual(r["canonical"]["موقعیت های باز"], 10)
        self.assertEqual(r["canonical"]["اندازه قرارداد"], 1000)
if __name__=="__main__": unittest.main()
