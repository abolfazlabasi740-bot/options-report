import json
import tempfile
import unittest
from unittest.mock import patch

from scripts.reconcile_tsetmc_option_universe import _candidate_records, run
from pathlib import Path


class UniverseReconciliationTests(unittest.TestCase):
    def test_candidate_records_require_explicit_option_identity(self):
        payload = {
            "marketWatch": [
                {"insCode_P": "P1", "insCode_C": "C1", "uaInsCode": "U1"},
                {"insCode": "OTHER"},
            ]
        }
        self.assertEqual(len(_candidate_records(payload)), 1)

    def test_run_does_not_change_production_universe(self):
        from pathlib import Path
        fake = {
            "flows": [0, 1, 2, 4],
            "record_count": 2,
            "flow_evidence": [],
            "snapshot_sha256": "flowsha",
            "retrieved_at": "2026-09-27T00:00:00Z",
        }
        class Response:
            endpoint = "https://example/MarketData/GetMarketWatch"
            sha256 = "rawsha"
            retrieved_at = "2026-09-27T00:00:00Z"
            payload = {"marketWatch": [{"insCode_P": "P1", "insCode_C": "C1"}]}
        with tempfile.TemporaryDirectory(prefix="optimus_reconcile_test_") as tempdir:
            test_output = Path(tempdir) / "universe_reconciliation.json"
            with patch("scripts.reconcile_tsetmc_option_universe.OUT", test_output), \
                 patch("scripts.reconcile_tsetmc_option_universe.TSETMCAdapter") as Adapter:
                instance = Adapter.return_value
                instance._request.return_value = Response()
                instance.option_market_watch_universe.return_value = fake
                result = run()
            self.assertTrue(test_output.is_file())
        self.assertTrue(result["interpretation"]["production_universe_changed"] is False)
        self.assertEqual(result["validated_option_universe"]["record_count"], 2)


if __name__ == "__main__":
    unittest.main()
