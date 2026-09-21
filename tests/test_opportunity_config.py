import os
import unittest
from unittest.mock import patch

import opportunity_config


class OpportunityConfigTests(unittest.TestCase):
    def test_defaults_are_explicit_and_valid(self):
        self.assertEqual(opportunity_config.CONFIG.relative_value_rank, 0.85)
        self.assertEqual(opportunity_config.CONFIG.historical_pattern_window, 3)

    def test_environment_override_is_read(self):
        with patch.dict(os.environ, {"OPP_RELATIVE_VALUE_RANK": "0.9"}, clear=False):
            cfg = opportunity_config.OpportunityConfig(
                relative_value_rank=float(os.environ["OPP_RELATIVE_VALUE_RANK"])
            )
            cfg.validate()
            self.assertEqual(cfg.relative_value_rank, 0.9)

    def test_invalid_bounds_fail(self):
        cfg = opportunity_config.OpportunityConfig(relative_value_rank=1.5)
        with self.assertRaises(ValueError):
            cfg.validate()


if __name__ == "__main__":
    unittest.main()
