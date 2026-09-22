import tempfile,unittest
from pathlib import Path
from equity_opportunity_lifecycle_shadow import append_opportunity_events,current_state

def opp(iid="EQ1",typ="EQUITY_MULTI_FACTOR_ANOMALY",fams=None,status="WATCH"):
    return {"instrument_id":iid,"type":typ,"evidence_families":fams or ["LIQUIDITY","PRICE_VOLUME"],
            "status":status,"opportunity_id":"OP1","cluster_id":"C1"}

class LifecycleTests(unittest.TestCase):
    def test_new_then_persistent(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"life.jsonl"
            a=append_opportunity_events(p,"S1",[opp()])
            b=append_opportunity_events(p,"S2",[opp()])
            self.assertEqual(a["states"],["NEW"])
            self.assertEqual(b["states"],["PERSISTENT"])
    def test_resolve_then_recur(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"life.jsonl"
            append_opportunity_events(p,"S1",[opp()])
            append_opportunity_events(p,"S2",[])
            r=append_opportunity_events(p,"S3",[opp()])
            self.assertIn("RECURRING",r["states"])
    def test_strength_change(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"life.jsonl"
            append_opportunity_events(p,"S1",[opp(status="WATCH")])
            r=append_opportunity_events(p,"S2",[opp(status="CONFIRMED")])
            self.assertIn("STRENGTHENING",r["states"])
    def test_explicit_key(self):
        a=opp("EQ1"); b=opp("EQ2")
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"life.jsonl"
            append_opportunity_events(p,"S1",[a,b])
            self.assertEqual(len(current_state(p)),2)

if __name__=="__main__": unittest.main()
