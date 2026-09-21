import unittest

import pandas as pd

from tsetmc_mapping import (
    AMBIGUOUS,
    EXACT,
    NO_MATCH,
    SYMBOL_ONLY,
    exact_only,
    map_option_rows,
)


class TSETMCMappingTests(unittest.TestCase):
    def test_exact_identifier_is_promoted(self):
        options = pd.DataFrame([{"نماد": "ضهرم"}])
        records = [{"instrument_id": "A", "symbol": "ضهرم"}]
        result = map_option_rows(options, records)
        self.assertEqual(result[0].status, SYMBOL_ONLY)
        self.assertEqual(exact_only(result), [])

    def test_explicit_identifier_is_exact(self):
        options = pd.DataFrame([{"نماد": "ضهرم", "insCode": "A"}])
        records = [{"instrument_id": "A", "symbol": "ضهرم"}]
        result = map_option_rows(options, records)
        self.assertEqual(result[0].status, EXACT)
        self.assertEqual(len(exact_only(result)), 1)

    def test_symbol_collision_is_ambiguous(self):
        options = pd.DataFrame([{"نماد": "نماد"}])
        records = [
            {"instrument_id": "A", "symbol": "نماد"},
            {"instrument_id": "B", "symbol": "نماد"},
        ]
        result = map_option_rows(options, records)
        self.assertEqual(result[0].status, AMBIGUOUS)

    def test_no_match_is_not_promoted(self):
        options = pd.DataFrame([{"نماد": "ندارد"}])
        records = [{"instrument_id": "A", "symbol": "نماد"}]
        result = map_option_rows(options, records)
        self.assertEqual(result[0].status, NO_MATCH)
        self.assertEqual(exact_only(result), [])


if __name__ == "__main__":
    unittest.main()
