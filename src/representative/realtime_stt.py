"""Streaming STT over the OpenAI Realtime API (kalem 3, 2026-08-17).

Yapısal gecikme kaldıracı: transkripsiyon konuşma SIRASINDA akar; sunucu VAD
sözü bitirdiğinde transkript ~1.3 sn içinde tamamlanır. Toplu (batch) bulut
STT'nin istemci-tarafı 1400 ms bekleme + ~1.1 sn işleme kuyruğuna karşı
sentetik ölçüm: ses sonu → transkript 1.88 sn (0.6 sn VAD dahil).

Half-duplex kuralı korunur: kapı kapalıyken (TTS konuşurken) kareler websocket'e
HİÇ gönderilmez — sunucu sessizlik görür, echo transkripti oluşamaz.

CI notu: websocket ve ağ gerektirir; birim testler yalnız saf mantığı
(zaman damgası hesabı) kapsar, canlı doğrulama prova koşusunda.
"""

from __future__ import annotations

import base64
import queue
import threading
import time
from dataclasses import dataclass

SAMPLE_RATE = 24000  # Realtime API pcm16 varsayılanı; rig bu backend'de 24k yakalar


@dataclass(frozen=True)
class RealtimeUtterance:
    text: str
    speech_end_ts: float  # monotonic; VAD sessizlik payı geri alınmış hali


def speech_end_from_stop_event(event_monotonic: float, vad_silence_ms: int) -> float:
    """speech_stopped olayı, gerçek söz sonundan vad_silence_ms sonra gelir."""
    return event_monotonic - vad_silence_ms / 1000.0


class RealtimeSTTStream:
    """Feeds mic PCM to a Realtime transcription session; yields utterances.

    Kullanım: start() → feed(frame) [ses eş yürütmesinden] → utterances.get().
    stop() websocket'i kapatır. Kapı kapalıyken feed çağrılmamalı (rig zaten
    yakalama anında düşürür).
    """

    def __init__(
        self,
        language: str | None,
        prompt: str | None = None,
        model: str = "gpt-4o-mini-transcribe",
        vad_silence_ms: int = 600,
    ) -> None:
        self._language = language
        self._prompt = prompt
        self._model = model
        self._vad_silence_ms = vad_silence_ms
        self._frames: queue.Queue[bytes | None] = queue.Queue()
        self.utterances: queue.Queue[RealtimeUtterance] = queue.Queue()
        self._threads: list[threading.Thread] = []
        self._conn = None
        self._cm = None
        self._speech_stopped_at: float | None = None

    def transcription_config(self) -> dict:
        """Transkripsiyon bloğu; `language=None` → anahtar HİÇ gönderilmez.

        Çift yönlü toplantıda dil sabitlenemez (canlı insan testi 4): dil
        verilirse sağlayıcı karşı tarafın İngilizcesini de Türkçe sanıp
        uydurulmuş metin üretiyordu. None → sağlayıcının kendi tespiti.
        """
        config: dict = {"model": self._model, "prompt": self._prompt or ""}
        if self._language is not None:
            config["language"] = self._language
        return config

    def start(self) -> None:
        from openai import OpenAI  # core dep; ağ anahtarı env'den

        self._cm = OpenAI().realtime.connect(extra_query={"intent": "transcription"})
        self._conn = self._cm.__enter__()
        self._conn.send(
            {
                "type": "session.update",
                "session": {
                    "type": "transcription",
                    "audio": {
                        "input": {
                            "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                            "transcription": self.transcription_config(),
                            "turn_detection": {
                                "type": "server_vad",
                                "silence_duration_ms": self._vad_silence_ms,
                            },
                        }
                    },
                },
            }
        )
        sender = threading.Thread(target=self._send_loop, daemon=True)
        reader = threading.Thread(target=self._read_loop, daemon=True)
        self._threads = [sender, reader]
        sender.start()
        reader.start()

    def feed(self, frame: bytes) -> None:
        self._frames.put(frame)

    def stop(self) -> None:
        self._frames.put(None)
        if self._cm is not None:
            try:
                self._cm.__exit__(None, None, None)
            except Exception:
                pass  # kapanış gürültüsü prova akışını bozmasın

    def _send_loop(self) -> None:
        while True:
            frame = self._frames.get()
            if frame is None:
                return
            try:
                self._conn.send(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(frame).decode(),
                    }
                )
            except Exception:
                return  # bağlantı kapandı; reader tarafı da sonlanır

    def _read_loop(self) -> None:
        try:
            for event in self._conn:
                if event.type == "input_audio_buffer.speech_stopped":
                    self._speech_stopped_at = time.monotonic()
                elif event.type == "conversation.item.input_audio_transcription.completed":
                    stopped = self._speech_stopped_at or time.monotonic()
                    self.utterances.put(
                        RealtimeUtterance(
                            text=(event.transcript or "").strip(),
                            speech_end_ts=speech_end_from_stop_event(
                                stopped, self._vad_silence_ms
                            ),
                        )
                    )
        except Exception:
            return  # stop() sonrası normal kapanış
