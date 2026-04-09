"""POST /chat: build_chat_reply (OpenAI mock)."""
from unittest.mock import MagicMock, patch

from kando_bridge.server import build_chat_reply


def test_build_chat_reply_success():
    fake_r1 = MagicMock()
    fake_r1.output_text = "INTENT: Kullanıcıyı selamlamak."
    fake_r2 = MagicMock()
    fake_r2.output_text = "Merhaba!"
    fake_client = MagicMock()
    fake_client.responses.create.side_effect = [fake_r1, fake_r2]
    with patch("openai.OpenAI", return_value=fake_client):
        r = build_chat_reply("selam")
    assert r == {
        "reply": "Merhaba!",
        "blocked": False,
        "mode": "chat",
        "intent": "Kullanıcıyı selamlamak.",
    }
    assert fake_client.responses.create.call_count == 2
    calls = fake_client.responses.create.call_args_list
    assert "Kısa ve doğal cevap ver: selam" in calls[0].kwargs["input"]
    assert "[Adım 1 — yalnızca iç karar]" in calls[0].kwargs["input"]
    assert "Sen Lumos'sun" in calls[0].kwargs["input"]
    assert "Kilit INTENT" in calls[1].kwargs["input"]
    assert "Kullanıcıyı selamlamak." in calls[1].kwargs["input"]
    assert "model" in calls[0].kwargs


def test_build_chat_reply_empty_step1_uses_fallback_intent():
    fake_r1 = MagicMock()
    fake_r1.output_text = ""
    fake_r2 = MagicMock()
    fake_r2.output_text = "Tamam."
    fake_client = MagicMock()
    fake_client.responses.create.side_effect = [fake_r1, fake_r2]
    with patch("openai.OpenAI", return_value=fake_client):
        r = build_chat_reply("x")
    assert r["reply"] == "Tamam."
    assert r["intent"] == "Kullanıcıya mesajına uygun kısa ve yardımcı cevap vermek."


def test_build_chat_reply_appends_current_message_when_not_last_in_history():
    """history + ayrı message (curl); son soru transcript'te olmalı."""
    fake_r1 = MagicMock()
    fake_r1.output_text = "INTENT: y."
    fake_r2 = MagicMock()
    fake_r2.output_text = "x"
    fake_client = MagicMock()
    fake_client.responses.create.side_effect = [fake_r1, fake_r2]
    history = [
        {"role": "user", "content": "Benim adım Kando"},
        {"role": "assistant", "content": "Memnun oldum Kando"},
    ]
    with patch("openai.OpenAI", return_value=fake_client):
        build_chat_reply("Adım neydi?", history)
    inp0 = fake_client.responses.create.call_args_list[0].kwargs["input"]
    assert "Kullanıcı: Adım neydi?" in inp0


def test_build_chat_reply_with_history_sends_full_transcript():
    fake_r1 = MagicMock()
    fake_r1.output_text = "INTENT: z."
    fake_r2 = MagicMock()
    fake_r2.output_text = "ok"
    fake_client = MagicMock()
    fake_client.responses.create.side_effect = [fake_r1, fake_r2]
    history = [
        {"role": "user", "content": "Adın ne?"},
        {"role": "assistant", "content": "Merhaba."},
        {"role": "user", "content": "Ben Ali"},
    ]
    with patch("openai.OpenAI", return_value=fake_client):
        build_chat_reply("Ben Ali", history)
    inp0 = fake_client.responses.create.call_args_list[0].kwargs["input"]
    inp1 = fake_client.responses.create.call_args_list[1].kwargs["input"]
    for inp in (inp0, inp1):
        assert "Kullanıcı: Adın ne?" in inp
        assert "Asistan: Merhaba." in inp
        assert "Kullanıcı: Ben Ali" in inp


def test_build_chat_reply_propagates_error():
    with patch("openai.OpenAI", side_effect=RuntimeError("no key")):
        try:
            build_chat_reply("x")
        except RuntimeError as e:
            assert "no key" in str(e)
        else:
            raise AssertionError("expected RuntimeError")
