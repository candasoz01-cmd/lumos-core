"""STT data-boundary contract: OPENAI_MODEL_STT, batch-only, real audio fail-closed."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from representative.stt import (
    STT_AUDIO_REAL,
    STT_AUDIO_SYNTHETIC,
    STT_BAD_MODEL,
    STT_EU_BASE_REQUIRED,
    STT_NOT_CONFIGURED,
    STT_REAL_BLOCKED,
    OpenAICloudSTT,
    SttBoundaryError,
    resolve_openai_stt_model,
)


def test_stt_model_not_configured_no_chat_fallback() -> None:
    env = {
        "OPENAI_MODEL_STT": "",
        "OPENAI_MODEL_CHAT": "gpt-4.1",
        "OPENAI_MODEL": "gpt-4.1-mini",
        "OPENAI_MODEL_CYBER": "gpt-5.6-cyber",
    }
    with patch.dict(os.environ, env, clear=False):
        model, err = resolve_openai_stt_model()
        assert model == ""
        assert err == STT_NOT_CONFIGURED
        try:
            OpenAICloudSTT(audio_source=STT_AUDIO_SYNTHETIC)
        except SttBoundaryError as exc:
            assert exc.status == STT_NOT_CONFIGURED
        else:
            raise AssertionError("unset OPENAI_MODEL_STT must fail closed")


def test_stt_uses_openai_model_stt_not_chat_or_cyber() -> None:
    env = {
        "OPENAI_MODEL_STT": "gpt-4o-mini-transcribe",
        "OPENAI_MODEL_CHAT": "gpt-4.1",
        "OPENAI_MODEL": "gpt-4.1-mini",
        "OPENAI_MODEL_CYBER": "gpt-5.6-cyber",
    }
    with patch.dict(os.environ, env, clear=False):
        model, err = resolve_openai_stt_model()
    assert err is None
    assert model == "gpt-4o-mini-transcribe"


def test_stt_rejects_disallowed_model() -> None:
    with patch.dict(os.environ, {"OPENAI_MODEL_STT": "gpt-4.1-mini"}, clear=False):
        model, err = resolve_openai_stt_model()
    assert model == "gpt-4.1-mini"
    assert err == STT_BAD_MODEL


def test_synthetic_batch_one_transcriptions_call_zero_chat_fallback() -> None:
    calls: list[str] = []

    def fake_create(*, model=None, file=None, **kwargs):
        calls.append(model)
        resp = MagicMock()
        resp.text = "sentetik"
        return resp

    env = {
        "OPENAI_MODEL_STT": "whisper-1",
        "OPENAI_MODEL_CHAT": "gpt-4.1",
        "OPENAI_MODEL_CYBER": "gpt-5.6-cyber",
        "LUMOS_STT_RESIDENCY_WRITTEN": "",
    }
    with patch.dict(os.environ, env, clear=False):
        stt = OpenAICloudSTT(audio_source=STT_AUDIO_SYNTHETIC)
        with patch("openai.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_client.audio.transcriptions.create = fake_create
            mock_cls.return_value = mock_client
            out = stt.transcribe(b"\x00\x00" * 160, sample_rate=16000)
    assert out.text == "sentetik"
    assert calls == ["whisper-1"]
    assert "gpt-4.1" not in calls
    assert "gpt-5.6-cyber" not in calls
    mock_cls.assert_called_once()
    assert mock_cls.call_args.kwargs.get("base_url") in (None, )


def test_real_audio_blocked_without_written_gate_zero_api_calls() -> None:
    env = {
        "OPENAI_MODEL_STT": "gpt-4o-transcribe",
        "LUMOS_STT_RESIDENCY_WRITTEN": "",
        "OPENAI_STT_BASE_URL": "https://eu.api.openai.com/v1",
    }
    with patch.dict(os.environ, env, clear=False):
        stt = OpenAICloudSTT(audio_source=STT_AUDIO_REAL)
        with patch("openai.OpenAI") as mock_cls:
            try:
                stt.transcribe(b"\x00\x00" * 160, sample_rate=16000)
            except SttBoundaryError as exc:
                assert exc.status == STT_REAL_BLOCKED
            else:
                raise AssertionError("real audio must not call the API")
    mock_cls.assert_not_called()


def test_real_audio_requires_eu_base_url() -> None:
    env = {
        "OPENAI_MODEL_STT": "gpt-4o-mini-transcribe",
        "LUMOS_STT_RESIDENCY_WRITTEN": "1",
        "OPENAI_STT_BASE_URL": "https://api.openai.com/v1",
    }
    with patch.dict(os.environ, env, clear=False):
        stt = OpenAICloudSTT(audio_source=STT_AUDIO_REAL)
        with patch("openai.OpenAI") as mock_cls:
            try:
                stt.transcribe(b"\x00\x00" * 160, sample_rate=16000)
            except SttBoundaryError as exc:
                assert exc.status == STT_EU_BASE_REQUIRED
            else:
                raise AssertionError("non-EU base must fail closed")
    mock_cls.assert_not_called()


def test_real_audio_eu_base_single_call_after_written_gate() -> None:
    captured: dict[str, str] = {}

    def fake_create(*, model=None, file=None, **kwargs):
        captured["model"] = model
        resp = MagicMock()
        resp.text = "eu"
        return resp

    env = {
        "OPENAI_MODEL_STT": "gpt-4o-mini-transcribe",
        "LUMOS_STT_RESIDENCY_WRITTEN": "1",
        "OPENAI_STT_BASE_URL": "https://eu.api.openai.com/v1",
    }
    with patch.dict(os.environ, env, clear=False):
        stt = OpenAICloudSTT(audio_source=STT_AUDIO_REAL)
        with patch("openai.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_client.audio.transcriptions.create = fake_create
            mock_cls.return_value = mock_client
            out = stt.transcribe(b"\x00\x00" * 160, sample_rate=16000)
    assert out.text == "eu"
    assert captured["model"] == "gpt-4o-mini-transcribe"
    mock_cls.assert_called_once()
    assert mock_cls.call_args.kwargs.get("base_url") == "https://eu.api.openai.com/v1"
