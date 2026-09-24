import json
import tempfile
import unittest
from pathlib import Path

from scripts.investigate_unmatched_tsetmc_search import exact_matches


class TestUnmatchedSearch(unittest.TestCase):
    def test_exact_symbol_only(self):
        records = [
            {"lVal18AFC": "ضفزر724", "insCode": "123"},
            {"lVal18AFC": "ضفزر72", "insCode": "456"},
        ]
        matches = exact_matches("ضفزر724", records)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["insCode"], "123")

    def test_no_similarity_inference(self):
        records = [
            {"lVal18AFC": "ضفزر725", "insCode": "123"},
            {"symbol": "ضفزر72", "insCode": "456"},
        ]
        self.assertEqual(exact_matches("ضفزر724", records), [])


if __name__ == "__main__":
    unittest.main()
