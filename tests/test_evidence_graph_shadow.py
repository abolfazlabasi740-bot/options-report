import unittest
from evidence_graph_shadow import build_evidence_graph

class EvidenceGraphTests(unittest.TestCase):
    def test_graph_is_deterministic_and_preserves_sources(self):
        cases=[{"case_id":"C1","symbol":"ضX","type":"BASE_BREAKEVEN_CONTEXT","status":"WATCH",
                "evidence":[{"name":"underlying_return_pct","value":-10,"source":"underlying_last_price/underlying_close_price"}]}]
        patterns={"patterns":[{"identity":"ضX","type":"PRICE_VOLUME_DIVERGENT","snapshot_id":"S1","classification":"DESCRIPTIVE_RELATIONSHIP"}]}
        g1=build_evidence_graph(cases,historical_patterns=patterns)
        g2=build_evidence_graph(cases,historical_patterns=patterns)
        self.assertEqual(g1["graph_sha256"],g2["graph_sha256"])
        self.assertTrue(any(e["relation"]=="SUPPORTED_BY" for e in g1["edges"]))
        self.assertTrue(any(e["relation"]=="HISTORICAL_CONTEXT" for e in g1["edges"]))

    def test_red_team_is_explicitly_connected(self):
        cases=[{"case_id":"C1","symbol":"ضX","type":"RELATIVE_VALUE_ANOMALY","status":"WATCH","evidence":[]}]
        red={"cases":[{"case_id":"C1","challenges":[{"code":"X","reason":"test"}]}]}
        g=build_evidence_graph(cases,red_team=red)
        self.assertTrue(any(e["relation"]=="CHALLENGED_BY" for e in g["edges"]))

if __name__=="__main__":
    unittest.main()
