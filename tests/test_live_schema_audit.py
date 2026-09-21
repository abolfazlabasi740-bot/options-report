import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from live_schema_audit import audit_live


class LiveSchemaAuditTests(unittest.TestCase):
    def test_live_audit_records_metadata_and_deletes_raw_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder) / ".live.xlsx"
            data = pd.DataFrame({
                "نماد": ["ضتست1"],
                "قیمت اعمال": [1000],
                "تاریخ سررسید": ["1405/07/30"],
                "قیمت سهم پایه": [1050],
            })

            class Response:
                content = b"PK" + (b"x" * 6000)

                def raise_for_status(self):
                    return None

            with patch("live_schema_audit.requests.get", return_value=Response()):
                with patch("live_schema_audit.pd.read_excel", return_value=data):
                    result = audit_live("https://example.invalid/source", temp)

            self.assertEqual(result["status"], "SUCCESS")
            self.assertEqual(result["row_count"], 1)
            self.assertEqual(result["column_count"], 4)
            self.assertEqual(result["audit"]["identity_readiness"], "INSUFFICIENT_DATA")
            self.assertFalse(temp.exists())


if __name__ == "__main__":
    unittest.main()
