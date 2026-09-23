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


if __name__ == "__main__":
    unittest.main()
