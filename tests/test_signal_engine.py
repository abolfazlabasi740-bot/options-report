import unittest

from signal_engine import (
    BLOCKED,
    SIGNAL_ENGINE_VERSION,
    evaluate_shadow_candidate,
    evaluate_shadow_candidates,
)


class SignalEngineShadowTests(unittest.TestCase):
    def _candidate(self):
        return {
            "instrument_id": "TEST-1",
            "symbol": "طستا7064",
            "contract_type": "PUT",
            "rank": 1,
            "score": 86.56,
            "blockers": [],
            "evidence": {
                "supported_blocks": ["LIQUIDITY", "VALUATION", "PAYOFF", "TIME", "MARKET"],
                "features": {
                    "calendar_days": 11,
                    "trade_value": 264627950000,
                    "volume": 737409,
                    "breakeven_distance": 0.04,
                    "leverage": 9.44,
                    "time_value_ratio": 0.01,
                    "last_vs_close": 0.0,
                    "intraday_range": 0.02,
                },
            },
        }

    def test_score_does_not_become_buy_signal(self):
        result = evaluate_shadow_candidate(self._candidate())
        self.assertEqual(result["state"], BLOCKED)
        self.assertIsNone(result["production_signal"])
        self.assertEqual(result["buy_sell_signal"], "NOT_GENERATED")
        self.assertIn("STRATEGY_POLICY_NOT_VERSIONED", result["blockers"])
        self.assertIn("RISK_POLICY_NOT_VERSIONED", result["blockers"])

    def test_production_disabled_remains_blocked_even_with_policies(self):
        result = evaluate_shadow_candidate(
            self._candidate(),
            strategy_policy={"version": "STRATEGY-1.0"},
            risk_policy={"version": "RISK-1.0"},
            production_enabled=False,
        )
        self.assertEqual(result["state"], BLOCKED)
        self.assertIn("PRODUCTION_SIGNAL_NOT_ENABLED", result["blockers"])

    def test_engine_is_deterministic_and_auditable(self):
        a = evaluate_shadow_candidates([self._candidate()])
        b = evaluate_shadow_candidates([self._candidate()])
        self.assertEqual(a, b)
        self.assertEqual(a["engine_version"], SIGNAL_ENGINE_VERSION)
        self.assertEqual(a["signal_count"], 1)


if __name__ == "__main__":
    unittest.main()

    def test_versioned_policies_still_do_not_authorize_directional_signal(self):
        result = evaluate_shadow_candidate(
            self._candidate(),
            strategy_policy={"version": "OPTIMUSAI-STRATEGY-V1"},
            risk_policy={"version": "OPTIMUSAI-RISK-V1"},
            production_enabled=True,
        )
        self.assertEqual(result["state"], "WATCH")
        self.assertIsNone(result["production_signal"])
        self.assertEqual(result["buy_sell_signal"], "NOT_GENERATED")
        self.assertEqual(result["blockers"], [])
        self.assertIn("NO_PRODUCTION_ACTION_AUTHORIZED", result["reason_codes"])
