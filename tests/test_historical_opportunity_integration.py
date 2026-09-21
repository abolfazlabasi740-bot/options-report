import tempfile
import unittest
from pathlib import Path

import pandas as pd

from historical_snapshot import build_snapshot
from opportunity_engine import run_shadow


class HistoricalOpportunityIntegrationTests(unittest.TestCase):
    def test_historical_context_is_attached_without_score_mutation(self):
        scored = pd.DataFrame([
            {
                "نماد": "ضتست1",
                "FinalScore": 60.0,
                "DataConfidence": 100.0,
                "AnalyticsFlags": "",
            }
        ])
        previous = build_snapshot(
            "S1",
            [{
                "نماد": "ضتست1",
                "FinalScore": 55.0,
                "DataConfidence": 90.0,
                "RemainingDays": 10,
            }],
        )
        current = build_snapshot(
            "S2",
            [{
                "نماد": "ضتست1",
                "FinalScore": 60.0,
                "DataConfidence": 100.0,
                "RemainingDays": 9,
            }],
        )

        result = run_shadow(
            scored,
            "S2",
            historical_previous=previous,
            historical_current=current,
        )

        self.assertEqual(result["historical_context"]["status"], "SUCCESS")
        self.assertEqual(
            result["historical_context"]["cases"][0]["historical_state"],
            "PERSISTENT_IN_CURRENT_SEQUENCE",
        )
        self.assertEqual(scored.iloc[0]["FinalScore"], 60.0)


if __name__ == "__main__":
    unittest.main()
