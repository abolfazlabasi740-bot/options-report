import unittest
from unittest.mock import patch
import bale_transport


class BaleTransportTests(unittest.TestCase):
    def test_split_message_preserves_all_content(self):
        text = "HEADER\n" + "🔹 A\n" + ("x" * 120) + "\n" + "🔹 B\n" + ("y" * 120)
        chunks = bale_transport.split_message(text, limit=100)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), text)

    def test_send_message_posts_all_chunks(self):
        text = "🔹 A\n" + ("x" * 80) + "\n🔹 B\n" + ("y" * 80)
        class Response:
            def raise_for_status(self):
                return None
            def json(self):
                return {"ok": True}
        with patch("bale_transport.requests.post", return_value=Response()) as post:
            count = bale_transport.send_message("TOKEN", "CHAT", text)
        self.assertGreaterEqual(count, 2)
        self.assertEqual(post.call_count, count)
        for call in post.call_args_list:
            self.assertIn("/botTOKEN/sendMessage", call.args[0])
            self.assertEqual(call.kwargs["data"]["chat_id"], "CHAT")

    def test_send_message_fails_closed_on_http_error(self):
        with patch("bale_transport.requests.post", side_effect=Exception("network")):
            with self.assertRaises(Exception):
                bale_transport.send_message("TOKEN", "CHAT", "test")


if __name__ == "__main__":
    unittest.main()
