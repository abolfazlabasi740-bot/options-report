import unittest

from report_engine import _attach_canonical_quote_evidence


class FakeAdapter:
    def __init__(self, payloads):
        self.payloads = payloads

    def quote(self, ins_code):
        return self.payloads[ins_code]


class CanonicalQuoteEvidenceTests(unittest.TestCase):
    def test_attaches_explicit_tsetmc_timestamp_and_match(self):
        rows = [{
            "identity": {"instrument_id": "OPT1"},
            "canonical": {"آخرین قیمت": 359.0, "قیمت پایانی": 359.0},
        }]
        adapter = FakeAdapter({
            "OPT1": {
                "source": "TSETMC",
                "endpoint": "https://example.test/ClosingPrice/GetClosingPriceInfo/OPT1",
                "retrieved_at": "2026-09-26T14:38:49Z",
                "data": {
                    "dEven": 20260926,
                    "hEven": 122958,
                    "pDrCotVal": 359.0,
                    "pClosing": 359.0,
                },
            }
        })

        _attach_canonical_quote_evidence(rows, adapter=adapter)

        self.assertEqual(rows[0]["source_market_timestamp"], "2026-09-26T12:29:58")
        self.assertEqual(rows[0]["source_market_timestamp_status"], "AVAILABLE")
        self.assertEqual(rows[0]["canonical_quote_evidence"]["quote_consistency"], "MATCH")

    def test_does_not_use_retrieval_time_when_source_timestamp_missing(self):
        rows = [{
            "identity": {"instrument_id": "OPT2"},
            "canonical": {"آخرین قیمت": 10.0, "قیمت پایانی": 10.0},
        }]
        adapter = FakeAdapter({
            "OPT2": {
                "source": "TSETMC",
                "endpoint": "https://example.test/ClosingPrice/GetClosingPriceInfo/OPT2",
                "retrieved_at": "2026-09-26T14:38:49Z",
                "data": {
                    "dEven": 0,
                    "hEven": 122958,
                    "pDrCotVal": 10.0,
                    "pClosing": 10.0,
                },
            }
        })

        _attach_canonical_quote_evidence(rows, adapter=adapter)

        self.assertIsNone(rows[0]["source_market_timestamp"])
        self.assertEqual(rows[0]["source_market_timestamp_status"], "UNAVAILABLE")
        self.assertEqual(
            rows[0]["canonical_quote_evidence"]["retrieved_at"],
            "2026-09-26T14:38:49Z",
        )

    def test_preserves_marketwatch_values_when_canonical_quote_differs(self):
        rows = [{
            "identity": {"instrument_id": "OPT3"},
            "canonical": {"آخرین قیمت": 47.0, "قیمت پایانی": 50.0},
        }]
        adapter = FakeAdapter({
            "OPT3": {
                "source": "TSETMC",
                "endpoint": "https://example.test/ClosingPrice/GetClosingPriceInfo/OPT3",
                "retrieved_at": "2026-09-26T14:38:50Z",
                "data": {
                    "dEven": 20260926,
                    "hEven": 122959,
                    "pDrCotVal": 48.0,
                    "pClosing": 51.0,
                },
            }
        })

        _attach_canonical_quote_evidence(rows, adapter=adapter)

        self.assertEqual(rows[0]["canonical"]["آخرین قیمت"], 47.0)
        self.assertEqual(rows[0]["canonical"]["قیمت پایانی"], 50.0)
        self.assertEqual(rows[0]["canonical_quote_evidence"]["quote_consistency"], "DIFFERS")
        self.assertEqual(rows[0]["source_market_timestamp"], "2026-09-26T12:29:59")


if __name__ == "__main__":
    unittest.main()
