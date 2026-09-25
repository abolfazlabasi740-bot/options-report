import json
import unittest

from tsetmc_adapter import TSETMCAdapter, TSETMCError


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self._body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TSETMCAdapterTests(unittest.TestCase):
    def test_quote_unwraps_and_hashes_payload(self):
        calls = []

        def opener(request, timeout):
            calls.append((request.full_url, timeout))
            return FakeResponse({"closingPriceInfo": {"pDrCotVal": 123}})

        result = TSETMCAdapter(
            base_url="https://example.test/api", retries=0, opener=opener
        ).quote("123")

        self.assertEqual(result["source"], "TSETMC")
        self.assertEqual(result["data"]["pDrCotVal"], 123)
        self.assertEqual(len(result["snapshot_sha256"]), 64)
        self.assertEqual(len(calls), 1)
        self.assertIn("/ClosingPrice/GetClosingPriceInfo/123", calls[0][0])

    def test_bestlimits_fails_fast_with_auxiliary_timeout(self):
        seen = []

        def opener(request, timeout):
            seen.append(timeout)
            raise TimeoutError("simulated BestLimits timeout")

        with self.assertRaises(TSETMCError):
            TSETMCAdapter(
                base_url="https://example.test/api", retries=2, timeout=8.0, opener=opener
            ).order_book("123")

        self.assertEqual(seen, [3.0])


    def test_symbol_is_encoded(self):
        seen = []

        def opener(request, timeout):
            seen.append(request.full_url)
            return FakeResponse({"instrumentSearch": []})

        TSETMCAdapter(
            base_url="https://example.test/api", retries=0, opener=opener
        ).search_instrument("نماد آزمون")

        self.assertIn("%D9%86%D9%85%D8%A7%D8%AF", seen[0])

    def test_soft_block_is_rejected(self):
        def opener(request, timeout):
            return FakeResponse({"error": "دسترسی شما مسدود است"})

        with self.assertRaises(TSETMCError):
            TSETMCAdapter(
                base_url="https://example.test/api", retries=0, opener=opener
            ).quote("123")

    def test_canonical_consumes_explicit_underlying_identity(self):
        def opener(request, timeout):
            if "GetInstrumentIdentity" in request.full_url:
                return FakeResponse({"instrumentIdentity": {
                    "lVal18AFC": "ضهرم", "underlyingId": "BASE1",
                    "underlyingSymbol": "هرم", "contractType": "CALL"
                }})
            if "GetInstrumentInfo" in request.full_url:
                return FakeResponse({"instrumentInfo": {}})
            return FakeResponse({"closingPriceInfo": {
                "pDrCotVal": 100, "pClosing": 101,
                "dEven": 20260922, "hEven": 123456
            }})

        row = TSETMCAdapter(
            base_url="https://example.test/api", retries=0, opener=opener
        ).canonical_instrument("123")

        self.assertEqual(row["underlying_id"], "BASE1")
        self.assertEqual(row["underlying_symbol"], "هرم")
        self.assertEqual(row["contract_type"], "CALL")
        self.assertEqual(row["source_market_timestamp"], "2026-09-22T12:34:56")
        self.assertEqual(row["source_market_timestamp_status"], "AVAILABLE")

    def test_canonical_does_not_infer_identity(self):
        def opener(request, timeout):
            if "GetInstrumentIdentity" in request.full_url:
                return FakeResponse({"instrumentIdentity": {"lVal18AFC": "ضهرم"}})
            if "GetInstrumentInfo" in request.full_url:
                return FakeResponse({"instrumentInfo": {"lVal18AFC": "ضهرم"}})
            return FakeResponse(
                {"closingPriceInfo": {"pDrCotVal": 100, "pClosing": 101}}
            )

        row = TSETMCAdapter(
            base_url="https://example.test/api", retries=0, opener=opener
        ).canonical_instrument("123")

        self.assertEqual(row["symbol"], "ضهرم")
        self.assertIsNone(row["contract_type"])
        self.assertIsNone(row["underlying_id"])
        self.assertIsNone(row["underlying_symbol"])
        self.assertIsNone(row["expiry"])
        self.assertIsNone(row["strike"])

    def test_option_market_watch_preserves_raw_payload_and_evidence(self):
        def opener(request, timeout):
            self.assertIn("/Instrument/GetInstrumentOptionMarketWatch/1", request.full_url)
            return FakeResponse({"optionMarketWatch": [{"insCode": "OPT1"}]})

        result = TSETMCAdapter(
            base_url="https://example.test/api", retries=0, opener=opener
        ).option_market_watch(1)

        self.assertEqual(result["source"], "TSETMC")
        self.assertEqual(result["data"]["optionMarketWatch"][0]["insCode"], "OPT1")
        self.assertEqual(len(result["snapshot_sha256"]), 64)


    def test_option_market_watch_records_preserve_explicit_identity(self):
        def opener(request, timeout):
            self.assertIn("/Instrument/GetInstrumentOptionMarketWatch/1", request.full_url)
            return FakeResponse({"instrumentOptMarketWatch": [{
                "insCode_P": "P123",
                "insCode_C": "C456",
                "uaInsCode": "UA789",
                "lVal18AFC_P": "طهرم7050",
                "lVal18AFC_C": "ضهرم7050",
                "lval30_UA": "اهرم",
                "strikePrice": 20000,
                "beginDate": "20260725",
                "endDate": "20261021",
                "remainedDay": 28,
            }]})

        adapter = TSETMCAdapter(
            base_url="https://example.test/api", retries=0, opener=opener
        )
        result = adapter.option_market_watch_records(flow=1)
        self.assertEqual(result["record_count"], 1)
        self.assertEqual(result["records"][0]["option_put_id"], "P123")
        self.assertEqual(result["records"][0]["option_call_id"], "C456")
        self.assertEqual(result["records"][0]["underlying_id"], "UA789")
        self.assertEqual(result["records"][0]["strike"], 20000)
        self.assertEqual(result["records"][0]["end_date"], "20261021")
        self.assertEqual(result["records"][0]["market_watch_fields"]["last_price"], None)
        self.assertIn("underlying_market_watch_fields", result["records"][0])
        self.assertEqual(result["records"][0]["contract_size"], None)

    def test_option_market_watch_instrument_records_expand_explicit_ids(self):
        def opener(request, timeout):
            return FakeResponse({"instrumentOptMarketWatch": [{
                "insCode_P": "P123",
                "insCode_C": "C456",
                "uaInsCode": "UA789",
                "lVal18AFC_P": "طهرم7050",
                "lVal18AFC_C": "ضهرم7050",
                "lval30_UA": "اهرم",
                "strikePrice": 20000,
                "beginDate": "20260725",
                "endDate": "20261021",
                "remainedDay": 28,
            }]})

        adapter = TSETMCAdapter(
            base_url="https://example.test/api", retries=0, opener=opener
        )
        result = adapter.option_market_watch_instrument_records(flow=1)
        self.assertEqual(result["record_count"], 2)
        by_id = {r["instrument_id"]: r for r in result["records"]}
        self.assertEqual(by_id["P123"]["contract_type"], "PUT")
        self.assertEqual(by_id["P123"]["identity_source_field"], "insCode_P")
        self.assertEqual(by_id["P123"]["underlying_id"], "UA789")
        self.assertEqual(by_id["C456"]["contract_type"], "CALL")
        self.assertEqual(by_id["C456"]["identity_source_field"], "insCode_C")
        self.assertEqual(by_id["C456"]["strike"], 20000)

    def test_option_market_watch_records_shape_placeholder(self):
        adapter = TSETMCAdapter(
            base_url="https://example.test/api", retries=0, opener=lambda request, timeout: FakeResponse({"instrumentOptMarketWatch": []})
        )
        self.assertEqual(adapter.option_market_watch_records(1)["record_count"], 0)


if __name__ == "__main__":
    unittest.main()
