"""Slice tests for Aşama B primitives: endpointing + half-duplex echo guard (T7 logic)."""

from __future__ import annotations

from array import array

from representative.audio import (
    HalfDuplexGate,
    SegmenterConfig,
    UtteranceSegmenter,
    frame_rms,
)

CFG = SegmenterConfig(
    sample_rate=16000, frame_ms=30, rms_threshold=500.0, end_silence_ms=90, min_utterance_ms=60
)
FRAME_SAMPLES = int(16000 * 0.03)


def tone_frame(amplitude: int) -> bytes:
    return array("h", [amplitude] * FRAME_SAMPLES).tobytes()


SPEECH = tone_frame(3000)
SILENCE = tone_frame(0)


def feed_all(segmenter: UtteranceSegmenter, frames: list[bytes]) -> list[bytes]:
    return [out for frame in frames if (out := segmenter.feed(frame)) is not None]


def test_frame_rms_scales_with_amplitude():
    assert frame_rms(SILENCE) == 0.0
    assert frame_rms(SPEECH) > frame_rms(tone_frame(100))


def test_speech_then_silence_emits_one_utterance():
    segmenter = UtteranceSegmenter(CFG)
    utterances = feed_all(segmenter, [SPEECH] * 5 + [SILENCE] * 4)
    assert len(utterances) == 1
    assert len(utterances[0]) >= 5 * len(SPEECH)  # konuşmanın tamamı içeride


def test_short_burst_is_discarded_as_noise():
    cfg = SegmenterConfig(
        sample_rate=16000,
        frame_ms=30,
        rms_threshold=500.0,
        end_silence_ms=90,
        min_utterance_ms=200,
    )
    segmenter = UtteranceSegmenter(cfg)
    assert feed_all(segmenter, [SPEECH, SILENCE, SILENCE, SILENCE, SILENCE]) == []


def test_intra_speech_pause_does_not_split_utterance():
    segmenter = UtteranceSegmenter(CFG)
    utterances = feed_all(segmenter, [SPEECH] * 3 + [SILENCE] * 2 + [SPEECH] * 3 + [SILENCE] * 4)
    assert len(utterances) == 1  # 60 ms'lik ara, 90 ms'lik eşik altında


def test_t7_frames_while_tts_speaking_are_dropped():
    gate = HalfDuplexGate()
    segmenter = UtteranceSegmenter(CFG, gate=gate)
    with gate:  # TTS konuşuyor: hoparlör çıkışı mikrofona dönse bile...
        assert feed_all(segmenter, [SPEECH] * 10 + [SILENCE] * 4) == []
    # ...kapı açılınca normal akış kaldığı yerden temiz başlar
    assert len(feed_all(segmenter, [SPEECH] * 5 + [SILENCE] * 4)) == 1


def test_t7_gate_closing_mid_utterance_discards_partial_buffer():
    gate = HalfDuplexGate()
    segmenter = UtteranceSegmenter(CFG, gate=gate)
    assert feed_all(segmenter, [SPEECH] * 3) == []  # söz birikmeye başladı
    with gate:
        assert segmenter.feed(SPEECH) is None  # TTS başladı: tampon atılır
    assert feed_all(segmenter, [SILENCE] * 6) == []  # yarım söz sızmaz


def test_gate_is_reentrant():
    gate = HalfDuplexGate()
    with gate:
        with gate:
            assert gate.listening is False
        assert gate.listening is False
    assert gate.listening is True


def test_calibration_raises_threshold_above_ambient():
    from representative.audio import calibrate_rms_threshold

    quiet = [tone_frame(50)] * 10
    noisy = [tone_frame(1000)] * 10
    assert calibrate_rms_threshold(quiet, floor=500.0) == 500.0  # taban korunur
    assert calibrate_rms_threshold(noisy, floor=500.0) == 4000.0  # ortam × 4
    assert calibrate_rms_threshold([], floor=500.0) == 500.0


def test_repeat_suppressor_drops_hallucination_spam():
    from representative.audio import RepeatSuppressor

    s = RepeatSuppressor(window_s=10.0)
    assert s.should_drop("Teşekkürler.", now=0.0) is False  # ilk kez: geçer
    assert s.should_drop("Teşekkürler.", now=3.0) is True  # pencere içi tekrar: düşer
    assert s.should_drop("Farklı cümle", now=4.0) is False
    assert s.should_drop("Teşekkürler.", now=5.0) is False  # araya başka metin girdi
    s2 = RepeatSuppressor(window_s=10.0)
    s2.should_drop("Teşekkürler.", now=0.0)
    assert s2.should_drop("Teşekkürler.", now=15.0) is False  # pencere dışı: geçer
