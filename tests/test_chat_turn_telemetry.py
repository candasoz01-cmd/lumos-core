"""Sohbet turu telemetrisi: intent + reply tek JSONL kaydında."""

import tempfile
from pathlib import Path

from kando_runtime.lumos_audit import (
    CHAT_TURN_TELEMETRY_SCHEMA,
    append_chat_turn_telemetry,
    find_audit_entry,
)


def test_append_chat_turn_telemetry_single_record_links_intent_and_reply():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        log_id = append_chat_turn_telemetry(
            root,
            user_message="selam",
            intent="Kullanıcıyı selamlamak.",
            reply="Merhaba!",
            model="test-model",
        )
        assert len(log_id) == 32
        found = find_audit_entry(root, log_id)
        assert found is not None
        assert found.get("schema_version") == CHAT_TURN_TELEMETRY_SCHEMA
        assert found.get("intent") == "Kullanıcıyı selamlamak."
        assert found.get("reply") == "Merhaba!"
        assert found.get("user_message") == "selam"
        assert found.get("model") == "test-model"
        assert found.get("mode") == "chat"
        assert found.get("blocked") is False


def test_append_chat_turn_telemetry_truncates_long_user_message():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        long_msg = "x" * 20_000
        log_id = append_chat_turn_telemetry(
            root,
            user_message=long_msg,
            intent="i",
            reply="r",
        )
        found = find_audit_entry(root, log_id)
        assert found is not None
        assert len(found["user_message"]) == 10_000
