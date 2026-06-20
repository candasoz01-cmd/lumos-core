"""panel_chat_errors sınıflandırması."""

from __future__ import annotations

import unittest

from core.panel_chat_errors import (
    classify_panel_chat_error,
    user_message_for_panel_chat_error,
)


class PanelChatErrorsTests(unittest.TestCase):
    def test_network_error(self) -> None:
        self.assertEqual(
            classify_panel_chat_error(err_name="TypeError", err_message="Failed to fetch"),
            "network_error",
        )

    def test_unauthorized_http(self) -> None:
        self.assertEqual(classify_panel_chat_error(http_status=401), "unauthorized")

    def test_model_error_upstream(self) -> None:
        self.assertEqual(
            classify_panel_chat_error(upstream_text="chat llm error: rate limit"),
            "model_error",
        )

    def test_user_messages_non_empty(self) -> None:
        for kind in (
            "network_error",
            "timeout",
            "unauthorized",
            "server_error",
            "model_error",
            "unknown_error",
        ):
            msg = user_message_for_panel_chat_error(kind)
            self.assertTrue(msg)
            self.assertNotIn("bağlantı katmanı", msg.lower())

    def test_user_messages_en_locale(self) -> None:
        msg = user_message_for_panel_chat_error("network_error", "en")
        self.assertIn("connection", msg.lower())
        self.assertNotIn("İletim", msg)


if __name__ == "__main__":
    unittest.main()
