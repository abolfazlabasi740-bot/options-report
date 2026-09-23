import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tsetmc_live_smoke


class TSETMCLiveSmokeTests(unittest.TestCase):
    def test_smoke_persists_source_evidence_without_network(self):
        class Adapter:
            def market_overview(self, flow=0):
                return {
                    "source": "TSETMC",
                    "endpoint": "https://example.invalid",
                    "snapshot_sha256": "abc123",
                    "data": {"ok": True},
                }

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "smoke.json"
            with patch.object(tsetmc_live_smoke, "TSETMCAdapter", return_value=Adapter()):
                with patch("sys.argv", ["tsetmc_live_smoke.py", "--output", str(target)]):
                    tsetmc_live_smoke.main()
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "SUCCESS")
            self.assertEqual(payload["snapshot_sha256"], "abc123")
            self.assertTrue(payload["data_present"])
            self.assertEqual(payload["explicit_ins_code_count"], 0)
            self.assertEqual(payload["explicit_option_record_count"], 0)
            self.assertTrue((target.with_suffix(".raw.json")).exists())

    def test_option_market_watch_collects_explicit_identity_without_inference(self):
        class Adapter:
            def option_market_watch(self, flow=0):
                return {
                    "source": "TSETMC",
                    "endpoint": "https://example.invalid/option-watch/1",
                    "snapshot_sha256": "def456",
                    "data": {
                        "instrumentOptMarketWatch": [{
                            "insCode_P": "P123",
                            "insCode_C": "C456",
                            "uaInsCode": "UA789",
                            "lVal18AFC_P": "طهرم7050",
                            "lVal18AFC_C": "ضهرم7050",
                        }]
                    },
                }

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "option_watch.json"
            with patch.object(tsetmc_live_smoke, "TSETMCAdapter", return_value=Adapter()):
                with patch(
                    "sys.argv",
                    ["tsetmc_live_smoke.py", "--option-market-watch", "--flow", "1", "--output", str(target)],
                ):
                    tsetmc_live_smoke.main()
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(payload["test"], "TSETMC_OPTION_MARKET_WATCH")
            self.assertEqual(payload["explicit_option_record_count"], 1)
            self.assertEqual(
                payload["explicit_option_records"],
                [{"insCode_P": "P123", "insCode_C": "C456", "uaInsCode": "UA789"}],
            )
            self.assertIn("P123", payload["explicit_ins_codes"])
            self.assertIn("C456", payload["explicit_ins_codes"])
            self.assertIn("UA789", payload["explicit_ins_codes"])


if __name__ == "__main__":
    unittest.main()
