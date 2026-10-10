import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bale_listener


class BaleListenerStateTests(unittest.TestCase):
    def test_active_menu_contains_only_two_ranking_glass_buttons(self):
        self.assertEqual(
            bale_listener.MENU_MARKUP,
            {
                "inline_keyboard": [[{
                    "text": bale_listener.MARKET_SHARES_LABEL,
                    "callback_data": "market_shares_page:0",
                }], [{
                    "text": bale_listener.OPTION_SHARES_LABEL,
                    "callback_data": "option_shares",
                }]]
            },
        )
        self.assertEqual(
            bale_listener.REPLY_MENU_COMMANDS[bale_listener.MARKET_SHARES_LABEL],
            "market_shares",
        )
        self.assertEqual(
            bale_listener.REPLY_MENU_COMMANDS[bale_listener.OPTION_SHARES_LABEL],
            "option_shares",
        )

    def test_option_callback_routes_open_and_pages(self):
        for data, expected_page, refresh in (("option_shares", 0, True), ("option_shares_page:1", 1, False), ("option_shares_page:0", 0, False)):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                update = {"update_id": 50, "callback_query": {"id": "cb", "data": data, "message": {"chat": {"id": 123}}}}
                with (
                    patch.object(bale_listener, "OUTPUT", root),
                    patch.object(bale_listener, "STATE_FILE", root / "state.json"),
                    patch.object(bale_listener, "TOKEN", "token"),
                    patch.object(bale_listener, "CHAT_ID", "123"),
                    patch.object(bale_listener, "get_updates", side_effect=[[update], KeyboardInterrupt]),
                    patch.object(bale_listener, "answer_callback_query"),
                    patch.object(bale_listener, "render_option_base_cards", return_value=("REPORT", {}, 26, expected_page, 3)) as renderer,
                    patch.object(bale_listener, "send_message") as sender,
                    patch.object(bale_listener, "send_report_menu"),
                ):
                    bale_listener.main()
                renderer.assert_called_once_with(expected_page, refresh=refresh)
                sender.assert_called_once_with(123, "REPORT", reply_markup={})
                self.assertEqual(json.loads((root / "state.json").read_text())["next_offset"], 51)

    def test_successful_update_commits_offset(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            state = root / "bale_listener_state.json"
            update = {"update_id": 41, "message": {"chat": {"id": 123}, "text": "market_shares"}}
            with (
                patch.object(bale_listener, "OUTPUT", root),
                patch.object(bale_listener, "STATE_FILE", state),
                patch.object(bale_listener, "TOKEN", "token"),
                patch.object(bale_listener, "CHAT_ID", "123"),
                patch.object(bale_listener, "get_updates", side_effect=[[update], KeyboardInterrupt]),
                patch.object(bale_listener, "render_market_share_cards", return_value=("REPORT", {}, 1, 0, 1)),
                patch.object(bale_listener, "send_message"),
                patch.object(bale_listener, "send_report_menu"),
            ):
                bale_listener.main()
            self.assertEqual(json.loads(state.read_text())["next_offset"], 42)

    def test_failed_update_is_not_committed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            state = root / "bale_listener_state.json"
            update = {"update_id": 41, "message": {"chat": {"id": 123}, "text": "market_shares"}}
            with (
                patch.object(bale_listener, "OUTPUT", root),
                patch.object(bale_listener, "STATE_FILE", state),
                patch.object(bale_listener, "TOKEN", "token"),
                patch.object(bale_listener, "CHAT_ID", "123"),
                patch.object(bale_listener, "get_updates", side_effect=[[update], KeyboardInterrupt]),
                patch.object(bale_listener, "render_market_share_cards", side_effect=RuntimeError("failure")),
                patch.object(bale_listener, "send_message", side_effect=RuntimeError("delivery failure")),
                patch.object(bale_listener, "send_report_menu"),
            ):
                bale_listener.main()
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
