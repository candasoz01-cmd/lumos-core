"""Yerel söz-sonu damgası testleri — ağ yok, duvar saati yok.

Bu sınıfın işi ÖLÇMEK: `speech_end_ts` sunucunun `speech_stopped` olayından
sabit geri sayımla TÜRETİLİYOR ve o varsayımın doğruluğu hiç sınanmadı.
"""

from __future__ import annotations

import math
import struct

import pytest

from representative.speech_end_probe import SpeechEndProbe


def pcm(amplitude: int, samples: int = 480) -> bytes:
    """Sabit genlikli int16 mono kare (480 örnek ≈ 30 ms @16 kHz)."""
    return struct.pack("<%dh" % samples, *([amplitude] * samples))


def tone(amplitude: int, samples: int = 480) -> bytes:
    """Sinüs kare — RMS ≈ amplitude/√2, sabit genlikten gerçekçi."""
    vals = [int(amplitude * math.sin(2 * math.pi * 200 * i / 16000)) for i in range(samples)]
    return struct.pack("<%dh" % samples, *vals)


QUIET = pcm(60)
LOUD = tone(9000)


def calibrated_probe(frames: int = 8) -> SpeechEndProbe:
    p = SpeechEndProbe(calibration_frames=frames)
    for i in range(frames):
        p.observe(QUIET, float(i) * 0.03)
    assert p.calibrated
    return p


def test_calibration_consumes_ambient_then_arms():
    p = SpeechEndProbe(calibration_frames=5)
    for i in range(4):
        p.observe(QUIET, float(i))
        assert not p.calibrated, "eşik erken kurulmamalı"
    p.observe(QUIET, 4.0)
    assert p.calibrated
    assert p.threshold is not None and p.threshold > 0


def test_quiet_frames_do_not_count_as_speech():
    p = calibrated_probe()
    for i in range(20):
        p.observe(QUIET, 10.0 + i * 0.03)
    assert p.last_voiced_before(20.0) is None, "sessizlik sesli sayıldı"


def test_last_voiced_before_returns_the_observed_speech_end():
    p = calibrated_probe()
    # 10.00–10.30 arası konuşma, sonra sessizlik
    for i in range(10):
        p.observe(LOUD, 10.0 + i * 0.03)
    for i in range(30):
        p.observe(QUIET, 10.3 + i * 0.03)

    end = p.last_voiced_before(11.5)
    assert end == pytest.approx(10.27, abs=0.001)


def test_last_voiced_before_ignores_speech_after_the_moment():
    """Sorgu anından SONRAKİ konuşma cevabı kirletmemeli (sonraki söz)."""
    p = calibrated_probe()
    for i in range(5):
        p.observe(LOUD, 10.0 + i * 0.03)   # birinci söz
    for i in range(5):
        p.observe(LOUD, 20.0 + i * 0.03)   # ikinci söz

    assert p.last_voiced_before(11.0) == pytest.approx(10.12, abs=0.001)


def test_offset_is_none_when_nothing_was_observed():
    """Ölçüm yoksa 0.0 UYDURULMAZ — None döner, kayıtta da ölçümsüz kalır."""
    p = calibrated_probe()
    assert p.offset_ms(100.0) is None


def test_offset_matches_the_vad_window_when_the_model_is_right():
    """Model doğruysa: sunucu olayı, gözlenen söz sonundan ~vad kadar sonra."""
    p = calibrated_probe()
    for i in range(10):
        p.observe(LOUD, 30.0 + i * 0.03)
    speech_end_observed = 30.27
    server_stop = speech_end_observed + 1.100      # tam pencere kadar sonra

    assert p.offset_ms(server_stop) == pytest.approx(1100.0, abs=1.0)


def test_offset_exposes_an_optimistic_e2e_when_the_server_lags():
    """İhtimal 2: sunucu pencereye kendi gecikmesini ekliyorsa fark > vad çıkar.

    Bu durumda `speech_end_ts` geri sayması YETERSİZDİR: gerçek söz sonu daha
    erkendir, yani kayıttaki e2e olduğundan İYİ görünür.
    """
    p = calibrated_probe()
    for i in range(10):
        p.observe(LOUD, 40.0 + i * 0.03)
    server_stop = 40.27 + 1.100 + 0.400            # 400 ms ek sunucu gecikmesi

    offset = p.offset_ms(server_stop)
    assert offset == pytest.approx(1500.0, abs=1.0)
    assert offset > 1100.0, "model iyimserliği yakalanmalı"


def test_probe_never_consumes_or_alters_frames():
    """Ölçüm sınıfı ses hattına dokunmaz: kare içeriği değişmeden kalır."""
    p = calibrated_probe()
    frame = bytes(LOUD)
    before = bytes(frame)
    p.observe(frame, 50.0)
    assert frame == before
