import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_verification


class RuntimeVerificationTests(unittest.TestCase):
    def test_environment_presence_is_boolean_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "report_engine.py").write_text("x = 1\n", encoding="utf-8")
            with patch.object(runtime_verification, "ROOT", root):
                with patch.dict(
                    runtime_verification.os.environ,
                    {"BALE_BOT_TOKEN": "SECRET", "BALE_CHAT_ID": "123"},
                    clear=False,
                ):
                    result = runtime_verification._compile(["report_engine.py"])
                    self.assertEqual(result["report_engine.py"], "OK")

    def test_git_lookup_failure_is_non_fatal(self):
        with patch(
            "runtime_verification.subprocess.check_output",
            side_effect=RuntimeError("no git"),
        ):
            self.assertIsNone(runtime_verification._git_sha())


if __name__ == "__main__":
    unittest.main()
