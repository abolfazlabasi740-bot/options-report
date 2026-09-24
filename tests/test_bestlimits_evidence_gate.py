import copy
import unittest

import bestlimits_evidence_gate as gate


class BestLimitsEvidenceGateTests(unittest.TestCase):
    def _capture(self, instrument_id, timestamp):
        payload = {"bestLimits": [{"zo": 1, "zd": 2, "pd": 1000, "po": 1010, "qd": 100, "qo": 200}]}
        return {
            "source": "TSETMC",
            "instrument_id": instrument_id,
            "endpoint": f"https://cdn.tsetmc.com/api/BestLimits/{instrument_id}",
            "capture_started_at_utc": timestamp,
            "retrieved_at_utc": timestamp,
            "payload_sha256": gate.sha256_json(payload),
            "raw_payload": payload,
            "level_count": 1,
            "raw_levels": payload["bestLimits"],
            "semantic_mapping_status": "OPEN",
            "scoring_status": "BLOCKED",
        }

    def _package(self):
        captures = []
        for iid, role in [("o1", "option"), ("o2", "option"), ("o3", "option"), ("u1", "underlying")]:
            captures.extend([self._capture(iid, "2026-09-24T10:00:00+00:00"), self._capture(iid, "2026-09-24T10:01:00+00:00")])
        return {
            "captures": captures,
            "instrument_roles": {"o1": "option", "o2": "option", "o3": "option", "u1": "underlying"},
            "independent_semantic_evidence": [{"instrument_id": "o1", "capture_timestamp_utc": "2026-09-24T10:00:00+00:00", "evidence_source": "TEST_ONLY", "evidence_location": "synthetic://unit-test"}],
        }

    def test_complete_package_is_ready_for_review_but_stays_blocked(self):
        result = gate.validate_package(self._package())
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertEqual(result["mapping_freeze"], "BLOCKED")
        self.assertEqual(result["scoring"], "BLOCKED")

    def test_payload_hash_mismatch_is_rejected(self):
        package = self._package()
        package["captures"][0]["raw_payload"] = copy.deepcopy(package["captures"][0]["raw_payload"])
        package["captures"][0]["raw_payload"]["bestLimits"][0]["pd"] = 999
        result = gate.validate_package(package)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertIn("capture[0]:payload_sha256_mismatch", result["errors"])


if __name__ == "__main__":
    unittest.main()
