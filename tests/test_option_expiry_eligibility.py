import unittest
from datetime import date

from tsetmc_eligibility import (
    classify_eligibility,
    EXPIRED_CONTRACT,
    EXPIRY_UNAVAILABLE,
    OPPORTUNITY_CANDIDATE,
)


def row(expiry):
    return {
        "identity": {
            "instrument_id": "option-1",
            "contract_type": "CALL",
            "end_date": expiry,
        },
        "canonical": {
            "نماد": "نمادآزمایشی",
            "تاریخ سررسید": expiry,
            "حجم معاملات": 100,
            "تعداد معاملات": 5,
            "حجم بهترین تقاضا": 10,
            "حجم بهترین عرضه": 10,
        },
    }


class ExpiryEligibilityTests(unittest.TestCase):
    def test_expired_contract_is_excluded_even_with_activity(self):
        result = classify_eligibility(row("20260930"), as_of_date=date(2026, 10, 2))
        self.assertEqual(result["state"], EXPIRED_CONTRACT)
        self.assertFalse(result["opportunity_eligible"])

    def test_active_contract_remains_eligible(self):
        result = classify_eligibility(row("20261007"), as_of_date=date(2026, 10, 2))
        self.assertEqual(result["state"], OPPORTUNITY_CANDIDATE)
        self.assertTrue(result["opportunity_eligible"])

    def test_same_day_expiry_is_excluded(self):
        result = classify_eligibility(row("20261002"), as_of_date=date(2026, 10, 2))
        self.assertEqual(result["state"], EXPIRED_CONTRACT)
        self.assertFalse(result["opportunity_eligible"])

    def test_missing_expiry_is_excluded(self):
        item = row(None)
        item["canonical"]["تاریخ سررسید"] = None
        item["identity"]["end_date"] = None
        result = classify_eligibility(item, as_of_date=date(2026, 10, 2))
        self.assertEqual(result["state"], EXPIRY_UNAVAILABLE)
        self.assertFalse(result["opportunity_eligible"])


if __name__ == "__main__":
    unittest.main()
