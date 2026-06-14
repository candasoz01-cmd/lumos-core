"""Local faster-whisper integration — skipped unless KANDO_STT_INTEGRATION=1."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from kando_bridge.transcribe import handle_transcribe_request
from kando_bridge.transcribe_engine import set_engine_instance

_FIXTURE_WAV = Path(__file__).resolve().parent / "fixtures" / "audio" / "tiny_silence.wav"


def _multipart_audio(
    audio: bytes,
    *,
    boundary: str = "----lumos-transcribe-integration",
    field: str = "audio",
    filename: str = "tiny_silence.wav",
) -> tuple[str, bytes]:
    ct = f"multipart/form-data; boundary={boundary}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode("utf-8") + audio + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return ct, body


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("KANDO_STT_INTEGRATION", "").strip() != "1",
    reason="Set KANDO_STT_INTEGRATION=1 to run local STT integration test",
)
def test_transcribe_faster_whisper_local_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("faster_whisper")

    set_engine_instance(None)
    monkeypatch.setenv("KANDO_STT_ENABLED", "1")
    monkeypatch.setenv("KANDO_STT_MODEL", os.environ.get("KANDO_STT_MODEL", "tiny"))
    monkeypatch.setenv("KANDO_STT_DEVICE", os.environ.get("KANDO_STT_DEVICE", "cpu"))
    monkeypatch.setenv(
        "KANDO_STT_COMPUTE_TYPE",
        os.environ.get("KANDO_STT_COMPUTE_TYPE", "int8"),
    )

    audio_bytes = _FIXTURE_WAV.read_bytes()
    ct, body = _multipart_audio(audio_bytes)

    status, payload = handle_transcribe_request(ct, body, content_length=len(body))

    assert status == 200
    assert payload["ok"] is True
    assert payload["engine"] == "faster-whisper"
    assert payload["model"]
    assert "text" in payload
    assert "transcript" in payload
    assert payload["text"] == payload["transcript"]
    assert isinstance(payload.get("language"), str)
    assert isinstance(payload.get("duration_sec"), (int, float))
    assert payload["duration_sec"] >= 0
