import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bale_listener


class BaleListenerStateTests(unittest.TestCase):
    def test_successful_update_commits_offset(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            state = root / "bale_listener_state.json"
            update = {"update_id": 41, "message": {"chat": {"id": 123}, "text": "گزارش"}}
            with (
                patch.object(bale_listener, "OUTPUT", root),
                patch.object(bale_listener, "STATE_FILE", state),
                patch.object(bale_listener, "TOKEN", "token"),
                patch.object(bale_listener, "CHAT_ID", "123"),
                patch.object(bale_listener, "get_updates", side_effect=[[update], KeyboardInterrupt]),
                patch.object(bale_listener, "generate_report", return_value="REPORT"),
                patch.object(bale_listener, "send_message"),
            ):
                bale_listener.main()
            self.assertEqual(json.loads(state.read_text())["next_offset"], 42)

    def test_failed_update_is_not_committed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            state = root / "bale_listener_state.json"
            update = {"update_id": 41, "message": {"chat": {"id": 123}, "text": "گزارش"}}
            with (
                patch.object(bale_listener, "OUTPUT", root),
                patch.object(bale_listener, "STATE_FILE", state),
                patch.object(bale_listener, "TOKEN", "token"),
                patch.object(bale_listener, "CHAT_ID", "123"),
                patch.object(bale_listener, "get_updates", side_effect=[[update], KeyboardInterrupt]),
                patch.object(bale_listener, "generate_report", side_effect=RuntimeError("failure")),
                patch.object(bale_listener, "send_message", side_effect=RuntimeError("delivery failure")),
            ):
                bale_listener.main()
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
