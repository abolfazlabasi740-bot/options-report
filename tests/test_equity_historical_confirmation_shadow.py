import unittest
from equity_historical_confirmation_shadow import enrich_opportunities

class HistoricalConfirmationTests(unittest.TestCase):
    def test_repeated_evidence(self):
        o={"opportunities":[{"instrument_id":"EQ1","type":"EQUITY_MULTI_FACTOR_ANOMALY",
            "evidence_families":["B","A"]}]}
        p={"patterns":[{"opportunity_key":"EQ1::EQUITY_MULTI_FACTOR_ANOMALY::A|B",
            "type":"RECURRING_PATTERN","observation_count":3,"recurrence_count":1,
            "first_seen_snapshot":"S1","last_seen_snapshot":"S3","evidence_families":["A","B"]}]}
        r=enrich_opportunities(o,p)
        self.assertEqual(r["opportunities"][0]["historical_confirmation"]["status"],"REPEATED_EVIDENCE")
        self.assertEqual(r["opportunities"][0]["historical_confirmation"]["observation_count"],3)
    def test_no_confirmation(self):
        r=enrich_opportunities({"opportunities":[{"instrument_id":"EQ1","type":"T","evidence_families":["A","B"]}]},{"patterns":[]})
        self.assertEqual(r["opportunities"][0]["historical_confirmation"]["status"],"NO_CROSS_SNAPSHOT_CONFIRMATION")
    def test_no_score_or_direction(self):
        r=enrich_opportunities({"opportunities":[{"instrument_id":"EQ1","type":"T","evidence_families":["A","B"]}]})
        h=r["opportunities"][0]["historical_confirmation"]
        self.assertEqual(h["direction_inference"],"DISABLED")
        self.assertEqual(h["score_change"],"NONE")

if __name__=="__main__": unittest.main()
