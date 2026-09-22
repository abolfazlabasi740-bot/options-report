import unittest
from equity_memory_shadow import build_memory

class MemoryTests(unittest.TestCase):
    def test_new(self):
        r=build_memory([{"historical_confirmation":{"status":"NO_CROSS_SNAPSHOT_CONFIRMATION"}}])
        self.assertEqual(r["opportunities"][0]["historical_memory"]["level"],"NEW_OR_UNCONFIRMED")
    def test_repeated(self):
        r=build_memory([{"historical_confirmation":{"status":"REPEATED_EVIDENCE","observation_count":2,"pattern_type":"PERSISTENT_OR_STRENGTHENING"}}])
        self.assertEqual(r["opportunities"][0]["historical_memory"]["level"],"PERSISTENT_OR_STRENGTHENING")
    def test_recurring(self):
        r=build_memory([{"historical_confirmation":{"status":"REPEATED_EVIDENCE","observation_count":4,"recurrence_count":1,"pattern_type":"RECURRING_PATTERN"}}])
        self.assertEqual(r["opportunities"][0]["historical_memory"]["level"],"RECURRING")
    def test_oscillating(self):
        r=build_memory([{"historical_confirmation":{"status":"REPEATED_EVIDENCE","observation_count":3,"pattern_type":"OSCILLATING_PATTERN"}}])
        self.assertEqual(r["opportunities"][0]["historical_memory"]["level"],"OSCILLATING")
    def test_no_score_direction(self):
        r=build_memory([{"historical_confirmation":{"status":"REPEATED_EVIDENCE","observation_count":2}}])
        h=r["opportunities"][0]["historical_memory"]
        self.assertEqual(h["direction_inference"],"DISABLED")
        self.assertEqual(h["score_change"],"NONE")

if __name__=="__main__": unittest.main()
