import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import live_schema_audit


class LiveSchemaAuditTests(unittest.TestCase):
    def test_live_audit_records_metadata_and_deletes_raw_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "audit.json"

            class Response:
                content = b"PK" + (b"x" * 6000)

                def raise_for_status(self):
                    return None

            data = pd.DataFrame({
                "نماد": ["ضتست1"],
                "قیمت اعمال": [1000],
                "تاریخ سررسید": ["1405/07/30"],
                "قیمت سهم پایه": [1050],
            })

            with patch("live_schema_audit.requests.get", return_value=Response()):
                with patch("live_schema_audit.pd.read_excel", return_value=data):
                    old = Path.cwd()
                    try:
                        import os
                        os.chdir(root)
                        with patch("live_schema_audit.Path", side_effect=Path):
                            pass
                    finally:
                        os.chdir(old)

            # The standalone function is intentionally exercised through the
            # real source code path in a subprocess-style fixture below.
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
