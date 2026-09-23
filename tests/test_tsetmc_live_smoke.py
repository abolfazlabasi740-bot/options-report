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
            self.assertTrue((target.with_suffix(".raw.json")).exists())


if __name__ == "__main__":
    unittest.main()