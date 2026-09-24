import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import live_capture_harness as harness


class LiveCaptureHarnessTests(unittest.TestCase):
    def test_capture_isolated_from_project_adapter(self):
        payload = {
            "bestLimits": [
                {"zo": 1, "zd": 2, "pd": 1000, "po": 1010, "qd": 100, "qo": 200}
            ]
        }

        class FakeResponse:
            status = 200
            def read(self):
                return json.dumps(payload).encode("utf-8")
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        with patch("live_capture_harness.urllib.request.urlopen", return_value=FakeResponse()):
            result = harness.capture("123", "https://example.test/api", 1)

        self.assertEqual(result["source"], "TSETMC")
        self.assertEqual(result["instrument_id"], "123")
        self.assertEqual(result["level_count"], 1)
        self.assertEqual(result["raw_levels"], payload["bestLimits"])
        self.assertEqual(result["raw_payload"], payload)
        self.assertEqual(result["payload_sha256"], harness.sha256_json(payload))
        self.assertEqual(result["semantic_mapping_status"], "OPEN")
        self.assertEqual(result["scoring_status"], "BLOCKED")
        self.assertEqual(len(result["payload_sha256"]), 64)

    def test_capture_rejects_missing_bestlimits(self):
        payload = {"other": []}

        class FakeResponse:
            status = 200
            def read(self):
                return json.dumps(payload).encode("utf-8")
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        with patch("live_capture_harness.urllib.request.urlopen", return_value=FakeResponse()):
            with self.assertRaises(RuntimeError):
                harness.capture("123", "https://example.test/api", 1)


if __name__ == "__main__":
    unittest.main()
