import unittest
from unittest.mock import patch

import termux_gate6_launcher as launcher


class TermuxGate6LauncherTests(unittest.TestCase):
    def test_fast_forward_then_runs_gate6(self):
        calls = []

        def fake_run(argv, capture=True):
            calls.append(argv)
            if argv == ["git", "branch", "--show-current"]:
                return "main"
            if argv == ["git", "status", "--porcelain"]:
                return ""
            if argv == ["git", "rev-parse", "HEAD"]:
                return "old"
            if argv == ["git", "rev-parse", "origin/main"]:
                return "new"
            return ""

        class Result:
            returncode = 0

        with (
            patch.object(launcher, "run", side_effect=fake_run),
            patch.object(launcher.subprocess, "run", return_value=Result()) as proc,
        ):
            launcher.main()

        self.assertIn(["git", "fetch", "--prune", "origin"], calls)
        self.assertIn(["git", "pull", "--ff-only", "origin", "main"], calls)
        proc.assert_called_once_with(
            [launcher.sys.executable, "gate6_runtime_verification.py"],
            cwd=launcher.ROOT,
            check=False,
            text=True,
        )

    def test_stops_on_tracked_local_changes(self):
        def fake_run(argv, capture=True):
            if argv == ["git", "branch", "--show-current"]:
                return "main"
            if argv == ["git", "status", "--porcelain"]:
                return " M report_engine.py"
            return ""

        with patch.object(launcher, "run", side_effect=fake_run):
            with self.assertRaises(RuntimeError):
                launcher.main()


if __name__ == "__main__":
    unittest.main()
