import unittest

import pandas as pd

from replay_engine import verify_shadow_replay


class ReplayEngineTests(unittest.TestCase):
    def test_shadow_replay_is_deterministic(self):
        scored = pd.DataFrame([
            {
                "نماد": "ضتست1",
                "FinalScore": 60.0,
                "DataConfidence": 100.0,
                "AnalyticsFlags": "",
            }
        ])
        result = verify_shadow_replay(scored, "S1")
        self.assertEqual(result["status"], "REPLAY_MATCH")
        self.assertTrue(result["deterministic"])

    def test_replay_changes_when_input_changes(self):
        first = pd.DataFrame([{
            "نماد": "ضتست1",
            "FinalScore": 60.0,
            "DataConfidence": 100.0,
            "AnalyticsFlags": "",
        }])
        second = first.copy()
        second.loc[0, "FinalScore"] = 61.0
        a = verify_shadow_replay(first, "S1")
        b = verify_shadow_replay(second, "S1")
        self.assertNotEqual(a["first_hash"], b["first_hash"])


if __name__ == "__main__":
    unittest.main()
