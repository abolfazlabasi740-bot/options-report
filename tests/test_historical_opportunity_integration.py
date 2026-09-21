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
        previous = build_snapshot("S1", [{"نماد": "ضتست1", "FinalScore": 55.0, "DataConfidence": 90.0, "RemainingDays": 10, "last_price": 100, "volume": 100}])
        middle1 = build_snapshot("S2", [{"نماد": "ضتست1", "FinalScore": 56.0, "DataConfidence": 93.0, "RemainingDays": 9, "last_price": 102, "volume": 110}])
        middle2 = build_snapshot("S3", [{"نماد": "ضتست1", "FinalScore": 58.0, "DataConfidence": 96.0, "RemainingDays": 8, "last_price": 104, "volume": 120}])
        current = build_snapshot("S4", [{"نماد": "ضتست1", "FinalScore": 60.0, "DataConfidence": 100.0, "RemainingDays": 7, "last_price": 106, "volume": 130}])

        result = run_shadow(
            scored,
            "S2",
            historical_previous=previous,
            historical_current=current,
            historical_sequence=[previous, middle1, middle2, current],
        )

        self.assertEqual(result["historical_context"]["status"], "SUCCESS")
        self.assertEqual(
            result["historical_context"]["cases"][0]["historical_state"],
            "PERSISTENT_IN_CURRENT_SEQUENCE",
        )
        self.assertEqual(scored.iloc[0]["FinalScore"], 60.0)
        self.assertEqual(result["historical_patterns"]["status"], "SUCCESS")
        pattern_types = {item["type"] for item in result["historical_patterns"]["patterns"]}
        self.assertIn("FINALSCORE_UP_SEQUENCE", pattern_types)


if __name__ == "__main__":
    unittest.main()
