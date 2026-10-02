import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import bale_transport


class Response:
    def __init__(self, payload=None, status=200):
        self.status = status
        self._payload = json.dumps(payload or {"ok": True}).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class BaleTransportTests(unittest.TestCase):
    def test_split_message_preserves_all_content(self):
        text = "HEADER\n" + "🔹 A\n" + ("x" * 120) + "\n" + "🔹 B\n" + ("y" * 120)
        chunks = bale_transport.split_message(text, limit=100)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), text)

    def test_send_message_posts_all_chunks(self):
        text = "🔹 A\n" + ("x" * 1800) + "\n🔹 B\n" + ("y" * 1800)
        with patch("bale_transport.urlopen", return_value=Response({"ok": True})) as post:
            count = bale_transport.send_message("TOKEN", "CHAT", text)
        self.assertGreaterEqual(count, 2)
        self.assertEqual(post.call_count, count)
        for call in post.call_args_list:
            request = call.args[0]
            self.assertIn("/botTOKEN/sendMessage", request.full_url)
            self.assertIn(b"chat_id=CHAT", request.data)

    def test_send_message_can_return_non_secret_receipts(self):
        payload = {"ok": True, "result": {"message_id": 123, "chat": {"id": "CHAT"}}}
        with patch("bale_transport.urlopen", return_value=Response(payload)):
            receipts = bale_transport.send_message("TOKEN", "CHAT", "test", return_receipts=True)
        self.assertEqual(receipts, [{"message_id": 123, "chat_id": "CHAT"}])

    def test_send_message_supports_reply_keyboard(self):
        markup = {
            "keyboard": [[{"text": "📊 گزارش ۱۵ فرصت برتر"}]],
            "resize_keyboard": True,
            "one_time_keyboard": False,
        }
        with patch("bale_transport.urlopen", return_value=Response()) as post:
            bale_transport.send_message("TOKEN", "CHAT", "test", reply_markup=markup)
        data = post.call_args.args[0].data.decode("utf-8")
        self.assertIn("reply_markup=", data)
        self.assertIn("%D8%AF%D8%B1%D8%B5%D8%AA", data)

    def test_send_message_supports_inline_keyboard(self):
        markup = {"inline_keyboard": [[{"text": "گزارش", "callback_data": "report_ranked_15"}]]}
        with patch("bale_transport.urlopen", return_value=Response()) as post:
            bale_transport.send_message("TOKEN", "CHAT", "test", reply_markup=markup)
        data = post.call_args.args[0].data.decode("utf-8")
        self.assertIn("reply_markup=", data)
        self.assertIn("report_ranked_15", data)

    def test_send_message_reports_safe_network_error(self):
        with patch("bale_transport.urlopen", side_effect=URLError("network")):
            with self.assertRaisesRegex(RuntimeError, "NETWORK_ERROR=URLError"):
                bale_transport.send_message("TOKEN", "CHAT", "test")

    def test_send_message_reports_safe_api_rejection(self):
        with patch("bale_transport.urlopen", return_value=Response({"ok": False})):
            with self.assertRaisesRegex(RuntimeError, "REASON=API_REJECTED"):
                bale_transport.send_message("TOKEN", "CHAT", "test")

    def test_send_message_fails_closed_on_http_error(self):
        error = HTTPError(
            url="https://tapi.bale.ai/botTOKEN/sendMessage",
            code=500,
            msg="server error",
            hdrs=None,
            fp=io.BytesIO(),
        )
        with patch("bale_transport.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "HTTP_STATUS=500"):
                bale_transport.send_message("TOKEN", "CHAT", "test")


if __name__ == "__main__":
    unittest.main()
