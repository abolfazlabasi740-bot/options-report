import unittest

from golden_output_validator import (
    load_golden,
    parse_report_cards,
    validate_report_against_golden,
)


class GoldenOutputValidatorTests(unittest.TestCase):
    def setUp(self):
        self.golden = {
            "source_file": "optionschool_20260922_071052_767703.xlsx",
            "selected": [
                {"rank": 1, "symbol": "ضستا7062", "final_score": 66.40},
                {"rank": 2, "symbol": "ضستا7060", "final_score": 66.25},
            ],
        }

    def test_parse_cards(self):
        report = (
            "📄 فایل: optionschool_20260922_071052_767703.xlsx\n"
            "🔹 1. ضستا7062\n"
            "🏆 امتیاز: 66.40\n"
            "🔹 2. ضستا7060\n"
            "🏆 امتیاز: 66.25\n"
        )
        self.assertEqual(parse_report_cards(report), self.golden["selected"])

    def test_match(self):
        report = (
            "📄 فایل: optionschool_20260922_071052_767703.xlsx\n"
            "🔹 1. ضستا7062\n"
            "🏆 امتیاز: 66.40\n"
            "🔹 2. ضستا7060\n"
            "🏆 امتیاز: 66.25\n"
        )
        result = validate_report_against_golden(report, self.golden)
        self.assertEqual(result["status"], "MATCH")

    def test_identity_mismatch_is_blocking_for_validation(self):
        report = (
            "📄 فایل: optionschool_20260922_071052_767703.xlsx\n"
            "🔹 1. ضستا7061\n"
            "🏆 امتیاز: 66.40\n"
            "🔹 2. ضستا7060\n"
            "🏆 امتیاز: 66.25\n"
        )
        result = validate_report_against_golden(report, self.golden)
        self.assertEqual(result["status"], "MISMATCH")
        self.assertEqual(
            result["mismatches"][0]["reason"],
            "IDENTITY_OR_RANK_MISMATCH",
        )

    def test_score_mismatch_is_detected(self):
        report = (
            "📄 فایل: optionschool_20260922_071052_767703.xlsx\n"
            "🔹 1. ضستا7062\n"
            "🏆 امتیاز: 66.10\n"
            "🔹 2. ضستا7060\n"
            "🏆 امتیاز: 66.25\n"
        )
        result = validate_report_against_golden(report, self.golden)
        self.assertEqual(result["status"], "MISMATCH")
        self.assertEqual(
            result["mismatches"][0]["reason"],
            "SCORE_MISMATCH",
        )

    def test_fixture_is_structurally_valid(self):
        fixture = load_golden(
            "tests/fixtures/golden_gate3_20260922_selected.json"
        )
        self.assertEqual(fixture["selected_count"], 15)
        self.assertEqual(len(fixture["selected"]), 15)
        self.assertEqual([x["rank"] for x in fixture["selected"]], list(range(1, 16)))
        self.assertEqual(len({x["symbol"] for x in fixture["selected"]}), 15)


if __name__ == "__main__":
    unittest.main()
