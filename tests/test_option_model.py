import math
import unittest

from option_model import black_scholes_metrics


class TestOptionModel(unittest.TestCase):
    def test_call_delta_and_price_are_deterministic(self):
        r = black_scholes_metrics(100.0, 100.0, 10.0, 365.0, 0.20, "CALL")
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r["black_scholes"], 7.9655674554, places=6)
        self.assertAlmostEqual(r["delta"], 0.5398278373, places=6)
        self.assertEqual(r["risk_free_rate"], 0.0)

    def test_put_delta_is_negative(self):
        r = black_scholes_metrics(100.0, 100.0, 10.0, 365.0, 0.20, "PUT")
        self.assertIsNotNone(r)
        self.assertLess(r["delta"], 0.0)
        self.assertAlmostEqual(r["delta"], -0.4601721627, places=6)

    def test_invalid_inputs_fail_closed(self):
        self.assertIsNone(black_scholes_metrics(100, 100, 10, 0, 0.2, "CALL"))


if __name__ == "__main__":
    unittest.main()
