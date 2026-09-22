import unittest
from equity_pattern_shadow import analyze_cross_snapshot_patterns

def e(s,state="PERSISTENT"):
    return {"snapshot_id":s,"opportunity_key":"EQ1::TYPE::A|B",
            "instrument_id":"EQ1","state":state,"transition":"PERSISTED",
            "evidence_families":["A","B"]}

class PatternTests(unittest.TestCase):
    def test_repeated(self):
        r=analyze_cross_snapshot_patterns([e("S1","NEW"),e("S2","PERSISTENT")])
        self.assertEqual(r["pattern_count"],1)
        self.assertEqual(r["patterns"][0]["type"],"PERSISTENT_OR_STRENGTHENING")
    def test_recurring(self):
        r=analyze_cross_snapshot_patterns([e("S1","NEW"),e("S2","RESOLVED"),e("S3","RECURRING")])
        self.assertEqual(r["pattern_count"],1)
        self.assertEqual(r["patterns"][0]["type"],"RECURRING_PATTERN")
    def test_resolution_is_preserved(self):
        r=analyze_cross_snapshot_patterns([e("S1","NEW"),e("S2","RESOLVED"),e("S3","RECURRING")])
        p=r["patterns"][0]
        self.assertEqual(p["states"],["NEW","RESOLVED","RECURRING"])
        self.assertEqual(p["timeline_event_count"],3)
        self.assertEqual(p["resolution_count"],1)
        self.assertEqual(p["observation_count"],2)

    def test_min_observations(self):
        r=analyze_cross_snapshot_patterns([e("S1")])
        self.assertEqual(r["pattern_count"],0)
    def test_deterministic(self):
        x=[e("S2"),e("S1")]
        a=analyze_cross_snapshot_patterns(x); b=analyze_cross_snapshot_patterns(x)
        self.assertEqual(a["patterns_sha256"],b["patterns_sha256"])
    def test_no_direction_or_score(self):
        r=analyze_cross_snapshot_patterns([e("S1"),e("S2")])
        p=r["patterns"][0]
        self.assertEqual(p["direction_inference"],"DISABLED")
        self.assertEqual(p["score_change"],"NONE")

if __name__=="__main__": unittest.main()
