"""POST /transcribe köprü iskeleti — doğrulama ve motor-yok yanıtı."""

from __future__ import annotations

from unittest.mock import patch

from kando_bridge.transcribe import (
    TRANSCRIBE_MAX_BYTES,
    handle_transcribe_request,
)
from kando_bridge.transcribe_engine import set_engine_instance


def _multipart_audio(
    audio: bytes,
    *,
    boundary: str = "----lumos-transcribe-test",
    field: str = "audio",
    filename: str = "clip.webm",
) -> tuple[str, bytes]:
    ct = f"multipart/form-data; boundary={boundary}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        f"Content-Type: audio/webm\r\n\r\n"
    ).encode("utf-8") + audio + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return ct, body


def test_transcribe_engine_unavailable_with_valid_audio() -> None:
    ct, body = _multipart_audio(b"\x00\x01\x02")
    status, payload = handle_transcribe_request(ct, body, content_length=len(body))
    assert status == 503
    assert payload == {
        "ok": False,
        "error": "transcribe_engine_unavailable",
        "message": "Ses metne çeviri motoru henüz bağlı değil.",
    }


class _MockTranscribeEngine:
    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language: str | None = None,
        filename: str | None = None,
    ) -> dict:
        assert audio_bytes == b"\x00\x01\x02"
        assert filename == "clip.webm"
        return {
            "ok": True,
            "text": "merhaba dünya",
            "language": language or "tr",
            "filename": filename,
        }


def test_transcribe_success_with_mock_engine() -> None:
    mock_engine = _MockTranscribeEngine()
    set_engine_instance(mock_engine)
    try:
        ct, body = _multipart_audio(b"\x00\x01\x02")
        status, payload = handle_transcribe_request(ct, body, content_length=len(body))
        assert status == 200
        assert payload == {
            "ok": True,
            "text": "merhaba dünya",
            "language": "tr",
            "filename": "clip.webm",
        }
    finally:
        set_engine_instance(None)


def test_transcribe_success_with_patched_engine() -> None:
    mock_result = {
        "ok": True,
        "text": "patched transcript",
        "language": "en",
    }
    with (
        patch("kando_bridge.transcribe.is_engine_available", return_value=True),
        patch(
            "kando_bridge.transcribe.transcribe_audio_bytes",
            return_value=mock_result,
        ) as mock_transcribe,
    ):
        ct, body = _multipart_audio(b"audio-data", filename="note.ogg")
        status, payload = handle_transcribe_request(ct, body, content_length=len(body))
        assert status == 200
        assert payload == mock_result
        mock_transcribe.assert_called_once()
        call_kwargs = mock_transcribe.call_args
        assert call_kwargs.args[0] == b"audio-data"
        assert call_kwargs.kwargs["filename"] == "note.ogg"
        assert call_kwargs.kwargs["language"] is None


def test_transcribe_missing_audio_empty_body() -> None:
    ct = "multipart/form-data; boundary=----x"
    status, payload = handle_transcribe_request(ct, b"", content_length=0)
    assert status == 400
    assert payload["ok"] is False
    assert payload["error"] == "transcribe_missing_audio"


def test_transcribe_missing_audio_field() -> None:
    boundary = "----no-audio-field"
    ct = f"multipart/form-data; boundary={boundary}"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="note"\r\n\r\n'
        "hello\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    status, payload = handle_transcribe_request(ct, body, content_length=len(body))
    assert status == 400
    assert payload["error"] == "transcribe_missing_audio"


def test_transcribe_invalid_content_type() -> None:
    status, payload = handle_transcribe_request(
        "application/json",
        b'{"audio":"x"}',
        content_length=13,
    )
    assert status == 400
    assert payload["error"] == "transcribe_invalid_content_type"


def test_transcribe_payload_too_large_by_content_length() -> None:
    ct, body = _multipart_audio(b"ok")
    status, payload = handle_transcribe_request(
        ct,
        body,
        content_length=TRANSCRIBE_MAX_BYTES + 1,
    )
    assert status == 413
    assert payload["error"] == "transcribe_payload_too_large"


def test_transcribe_payload_too_large_audio_part() -> None:
    oversized = b"x" * (TRANSCRIBE_MAX_BYTES + 1)
    ct, body = _multipart_audio(oversized)
    status, payload = handle_transcribe_request(ct, body, content_length=len(body))
    assert status == 413
    assert payload["error"] == "transcribe_payload_too_large"
