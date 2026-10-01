import unittest
from signal_engine_shadow import evaluate_shadow_candidate, evaluate_shadow_candidates

class SignalEngineShadowTests(unittest.TestCase):
    def candidate(self, **overrides):
        x={"instrument_id":"1","symbol":"طستا7065","contract_type":"PUT","rank":1,"score":90,
           "evidence":{"supported_blocks":["LIQUIDITY","VALUATION"],
                       "features":{"calendar_days":6,"trade_value":1000,"volume":100}}}
        x.update(overrides)
        return x
    def test_default_is_blocked(self):
        r=evaluate_shadow_candidate(self.candidate())
        self.assertEqual(r["state"],"BLOCKED")
        self.assertIsNone(r["production_signal"])
        self.assertEqual(r["buy_sell_signal"],"NOT_GENERATED")
        self.assertIn("STRATEGY_POLICY_NOT_VERSIONED",r["blockers"])
        self.assertIn("RISK_POLICY_NOT_VERSIONED",r["blockers"])
    def test_missing_evidence_fails_closed(self):
        r=evaluate_shadow_candidate(self.candidate(score=None))
        self.assertEqual(r["state"],"BLOCKED")
        self.assertIn("RANKING_SCORE_UNAVAILABLE",r["blockers"])
    def test_production_flag_alone_does_not_authorize_action(self):
        r=evaluate_shadow_candidate(self.candidate(),strategy_policy={"version":"S1"},
                                     risk_policy={"version":"R1"},production_enabled=True)
        self.assertEqual(r["state"],"WATCH")
        self.assertIsNone(r["production_signal"])
        self.assertIsNone(r["proposed_signal"])
    def test_batch_contract(self):
        r=evaluate_shadow_candidates([self.candidate(),self.candidate(instrument_id="2")])
        self.assertEqual(r["status"],"PASS")
        self.assertEqual(r["signal_count"],2)
        self.assertEqual(r["buy_sell_signal"],"NOT_GENERATED")
if __name__=="__main__":
    unittest.main()
