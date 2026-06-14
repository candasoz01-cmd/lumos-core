"""POST /transcribe — ses→metin köprü; doğrulama + isteğe bağlı STT motoru."""
from __future__ import annotations

import re
from email import policy
from email.parser import BytesParser

from kando_bridge.transcribe_engine import (
    EngineUnavailable,
    is_engine_available,
    transcribe_audio_bytes,
)

TRANSCRIBE_MAX_BYTES = 10 * 1024 * 1024
TRANSCRIBE_AUDIO_FIELD = "audio"

_ENGINE_UNAVAILABLE = {
    "ok": False,
    "error": "transcribe_engine_unavailable",
    "message": "Ses metne çeviri motoru henüz bağlı değil.",
}


def _parse_boundary(content_type: str | None) -> str | None:
    if not content_type:
        return None
    for segment in content_type.split(";")[1:]:
        seg = segment.strip()
        if seg.lower().startswith("boundary="):
            value = seg.split("=", 1)[1].strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            return value or None
    return None


def _extract_multipart_field(
    content_type: str | None,
    raw: bytes,
    field_name: str,
) -> tuple[bytes | None, str | None]:
    """İlk eşleşen form alanının gövdesini ve dosya adı ipucunu döndürür."""
    boundary = _parse_boundary(content_type)
    if not boundary:
        return None, None
    header_block = f"Content-Type: {content_type}\r\n\r\n".encode("utf-8", errors="replace")
    try:
        msg = BytesParser(policy=policy.default).parsebytes(header_block + raw)
    except (ValueError, TypeError):
        return None, None
    for part in msg.iter_parts():
        disp = part.get("Content-Disposition") or ""
        m = re.search(r'name="([^"]+)"', disp, re.I)
        if not m:
            continue
        if m.group(1) != field_name:
            continue
        filename_hint: str | None = None
        m_fn = re.search(r'filename="([^"]+)"', disp, re.I)
        if m_fn:
            filename_hint = m_fn.group(1)
        payload = part.get_payload(decode=True)
        if isinstance(payload, (bytes, bytearray)):
            return bytes(payload), filename_hint
    return None, None


def handle_transcribe_request(
    content_type: str | None,
    raw: bytes,
    *,
    content_length: int | None = None,
) -> tuple[int, dict]:
    """
    Ses yükleme isteğini doğrular; gövde kalıcı saklanmaz.
    STT motoru yoksa 503; motor varsa transkript sonucu döner.
    """
    declared_len = content_length
    if declared_len is None:
        declared_len = len(raw)

    if declared_len > TRANSCRIBE_MAX_BYTES:
        return (
            413,
            {
                "ok": False,
                "error": "transcribe_payload_too_large",
                "message": "Ses dosyası en fazla 10 MB olabilir.",
            },
        )

    ct_main = (content_type or "").split(";")[0].strip().lower()
    if ct_main != "multipart/form-data":
        return (
            400,
            {
                "ok": False,
                "error": "transcribe_invalid_content_type",
                "message": "multipart/form-data ile ses dosyası gerekli.",
            },
        )

    if not raw:
        return (
            400,
            {
                "ok": False,
                "error": "transcribe_missing_audio",
                "message": "Ses dosyası gerekli.",
            },
        )

    audio_bytes, filename_hint = _extract_multipart_field(
        content_type,
        raw,
        TRANSCRIBE_AUDIO_FIELD,
    )
    if not audio_bytes:
        return (
            400,
            {
                "ok": False,
                "error": "transcribe_missing_audio",
                "message": "Ses dosyası gerekli.",
            },
        )

    if len(audio_bytes) > TRANSCRIBE_MAX_BYTES:
        return (
            413,
            {
                "ok": False,
                "error": "transcribe_payload_too_large",
                "message": "Ses dosyası en fazla 10 MB olabilir.",
            },
        )

    if not is_engine_available():
        return 503, dict(_ENGINE_UNAVAILABLE)

    try:
        result = transcribe_audio_bytes(
            audio_bytes,
            language=None,
            filename=filename_hint,
        )
    except EngineUnavailable:
        return 503, dict(_ENGINE_UNAVAILABLE)

    # Gövde işlendi; kalıcı depolama yok — audio_bytes scope dışına çıkınca atılır.
    return 200, result
