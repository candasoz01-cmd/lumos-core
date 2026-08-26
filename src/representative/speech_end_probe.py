"""Bağımsız yerel söz-sonu damgası — YALNIZ ÖLÇÜM, davranışa dokunmaz.

Neden var
---------
`realtime_stt.speech_end_from_stop_event` söz sonunu ÖLÇMEZ, TÜRETİR:
sunucunun `speech_stopped` olayından sabit `vad_silence_ms` geri sayar. Yani
kayıttaki `speech_end_ts` gözlenmiş bir an değil, MODELLENMİŞ bir andır ve
`stt_ms`/`e2e_first_audio_ms` bu modelin üstüne kuruludur.

Model yanlışsa (sunucu sessizlik penceresinin ÜSTÜNE kendi algılama gecikmesini
ekliyorsa) gerçek söz sonu sandığımızdan erkendir ve **e2e olduğundan iyi
ölçülüyor** demektir. Bu sınıf o varsayımı bağımsız olarak sınamak için aynı ses
akışından enerji tabanlı ikinci bir söz-sonu damgası üretir.

Üç ihtimali ayırır:
  fark ≈ vad_silence_ms   → mevcut model iyi
  fark sistematik > vad   → e2e iyimser ölçülüyor
  fark çok oynak          → endpointing/jitter sorunu

Ölçüm sınırı (dürüstlük notu)
-----------------------------
`now` damgası, karenin BİZE ULAŞTIĞI andır; gerçek mikrofon anı değil. Sunucu
olayı da bize ulaştığı anda damgalanıyor. İki damga da aynı yerel saatten
geldiği için SABİT taşıma gecikmesi büyük ölçüde sadeleşir — ama iki yön farklı
kanallardan geldiği için (ses bizden OpenAI'ye, olay OpenAI'den bize) fark
tamamen kaybolmaz. Bu yüzden sonuç mutlak bir gerçek değil, mevcut modele göre
BAĞIMSIZ bir ikinci görüştür.
"""

from __future__ import annotations

from collections import deque

from representative.audio import calibrate_rms_threshold, frame_rms

# Ortam kalibrasyonu için toplanan kare sayısı. Kısa tutuldu: prova başında
# birkaç saniye sessizlik yeter, uzun tutmak ilk sözleri ölçümsüz bırakırdı.
CALIBRATION_FRAMES = 40
# Sesli kare damgası tamponu. ~30 ms/kare varsayımıyla 4096 kare ≈ 2 dakika
# kesintisiz konuşma; sorgular olaydan hemen sonra geldiği için fazlasıyla yeter.
VOICED_HISTORY = 4096


class SpeechEndProbe:
    """Enerji tabanlı söz-sonu gözlemcisi. Sesi TÜKETMEZ, yalnız izler.

    `observe()` ses hattındaki her kare için çağrılır ve karenin RMS'i eşiğin
    üstündeyse o anı "sesli" diye kaydeder. `last_voiced_before(t)` verilen andan
    ÖNCEKİ son sesli anı döndürür — yani gözlenen söz sonu.
    """

    def __init__(
        self,
        calibration_frames: int = CALIBRATION_FRAMES,
        history: int = VOICED_HISTORY,
    ) -> None:
        if calibration_frames < 1:
            raise ValueError("calibration_frames must be positive")
        self._calibration_frames = calibration_frames
        self._ambient: list[bytes] = []
        self._threshold: float | None = None
        self._voiced: deque[float] = deque(maxlen=history)

    @property
    def calibrated(self) -> bool:
        return self._threshold is not None

    @property
    def threshold(self) -> float | None:
        return self._threshold

    def observe(self, frame: bytes, now: float) -> None:
        """Bir PCM karesini izler. Kalibrasyon bitene kadar yalnız ortam toplar."""
        if self._threshold is None:
            self._ambient.append(frame)
            if len(self._ambient) >= self._calibration_frames:
                self._threshold = calibrate_rms_threshold(self._ambient)
                self._ambient.clear()
            return
        if frame_rms(frame) >= self._threshold:
            self._voiced.append(now)

    def last_voiced_before(self, moment: float) -> float | None:
        """`moment`tan önceki son sesli an. Gözlem yoksa None — 0.0 UYDURULMAZ."""
        for ts in reversed(self._voiced):
            if ts <= moment:
                return ts
        return None

    def offset_ms(self, server_stop_ts: float) -> float | None:
        """Sunucunun durma olayı ile gözlenen söz sonu arasındaki fark (ms).

        Beklenen değer `vad_silence_ms` civarıdır. Belirgin biçimde BÜYÜKSE
        sunucu sessizlik penceresine kendi gecikmesini ekliyor demektir ve
        `speech_end_ts` geri sayması yetersiz kalıyordur.
        """
        local_end = self.last_voiced_before(server_stop_ts)
        if local_end is None:
            return None
        return (server_stop_ts - local_end) * 1000.0
