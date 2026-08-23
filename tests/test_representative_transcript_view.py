"""Canlı transkript gösterim testleri — özgün söz ile çeviri ayrı okunmalı."""

from representative.pipeline import UtteranceRecord
from representative.transcript_view import (
    attribution_note,
    format_heard,
    format_telemetry,
    format_translation,
)


def _record(**over: object) -> UtteranceRecord:
    base: dict[str, object] = {
        "source_text": "Merhaba",
        "source_lang": "tr",
        "translated_text": "Hello",
        "target_lang": "en",
        "confidence": 0.95,
        "flagged": False,
        "flag_reason": "ok",
        "latency_ms": 2130.0,
        "recorded_at": 0.0,
    }
    base.update(over)
    return UtteranceRecord(**base)  # type: ignore[arg-type]


def test_heard_line_states_language_only() -> None:
    assert format_heard("tr", "Merhaba") == "Duyulan (TR): Merhaba"
    assert format_heard("en", "How are you?") == "Duyulan (EN): How are you?"


def test_no_speaker_attribution_is_claimed_anywhere() -> None:
    """Kurucu kararı 2026-08-23: atıf dilden türetilemez, etiket kimse demez."""
    surfaces = [
        format_heard("tr", "Merhaba"),
        format_heard("en", "Hello"),
        format_translation(_record()),
        attribution_note(),
    ]
    for text in surfaces:
        assert "Sen" not in text.replace("Duyulan", "")
        assert "Karşı taraf" not in text


def test_translation_is_a_separate_attributed_line() -> None:
    line = format_translation(_record())
    assert line.strip() == "Lumos → EN: Hello"
    # Özgün söz çeviri satırına karışmaz.
    assert "Merhaba" not in line


def test_low_confidence_is_marked_but_still_shown() -> None:
    line = format_translation(_record(flagged=True, flag_reason="below_threshold"))
    assert "Hello" in line
    assert "düşük güven" in line


def test_undelivered_translation_says_it_was_not_spoken() -> None:
    line = format_translation(_record(delivered=False, flag_reason="meta_output"))
    assert "seslendirilmedi" in line


def test_telemetry_lives_on_its_own_line() -> None:
    record = _record(stt_ms=900.0, translate_ms=610.0, tts_to_first_audio_ms=620.0)
    telemetry = format_telemetry(record, "detected")
    assert "e2e 2130 ms" in telemetry
    assert "yön: detected" in telemetry
    # Çeviri metni ölçüm satırında tekrar edilmez.
    assert "Hello" not in telemetry


def test_attribution_note_states_the_honest_limit() -> None:
    note = attribution_note()
    assert "konuşmacı kimliği yok" in note
    assert "kimin konuştuğu bu sürümde bilinmiyor" in note
