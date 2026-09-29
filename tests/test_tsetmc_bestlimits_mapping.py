import unittest

from tsetmc_bestlimits_mapping import (
    MAPPING_VERSION,
    map_bestlimits_level_1,
)


class TSETMCBestLimitsMappingTests(unittest.TestCase):
    def test_normal_two_sided_book(self):
        raw = {
            "pMeDem": 68825.0,
            "pMeOf": 68888.0,
            "qTitMeDem": 24740,
            "qTitMeOf": 1000,
            "zOrdMeDem": 9,
            "zOrdMeOf": 1,
        }
        self.assertEqual(
            map_bestlimits_level_1(raw),
            {
                "bid_price": 68825.0,
                "ask_price": 68888.0,
                "bid_quantity": 24740,
                "ask_quantity": 1000,
                "bid_order_count": 9,
                "ask_order_count": 1,
            },
        )

    def test_one_sided_book_preserves_zeroes(self):
        raw = {
            "pMeDem": 5.0,
            "pMeOf": 0.0,
            "qTitMeDem": 24,
            "qTitMeOf": 0,
            "zOrdMeDem": 1,
            "zOrdMeOf": 0,
        }
        result = map_bestlimits_level_1(raw)
        self.assertEqual(result["bid_price"], 5.0)
        self.assertEqual(result["ask_price"], 0.0)
        self.assertEqual(result["bid_quantity"], 24)
        self.assertEqual(result["ask_quantity"], 0)
        self.assertEqual(result["bid_order_count"], 1)
        self.assertEqual(result["ask_order_count"], 0)

    def test_missing_fields_are_not_invented(self):
        result = map_bestlimits_level_1({"pMeDem": 3.0})
        self.assertEqual(result["bid_price"], 3.0)
        self.assertIsNone(result["ask_price"])
        self.assertIsNone(result["bid_quantity"])
        self.assertIsNone(result["ask_quantity"])
        self.assertIsNone(result["bid_order_count"])
        self.assertIsNone(result["ask_order_count"])

    def test_mapping_version_is_explicit(self):
        self.assertEqual(MAPPING_VERSION, "TSETMC-BESTLIMITS-MAPPING-1.0")


if __name__ == "__main__":
    unittest.main()
