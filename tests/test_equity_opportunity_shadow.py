import unittest
import pandas as pd
from equity_intelligence_shadow import analyze_equities
from equity_opportunity_shadow import detect_equity_opportunities

class EquityOpportunityTests(unittest.TestCase):
    def _df(self):
        return pd.DataFrame([{
            "instrument_id":"EQ1","last_price":110,"close_price":100,
            "volume":1000,"trade_value":50000,"return_pct":10,
            "volume_change_pct":20,"benchmark_return_pct":2,
            "individual_net_flow":100
        }])

    def test_multifamily_cluster_creates_opportunity(self):
        r=analyze_equities(self._df(),"S1")
        o=detect_equity_opportunities(r["cases"],r["evidence_clusters"],snapshot_id="S1")
        self.assertEqual(o["summary"]["opportunity_count"],1)
        self.assertEqual(o["opportunities"][0]["status"],"WATCH")
        self.assertEqual(o["opportunities"][0]["direction_inference"],"DISABLED")

    def test_single_family_does_not_create(self):
        cases=[{"case_id":"c1","instrument_id":"EQ1","family":"PRICE_STRUCTURE","status":"OBSERVED","evidence":[]}]
        clusters={"clusters":[{"cluster_id":"x","instrument_id":"EQ1",
                               "independent_family_count":1,
                               "case_ids":["c1"],"supporting_evidence":[{"family":"PRICE_STRUCTURE","case_ids":["c1"]}]}]}
        o=detect_equity_opportunities(cases,clusters,snapshot_id="S1")
        self.assertEqual(o["summary"]["opportunity_count"],0)

    def test_missing_evidence_not_zero_filled(self):
        cases=[{"case_id":"c1","instrument_id":"EQ1","family":"PRICE_STRUCTURE","status":"INSUFFICIENT_DATA","evidence":[]}]
        clusters={"clusters":[]}
        o=detect_equity_opportunities(cases,clusters,snapshot_id="S1")
        self.assertEqual(o["opportunities"],[])

    def test_price_volume_relationship_is_descriptive(self):
        r=analyze_equities(self._df(),"S1")
        pv=next(x for x in r["cases"] if x["family"]=="PRICE_VOLUME")
        self.assertEqual(pv["status"],"OBSERVED")
        self.assertIn(pv["evidence"][-1]["value"],{"CONCORDANT","DIVERGENT","NEUTRAL"})
        o=detect_equity_opportunities(r["cases"],r["evidence_clusters"],snapshot_id="S1")
        self.assertFalse(any("BUY" in str(x) or "SELL" in str(x) for x in o["opportunities"]))

    def test_explicit_benchmark_only(self):
        df=self._df().drop(columns=["benchmark_return_pct"])
        r=analyze_equities(df,"S1")
        rel=next(x for x in r["cases"] if x["family"]=="MARKET_RELATIVE")
        self.assertEqual(rel["status"],"INSUFFICIENT_DATA")

    def test_deterministic(self):
        r=analyze_equities(self._df(),"S1")
        a=detect_equity_opportunities(r["cases"],r["evidence_clusters"],snapshot_id="S1")
        b=detect_equity_opportunities(r["cases"],r["evidence_clusters"],snapshot_id="S1")
        self.assertEqual(a["opportunities_sha256"],b["opportunities_sha256"])

if __name__=="__main__":
    unittest.main()
