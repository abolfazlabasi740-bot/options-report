import tempfile
import unittest
from pathlib import Path

from case_lifecycle_shadow import append_events, current_state


class CaseLifecycleTests(unittest.TestCase):
    def test_new_persistent_strengthening_resolved_and_recurring(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lifecycle.jsonl"
            c = {
                "case_id": "S1:C:ضتست1",
                "symbol": "ضتست1",
                "type": "RELATIVE_VALUE_ANOMALY",
                "status": "WATCH",
            }
            first = append_events(path, "S1", [c])
            self.assertEqual(first["states"], ["NEW"])

            c2 = dict(c, case_id="S2:C:ضتست1", status="CONFIRMED")
            second = append_events(path, "S2", [c2])
            self.assertIn("STRENGTHENING", second["states"])

            append_events(path, "S3", [])
            state = current_state(path)
            self.assertEqual(state["RELATIVE_VALUE_ANOMALY::ضتست1"]["state"], "RESOLVED")

            third = append_events(path, "S4", [dict(c2, case_id="S4:C:ضتست1")])
            self.assertIn("RECURRING", third["states"])

    def test_same_status_is_persistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lifecycle.jsonl"
            c = {"case_id": "S1:C:X", "symbol": "X", "type": "T", "status": "WATCH"}
            append_events(path, "S1", [c])
            result = append_events(path, "S2", [dict(c, case_id="S2:C:X")])
            self.assertIn("PERSISTENT", result["states"])


if __name__ == "__main__":
    unittest.main()
