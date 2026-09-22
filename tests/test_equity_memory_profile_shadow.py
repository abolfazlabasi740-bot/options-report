import unittest
from equity_memory_profile_shadow import build_memory_profiles

class MemoryProfileTests(unittest.TestCase):
    def test_single(self):
        r=build_memory_profiles([{"instrument_id":"E","type":"T","historical_memory":{"level":"NEW_OR_UNCONFIRMED"}}])
        self.assertEqual(r["profiles"][0]["continuity"],"SINGLE_OR_UNCONFIRMED")
    def test_repeated(self):
        r=build_memory_profiles([{"instrument_id":"E","type":"T","historical_memory":{"level":"REPEATED","observation_count":2}}])
        self.assertEqual(r["profiles"][0]["continuity"],"REPEATED")
    def test_recurring(self):
        r=build_memory_profiles([{"instrument_id":"E","type":"T","historical_memory":{"level":"RECURRING","observation_count":4,"recurrence_count":1}}])
        self.assertEqual(r["profiles"][0]["continuity"],"RECURRING")
    def test_no_direction_score(self):
        r=build_memory_profiles([{"instrument_id":"E","type":"T","historical_memory":{"level":"REPEATED","observation_count":2}}])
        self.assertEqual(r["profiles"][0]["direction_inference"],"DISABLED")
        self.assertEqual(r["profiles"][0]["score_change"],"NONE")

if __name__=="__main__": unittest.main()
