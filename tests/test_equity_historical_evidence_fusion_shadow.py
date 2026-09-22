import unittest
from equity_historical_evidence_fusion_shadow import fuse_historical_evidence

class FusionTests(unittest.TestCase):
    def test_none(self):
        r=fuse_historical_evidence([{"instrument_id":"E","type":"T"}])
        self.assertEqual(r["opportunities"][0]["historical_evidence_fusion"]["state"],"NO_HISTORICAL_CONFIRMATION")
    def test_repeated(self):
        r=fuse_historical_evidence([{"instrument_id":"E","type":"T","historical_confirmation":{"status":"REPEATED_EVIDENCE","observation_count":2},"historical_memory":{"level":"REPEATED","observation_count":2}}])
        self.assertEqual(r["opportunities"][0]["historical_evidence_fusion"]["state"],"REPEATED_HISTORICAL_EVIDENCE")
    def test_recurring(self):
        r=fuse_historical_evidence([{"instrument_id":"E","type":"T","historical_confirmation":{"status":"REPEATED_EVIDENCE","recurrence_count":1},"historical_memory":{"level":"RECURRING"}}])
        self.assertEqual(r["opportunities"][0]["historical_evidence_fusion"]["state"],"RECURRING_HISTORICAL_EVIDENCE")
    def test_safety(self):
        r=fuse_historical_evidence([{"instrument_id":"E","type":"T","historical_memory":{"level":"REPEATED"}}])
        f=r["opportunities"][0]["historical_evidence_fusion"]
        self.assertEqual(f["direction_inference"],"DISABLED")
        self.assertEqual(f["score_change"],"NONE")
        self.assertFalse(f["causal_inference"])

if __name__=="__main__": unittest.main()
