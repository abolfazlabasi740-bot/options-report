import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.verify_optionschool_identity_readiness import inspect_workbook


class OptionSchoolIdentityReadinessTests(unittest.TestCase):
    def test_no_explicit_id_does_not_infer_from_symbol(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "options.xlsx"
            pd.DataFrame({"نماد": ["ضهرم7050"], "قیمت اعمال": [20000]}).to_excel(path, index=False)
            result = inspect_workbook(path)
            self.assertEqual(result["status"], "NO_EXPLICIT_OPTION_ID")
            self.assertFalse(result["promotion_ready"])
            self.assertEqual(result["identity_inference"], "DISABLED")

    def test_explicit_id_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "options.xlsx"
            pd.DataFrame({"نماد": ["ضهرم7050"], "insCode": ["62444611500832644"]}).to_excel(path, index=False)
            result = inspect_workbook(path)
            self.assertEqual(result["status"], "EXPLICIT_ID_AVAILABLE")
            self.assertTrue(result["promotion_ready"])
            self.assertEqual(result["populated_id_counts"]["insCode"], 1)


if __name__ == "__main__":
    unittest.main()
