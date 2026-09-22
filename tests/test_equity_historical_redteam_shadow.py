import unittest
from equity_historical_redteam_shadow import fuse_historical_redteam

class HistoricalRedTeamTests(unittest.TestCase):
    def test_no_match(self):
        r=fuse_historical_redteam([{"instrument_id":"E","type":"T","evidence_families":["FLOW"]}], [])
        self.assertEqual(r["opportunities"][0]["historical_redteam_fusion"]["state"], "HISTORICAL_NO_MATCH")

    def test_support(self):
        o={"instrument_id":"E","type":"T","evidence_families":["FLOW"]}
        key="E::T::FLOW"
        events=[{"opportunity_key":key,"snapshot_id":"old","state":"PERSISTENT","red_team_challenges":[]}]
        r=fuse_historical_redteam([o], events)
        self.assertEqual(r["opportunities"][0]["historical_redteam_fusion"]["state"], "HISTORICAL_SUPPORT_PRESENT")

    def test_mixed(self):
        o={"instrument_id":"E","type":"T","evidence_families":["FLOW"],"snapshot_id":"new"}
        key="E::T::FLOW"
        events=[{"opportunity_key":key,"snapshot_id":"old","state":"PERSISTENT",
                 "red_team_challenges":[{"case_id":"C1","challenge":"test"}]}]
        r=fuse_historical_redteam([o], events)
        self.assertEqual(r["opportunities"][0]["historical_redteam_fusion"]["state"], "HISTORICAL_MIXED_EVIDENCE")

    def test_safety(self):
        o={"instrument_id":"E","type":"T","evidence_families":["FLOW"]}
        r=fuse_historical_redteam([o], [{"opportunity_key":"E::T::FLOW","snapshot_id":"old","state":"PERSISTENT"}])
        f=r["opportunities"][0]["historical_redteam_fusion"]
        self.assertEqual(f["direction_inference"], "DISABLED")
        self.assertEqual(f["score_change"], "NONE")
        self.assertFalse(f["causal_inference"])

if __name__=="__main__":
    unittest.main()
