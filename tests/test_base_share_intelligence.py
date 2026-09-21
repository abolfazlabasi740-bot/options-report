import unittest

from base_share_intelligence import build_base_share_intelligence


class BaseShareIntelligenceTests(unittest.TestCase):
    def test_explicit_instrument_history_produces_directional_changes(self):
        previous = [{
            "instrument_id": "BASE1",
            "symbol": "فزر",
            "last_price": 100,
            "close_price": 99,
            "volume": 1000,
            "trade_value": 5000,
        }]
        current = [{
            "instrument_id": "BASE1",
            "symbol": "فزر",
            "last_price": 105,
            "close_price": 104,
            "volume": 1200,
            "trade_value": 6000,
        }]
        result = build_base_share_intelligence(current, previous)
        row = result["rows"][0]
        self.assertEqual(row["sequence_state"], "PERSISTENT")
        self.assertEqual(row["last_price"]["direction"], "UP")
        self.assertEqual(row["volume"]["direction"], "UP")
        self.assertEqual(row["trade_value"]["direction"], "UP")
        self.assertAlmostEqual(row["last_price"]["delta"], 5)

    def test_symbol_without_explicit_instrument_id_is_not_linked(self):
        current = [{"symbol": "فزر", "last_price": 105}]
        result = build_base_share_intelligence(current, [])
        self.assertEqual(result["rows"], [])

    def test_option_link_requires_explicit_underlying_id(self):
        current = [{"instrument_id": "BASE1", "symbol": "فزر", "last_price": 100}]
        options = [
            {
                "instrument_id": "OPT1",
                "underlying_id": "BASE1",
                "volume": 10,
                "trade_value": 100,
                "last_price": 5,
                "FinalScore": 60,
            },
            {
                "instrument_id": "OPT2",
                "underlying_id": None,
                "volume": 100,
                "trade_value": 1000,
                "last_price": 10,
                "FinalScore": 90,
            },
        ]
        result = build_base_share_intelligence(current, [], options)
        context = result["rows"][0]["option_context"]
        self.assertEqual(context["linked_option_count"], 1)
        self.assertEqual(context["option_volume_total"], 10)


if __name__ == "__main__":
    unittest.main()
