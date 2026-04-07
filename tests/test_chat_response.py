"""POST /chat: build_chat_reply (OpenAI mock)."""
from unittest.mock import MagicMock, patch

from kando_bridge.server import build_chat_reply


def test_build_chat_reply_success():
    fake_resp = MagicMock()
    fake_resp.output_text = "  Merhaba!  "
    fake_client = MagicMock()
    fake_client.responses.create.return_value = fake_resp
    with patch("openai.OpenAI", return_value=fake_client):
        r = build_chat_reply("selam")
    assert r == {"reply": "Merhaba!", "blocked": False, "mode": "chat"}
    fake_client.responses.create.assert_called_once()
    call_kw = fake_client.responses.create.call_args.kwargs
    assert "Kısa ve doğal cevap ver: selam" in call_kw["input"]
    assert "Sen Lumos'sun" in call_kw["input"]
    assert "model" in call_kw


def test_build_chat_reply_appends_current_message_when_not_last_in_history():
    """history + ayrı message (curl); son soru transcript'te olmalı."""
    fake_resp = MagicMock()
    fake_resp.output_text = "x"
    fake_client = MagicMock()
    fake_client.responses.create.return_value = fake_resp
    history = [
        {"role": "user", "content": "Benim adım Kando"},
        {"role": "assistant", "content": "Memnun oldum Kando"},
    ]
    with patch("openai.OpenAI", return_value=fake_client):
        build_chat_reply("Adım neydi?", history)
    inp = fake_client.responses.create.call_args.kwargs["input"]
    assert "Kullanıcı: Adım neydi?" in inp


def test_build_chat_reply_with_history_sends_full_transcript():
    fake_resp = MagicMock()
    fake_resp.output_text = "ok"
    fake_client = MagicMock()
    fake_client.responses.create.return_value = fake_resp
    history = [
        {"role": "user", "content": "Adın ne?"},
        {"role": "assistant", "content": "Merhaba."},
        {"role": "user", "content": "Ben Ali"},
    ]
    with patch("openai.OpenAI", return_value=fake_client):
        build_chat_reply("Ben Ali", history)
    inp = fake_client.responses.create.call_args.kwargs["input"]
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
