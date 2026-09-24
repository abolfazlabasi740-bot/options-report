import unittest


CANDIDATE_FIELDS = {
    "bid_price": "pd",
    "ask_price": "po",
    "bid_quantity": "qd",
    "ask_quantity": "qo",
    "bid_order_count": "zd",
    "ask_order_count": "zo",
}


def validate_candidate_mapping(raw):
    """Validate only structural market invariants for a quarantined hypothesis.

    This helper deliberately does not assert that the hypothesis is true.
    It is a regression harness for rejecting structurally impossible mappings.
    """
    errors = []
    for index, level in enumerate(raw, start=1):
        missing = [field for field in CANDIDATE_FIELDS.values() if field not in level]
        if missing:
            errors.append(f"level {index}: missing raw fields {missing}")
            continue

        pd = level["pd"]
        po = level["po"]
        qd = level["qd"]
        qo = level["qo"]
        zd = level["zd"]
        zo = level["zo"]

        if pd is not None and po is not None and po < pd:
            errors.append(f"level {index}: ask price {po} < bid price {pd}")
        if qd is not None and qd < 0:
            errors.append(f"level {index}: negative bid quantity {qd}")
        if qo is not None and qo < 0:
            errors.append(f"level {index}: negative ask quantity {qo}")
        if zd is not None and zd < 0:
            errors.append(f"level {index}: negative bid order count {zd}")
        if zo is not None and zo < 0:
            errors.append(f"level {index}: negative ask order count {zo}")

    return errors


class BestLimitsEvidenceHarnessTests(unittest.TestCase):
    # Synthetic fixtures only. They are not production market observations.
    def _fixtures(self):
        return [
            {
                "instrument_id": "OPT_A",
                "timestamp": "2026-09-24T09:10:00",
                "levels": [
                    {"zo": 3, "zd": 4, "pd": 1000, "po": 1010, "qd": 1200, "qo": 900},
                    {"zo": 2, "zd": 3, "pd": 990, "po": 1020, "qd": 800, "qo": 700},
                ],
            },
            {
                "instrument_id": "OPT_B",
                "timestamp": "2026-09-24T10:15:00",
                "levels": [
                    {"zo": 1, "zd": 5, "pd": 2050, "po": 2060, "qd": 500, "qo": 450},
                ],
            },
            {
                "instrument_id": "OPT_C",
                "timestamp": "2026-09-24T11:20:00",
                "levels": [
                    {"zo": 0, "zd": 2, "pd": 3000, "po": None, "qd": 200, "qo": 0},
                ],
            },
            {
                "instrument_id": "UNDERLYING_A",
                "timestamp": "2026-09-24T12:30:00",
                "levels": [
                    {"zo": 7, "zd": 9, "pd": 50000, "po": 50100, "qd": 10000, "qo": 8000},
                ],
            },
        ]

    def test_candidate_mapping_field_contract_is_explicit(self):
        self.assertEqual(CANDIDATE_FIELDS, {
            "bid_price": "pd",
            "ask_price": "po",
            "bid_quantity": "qd",
            "ask_quantity": "qo",
            "bid_order_count": "zd",
            "ask_order_count": "zo",
        })

    def test_candidate_mapping_passes_structural_invariants(self):
        for fixture in self._fixtures():
            self.assertEqual(
                validate_candidate_mapping(fixture["levels"]),
                [],
                fixture["instrument_id"],
            )

    def test_harness_rejects_inverted_price_relationship(self):
        bad = [{"zo": 1, "zd": 1, "pd": 1100, "po": 1000, "qd": 100, "qo": 100}]
        errors = validate_candidate_mapping(bad)
        self.assertTrue(any("ask price" in error for error in errors))

    def test_harness_rejects_negative_quantities_and_counts(self):
        bad = [{"zo": -1, "zd": 2, "pd": 1000, "po": 1010, "qd": -5, "qo": 10}]
        errors = validate_candidate_mapping(bad)
        self.assertEqual(len(errors), 2)

    def test_fixture_coverage_is_four_instruments(self):
        fixtures = self._fixtures()
        self.assertEqual(len(fixtures), 4)
        self.assertEqual(
            {f["instrument_id"] for f in fixtures},
            {"OPT_A", "OPT_B", "OPT_C", "UNDERLYING_A"},
        )


if __name__ == "__main__":
    unittest.main()
