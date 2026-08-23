"""MeetingIngress kural testleri — kurucu şartları (2026-08-12) kod düzeyinde."""

from __future__ import annotations

import json

import pytest

from representative.meeting_ingress import (
    REAL_MEETING_RETENTION,
    REHEARSAL_RETENTION,
    DISCLOSURE_LINE_EN,
    DISCLOSURE_LINE_TR,
    RecallMeetingIngress,
    RetentionPolicy,
    build_recall_bot_payload,
)

MEET_URL = "https://meet.google.com/abc-defg-hij"


def test_retention_is_mandatory_and_validated():
    with pytest.raises(ValueError):
        RetentionPolicy(kind="forever")  # süresiz saklama diye bir seçenek YOK
    with pytest.raises(ValueError):
        RetentionPolicy(kind="timed")  # saat vermeden timed olmaz
    with pytest.raises(ValueError):
        build_recall_bot_payload(MEET_URL, retention=None, internal_ref="x")  # type: ignore[arg-type]


def test_rehearsal_and_real_meeting_policies():
    assert REHEARSAL_RETENTION.to_recall() == {"type": "timed", "hours": 24}
    assert REAL_MEETING_RETENTION.to_recall() is None  # zero: hiçbir medya saklanmaz


def test_payload_rules_pin_founder_constraints():
    payload = build_recall_bot_payload(MEET_URL, REHEARSAL_RETENTION, internal_ref="ref-123")
    assert payload["bot_name"] == "Lumos · AI Representative"
    assert payload["recording_config"]["retention"] == {"type": "timed", "hours": 24}
    assert payload["metadata"] == {"lumos_ref": "ref-123"}  # yalnız opak referans
    assert "transcription" not in json.dumps(payload).lower()  # Recall STT asla
    # Prova 2 canlı bulgusu: boş b64 Recall'da 400 — klip yoksa alan HİÇ gönderilmez
    assert "automatic_audio_output" not in payload
    with_clip = build_recall_bot_payload(
        MEET_URL, REHEARSAL_RETENTION, internal_ref="r", disclosure_mp3_b64="QUJD"
    )
    assert with_clip["automatic_audio_output"]["in_call_recording"]["data"]["b64_data"] == "QUJD"


def test_meet_avatar_is_idle_on_join_in_both_call_states():
    payload = build_recall_bot_payload(
        MEET_URL,
        REHEARSAL_RETENTION,
        internal_ref="avatar-test",
        avatar_idle_jpeg_b64="/9j/idle/9k=",
    )
    expected = {"kind": "jpeg", "b64_data": "/9j/idle/9k="}
    assert payload["automatic_video_output"] == {
        "in_call_not_recording": expected,
        "in_call_recording": expected,
    }


def test_show_avatar_uses_recall_output_video_endpoint(monkeypatch):
    ingress = RecallMeetingIngress(
        REHEARSAL_RETENTION, "https://us-west-2.recall.ai", api_key="test"
    )
    calls = []
    monkeypatch.setattr(
        ingress,
        "_request",
        lambda method, path, body=None: calls.append((method, path, body)),
    )

    ingress.show_avatar("bot-123", "JPEG64")

    assert calls == [
        (
            "POST",
            "/api/v1/bot/bot-123/output_video/",
            {"kind": "jpeg", "b64_data": "JPEG64"},
        )
    ]


def test_only_google_meet_urls_in_phase0():
    with pytest.raises(ValueError):
        build_recall_bot_payload("https://zoom.us/j/123", REHEARSAL_RETENTION, "x")


def test_opaque_ref_rejects_meaningful_content():
    with pytest.raises(ValueError):
        build_recall_bot_payload(MEET_URL, REHEARSAL_RETENTION, "candas toplantısı")


def test_missing_api_key_fails_closed(monkeypatch):
    monkeypatch.delenv("RECALL_API_KEY", raising=False)
    with pytest.raises(ValueError):
        RecallMeetingIngress(REHEARSAL_RETENTION, "https://us-west-2.recall.ai")


def test_disclosure_guard_matches_english_only_speech():
    """Susturma penceresi EN-only beyana göre hesaplanmalı (A hattı).

    İki dilli eski varsayım (~27 sn) kalırsa bot, beyan bittikten sonra da
    karşı tarafı uzun süre duymaz. #779 sonrası bu değer küçülmeli.
    """
    from representative.bot_rig import DISCLOSURE_GUARD_S

    assert DISCLOSURE_GUARD_S < 20.0
    two_language_estimate = (len(DISCLOSURE_LINE_TR) + len(DISCLOSURE_LINE_EN)) / 14.0
    assert DISCLOSURE_GUARD_S < two_language_estimate


def test_disclosure_lines_state_ai_and_transcript():
    for line in (DISCLOSURE_LINE_TR, DISCLOSURE_LINE_EN):
        low = line.lower()
        assert "lumos" in low
        assert "yapay zekâ" in low or "ai" in low
        assert "tutanak" in low or "transcript" in low
        assert "kurucu" in low or "founder" in low
        assert "temsilci" in low or "representative" in low


def test_bot_name_is_english_and_does_not_claim_founder_role():
    """V1 kararı: toplantı arayüzünde herkese görünen ad İngilizce ve sade."""
    payload = build_recall_bot_payload(MEET_URL, REHEARSAL_RETENTION, internal_ref="ad-testi")
    assert payload["bot_name"] == "Lumos · AI Representative"


def test_spoken_disclosure_is_english_only_and_short():
    """V1 kurucu kararı (2026-08-20): tek ses akışına yalnız İngilizce beyan."""
    assert len(DISCLOSURE_LINE_EN) < 200
    low = DISCLOSURE_LINE_EN.lower()
    for required in ("lumos", "ai", "representative", "founder", "transcript"):
        assert required in low, f"beyan '{required}' unsurunu kaybetti"


def test_turkish_disclosure_kept_for_written_channel():
    """TR metni silinmez: yazılı kanal ve ileride çok dilli aşama için durur."""
    low = DISCLOSURE_LINE_TR.lower()
    for required in ("lumos", "yapay zekâ", "temsilci", "kurucu", "tutanak"):
        assert required in low, f"TR beyan '{required}' unsurunu kaybetti"


def test_disclosure_states_the_video_is_generated_not_a_camera() -> None:
    """ADR-023 madde 3: görsel katman ancak karşı tarafa ifşa ile açılır.

    Avatar bir kamera görüntüsü değil, üretilmiş iki durumlu gösterge.
    Karşı taraf bunu duymadan görsel katman açılamaz."""
    low = DISCLOSURE_LINE_EN.lower()
    assert "camera" in low
    assert "generated" in low

    low_tr = DISCLOSURE_LINE_TR.lower()
    assert "kamera" in low_tr
    assert "gösterge" in low_tr or "üretilmiş" in low_tr


def test_spoken_disclosure_stays_short_enough_to_be_heard() -> None:
    """Beyan uzadıkça susturma penceresi de uzuyor; bot o sürede karşı tarafı
    duymuyor. Görüntü ibaresi eklendi, sınır hâlâ korunmalı."""
    from representative.bot_rig import DISCLOSURE_GUARD_S

    assert len(DISCLOSURE_LINE_EN) < 200
    assert DISCLOSURE_GUARD_S < 20.0
