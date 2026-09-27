import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bale_listener


class BaleListenerStateTests(unittest.TestCase):
    def test_reply_menu_mapping_is_deterministic(self):
        self.assertEqual(bale_listener.REPLY_MENU_COMMANDS["📊 گزارش ۱۵ فرصت برتر"], "گزارش")
        self.assertEqual(bale_listener.REPLY_MENU_COMMANDS["📈 گزارش ۱۵ قرارداد فعال"], "فعالیت")
        self.assertEqual(bale_listener.REPLY_MENU_COMMANDS["📋 وضعیت سیستم"], "وضعیت")

    def test_callback_menu_mapping_is_deterministic(self):
        self.assertEqual(bale_listener.CALLBACK_COMMANDS["report_ranked_15"], "گزارش")
        self.assertEqual(bale_listener.CALLBACK_COMMANDS["report_activity_15"], "فعالیت")
        self.assertEqual(bale_listener.CALLBACK_COMMANDS["system_status"], "وضعیت")

    def test_symbol_menu_uses_tsetmc_underlyings_and_paginates(self):
        rows = [
            {"identity": {"underlying_symbol": "وبملت"}},
            {"identity": {"underlying_symbol": "خودرو"}},
            {"identity": {"underlying_symbol": "وبملت"}},
            {"identity": {"underlying_symbol": "شستا"}},
        ]
        captured = {}

        def fake_send(chat_id, text, reply_markup=None):
            captured["chat_id"] = chat_id
            captured["text"] = text
            captured["markup"] = reply_markup

        with (
            patch.object(bale_listener, "build_tsetmc_snapshot", return_value={"rows": rows}),
            patch.object(bale_listener, "send_message", side_effect=fake_send),
        ):
            bale_listener.send_symbol_menu("123", 0)

        self.assertEqual(captured["chat_id"], "123")
        self.assertIn("تعداد نمادهای دارای اختیار معامله", captured["text"])
        self.assertIn("صفحه 1 از 1", captured["text"])
        buttons = [
            button["text"]
            for row in captured["markup"]["keyboard"]
            for button in row
        ]
        self.assertIn("نماد: خودرو", buttons)
        self.assertIn("نماد: شستا", buttons)
        self.assertIn("نماد: وبملت", buttons)
        self.assertEqual(captured["markup"]["one_time_keyboard"], False)

    def test_symbol_menu_uses_requested_priority_then_alphabetical_remainder(self):
        rows = [
            {"identity": {"underlying_symbol": "زملارد"}},
            {"identity": {"underlying_symbol": "وبصادر"}},
            {"identity": {"underlying_symbol": "اهرم"}},
            {"identity": {"underlying_symbol": "وبملت"}},
            {"identity": {"underlying_symbol": "فملی"}},
            {"identity": {"underlying_symbol": "شستا"}},
            {"identity": {"underlying_symbol": "خودرو"}},
            {"identity": {"underlying_symbol": "الف"}},
            {"identity": {"underlying_symbol": "تاصیکو"}},
            {"identity": {"underlying_symbol": "دزاگرس"}},
            {"identity": {"underlying_symbol": "دارونو"}},
            {"identity": {"underlying_symbol": "خبهمن"}},
            {"identity": {"underlying_symbol": "فزر"}},
            {"identity": {"underlying_symbol": "خساپا"}},
            {"identity": {"underlying_symbol": "ذوب"}},
            {"identity": {"underlying_symbol": "شپنا"}},
            {"identity": {"underlying_symbol": "وتجارت"}},
        ]

        with patch.object(
            bale_listener,
            "build_tsetmc_snapshot",
            return_value={"rows": rows},
        ):
            symbols = bale_listener._underlying_symbols()

        expected_prefix = [
            "اهرم",
            "وبملت",
            "وتجارت",
            "وبصادر",
            "فزر",
            "تاصیکو",
            "فملی",
            "شستا",
            "خودرو",
            "خساپا",
            "ذوب",
            "شپنا",
            "خبهمن",
            "دارونو",
            "دزاگرس",
        ]
        self.assertEqual(symbols[:len(expected_prefix)], expected_prefix)
        self.assertEqual(symbols[len(expected_prefix):], ["الف", "زملارد"])

    def test_symbol_selector_command_is_deterministic(self):
        self.assertEqual(bale_listener.REPLY_MENU_COMMANDS["🔎 انتخاب نماد"], "نمادها")


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
                patch.object(bale_listener, "send_report_menu"),
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
                patch.object(bale_listener, "send_report_menu"),
            ):
                bale_listener.main()
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
