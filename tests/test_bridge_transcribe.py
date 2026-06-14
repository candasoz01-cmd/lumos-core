"""POST /transcribe köprü iskeleti — doğrulama ve motor-yok yanıtı."""

from __future__ import annotations

from kando_bridge.transcribe import (
    TRANSCRIBE_MAX_BYTES,
    handle_transcribe_request,
)


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
