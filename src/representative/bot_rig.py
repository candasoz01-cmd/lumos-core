"""In-meeting interpreter rig: Recall inbound audio → core → bot voice out.

Prova 1 teşhisi (2026-08-17, kurucu): join/disclosure PASS; "Meet sesi →
STT → çeviri → TTS → bota geri ses" zinciri BAĞLI DEĞİLDİ. Bu modül o kulağı
bağlar:

    Recall realtime_endpoints (websocket push, 16k PCM)
      → ngrok tüneli → yerel ws sunucu (bu süreç)
      → 16k→24k → RealtimeSTTStream → filtreler → InterpreterPipeline
      → RecallSpeaker (OpenAI TTS mp3 → output_audio)

Half-duplex toplantı içinde de geçerli: bot konuşurken (tahmini klip süresi
boyunca kapı kapalı) gelen kareler DÜŞÜRÜLÜR — bot kendi sesini çeviremez.
Fail-closed: wss olmayan endpoint reddedilir; bilinmeyen ws mesaj şekilleri
sayılır ve düşürülür; retention kuralları meeting_ingress'ten aynen gelir.
HTTP/ws şekilleri ilk canlı koşuda doğrulanır (dürüstlük notu).

Usage:
    python -m representative.bot_rig --meeting-url https://meet.google.com/xxx
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.request
from collections import deque
from typing import Any

from representative.audio import HalfDuplexGate, RepeatSuppressor
from representative.meeting_ingress import (
    REHEARSAL_RETENTION,
    RecallMeetingIngress,
    build_recall_bot_payload,
)
from representative.pipeline import (
    BilingualTranscript,
    ConfidenceGate,
    InterpreterPipeline,
    Utterance,
    summarize_latencies_ms,
)
from representative.stt import LUMOS_TERMS_PROMPT

RECALL_INBOUND_RATE = 16000


def extract_audio_b64(message: dict[str, Any]) -> str | None:
    """Recall realtime ses olayından b64 PCM çıkarır; tanımadığını DÜŞÜRÜR."""
    if message.get("event") != "audio_mixed_raw.data":
        return None
    data = message.get("data") or {}
    inner = data.get("data") if isinstance(data.get("data"), dict) else data
    buffer = inner.get("buffer") if isinstance(inner, dict) else None
    return buffer if isinstance(buffer, str) and buffer else None


def resample_16k_to_24k(pcm: bytes) -> bytes:
    import numpy as np  # representative opsiyonel grubuyla gelir

    samples = np.frombuffer(pcm, dtype=np.int16)
    if len(samples) == 0:
        return b""
    positions = np.linspace(0, len(samples) - 1, int(len(samples) * 1.5))
    return np.interp(positions, np.arange(len(samples)), samples).astype(np.int16).tobytes()


def estimate_speech_seconds(text: str) -> float:
    """Kaba klip süresi tahmini — half-duplex kapının tutulma süresi."""
    return 0.075 * len(text) + 1.0


def build_realtime_endpoint(wss_url: str) -> dict[str, Any]:
    if not wss_url.startswith("wss://"):
        raise ValueError("realtime endpoint wss:// olmalı (fail-closed)")
    return {"type": "websocket", "url": wss_url, "events": ["audio_mixed_raw.data"]}


class RecallSpeaker:
    """TextToSpeech gerçeklemesi: nötr erkek TTS → botun sesinden toplantıya."""

    def __init__(self, ingress: RecallMeetingIngress, bot_id: str, gate: HalfDuplexGate) -> None:
        from openai import OpenAI

        self._client = OpenAI()
        self._ingress = ingress
        self._bot_id = bot_id
        self._gate = gate

    def speak(self, text: str, lang: str) -> None:
        resp = self._client.audio.speech.create(
            model="gpt-4o-mini-tts", voice="onyx", input=text, response_format="mp3"
        )
        with self._gate:  # bot konuşurken gelen kareler düşer (toplantı içi yankı)
            self._ingress.speak(self._bot_id, base64.b64encode(resp.content).decode())
            time.sleep(estimate_speech_seconds(text))


def start_ngrok(port: int) -> tuple[subprocess.Popen, str]:
    proc = subprocess.Popen(
        ["ngrok", "http", str(port), "--log", "stdout"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(100):
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as r:
                tunnels = json.load(r).get("tunnels", [])
            if tunnels:
                url = tunnels[0]["public_url"].replace("https://", "wss://")
                return proc, url
        except Exception:
            pass
        time.sleep(0.2)
    proc.terminate()
    raise RuntimeError("ngrok tüneli açılamadı (authtoken/ağ?)")


def main(argv: list[str] | None = None) -> int:
    from websockets.sync.server import serve  # openai[realtime] ile kurulu

    from representative.local_rig import OpenAITranslator
    from representative.realtime_stt import RealtimeSTTStream
    from representative.terms import TermCorrector, is_prompt_echo

    parser = argparse.ArgumentParser(description="Faz 0 toplantı-içi tercüman rig'i")
    parser.add_argument("--meeting-url", required=True)
    parser.add_argument("--source-lang", default="tr", choices=("tr", "en"))
    parser.add_argument("--target-lang", default="en", choices=("tr", "en"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--jsonl-out", default="prova_bot.jsonl")
    args = parser.parse_args(argv)
    if args.source_lang == args.target_lang:
        parser.error("source and target languages must differ")

    gate = HalfDuplexGate()
    inbound: queue.Queue[bytes] = queue.Queue()
    dropped_unknown = 0

    def on_ws(conn) -> None:
        nonlocal dropped_unknown
        print("Recall websocket bağlandı.")
        for raw in conn:
            try:
                b64 = extract_audio_b64(json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                dropped_unknown += 1
                continue
            if b64 is None:
                dropped_unknown += 1
                continue
            if gate.listening:
                inbound.put(base64.b64decode(b64))

    server = serve(on_ws, "127.0.0.1", args.port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    ngrok_proc, wss_url = start_ngrok(args.port)
    print(f"tünel: {wss_url}")

    ingress = RecallMeetingIngress(
        REHEARSAL_RETENTION, os.environ["RECALL_REGION_URL"]
    )
    payload = build_recall_bot_payload(
        args.meeting_url, REHEARSAL_RETENTION, internal_ref="faz0-bot-prova"
    )
    payload["recording_config"]["realtime_endpoints"] = [build_realtime_endpoint(wss_url)]
    from openai import OpenAI

    from representative.meeting_ingress import DISCLOSURE_LINE_EN, DISCLOSURE_LINE_TR

    disclosure = OpenAI().audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="onyx",
        input=DISCLOSURE_LINE_TR + " ... " + DISCLOSURE_LINE_EN,
        response_format="mp3",
    )
    payload["automatic_audio_output"]["in_call_recording"]["data"]["b64_data"] = (
        base64.b64encode(disclosure.content).decode()
    )
    bot_id = str(ingress._request("POST", "/api/v1/bot/", payload)["id"])
    print(f"bot: {bot_id} — Meet'te katılma isteğini kabul et.")

    transcript = BilingualTranscript()
    translator = OpenAITranslator()
    translator.translate(  # ısıtma
        Utterance(text="Merhaba.", source_lang=args.source_lang,
                  target_lang=args.target_lang, speech_end_ts=0.0)
    )
    pipeline = InterpreterPipeline(
        translator=translator,
        tts=RecallSpeaker(ingress, bot_id, gate),
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        on_flag=lambda r: print(f"  ⚠ düşük güven ({r.flag_reason})"),
        on_record=lambda r: BilingualTranscript.append_jsonl(args.jsonl_out, r),
    )
    stt = RealtimeSTTStream(language=args.source_lang, prompt=LUMOS_TERMS_PROMPT)
    stt.start()
    corrector = TermCorrector()
    suppressor = RepeatSuppressor()
    recent: deque[str] = deque(maxlen=4)

    def pump_audio() -> None:
        while True:
            stt.feed(resample_16k_to_24k(inbound.get()))

    threading.Thread(target=pump_audio, daemon=True).start()
    print("Tercüman hattı canlı — konuş; Ctrl+C: kill-switch + çıkış.")
    try:
        while True:
            try:
                utt = stt.utterances.get(timeout=0.5)
            except queue.Empty:
                continue
            if not utt.text or is_prompt_echo(utt.text, LUMOS_TERMS_PROMPT):
                continue
            heard = corrector.correct(utt.text)
            if suppressor.should_drop(heard, time.monotonic()):
                continue
            print(f"{args.source_lang.upper()}(duyulan)> {heard}")
            record = pipeline.process(
                Utterance(
                    text=heard,
                    source_lang=args.source_lang,
                    target_lang=args.target_lang,
                    speech_end_ts=utt.speech_end_ts,
                    context=tuple(recent),
                )
            )
            recent.append(heard)
            marker = "" if record.delivered else " [TESLİM EDİLMEDİ]"
            print(f"{args.target_lang.upper()}> {record.translated_text}{marker}"
                  f"  ({record.latency_ms:.0f} ms)")
    except KeyboardInterrupt:
        pass
    finally:
        print("\nkill-switch: bot çıkarılıyor...")
        try:
            ingress.kill(bot_id)
        except Exception as exc:
            print(f"leave_call hatası: {type(exc).__name__}")
        stt.stop()
        ngrok_proc.terminate()
        print(transcript.to_markdown())
        print(summarize_latencies_ms(transcript))
        print(f"(bilinmeyen/düşürülen ws mesajı: {dropped_unknown})")
        print(f"medya erken silme için: bot_id={bot_id} (delete_media ayrı komut)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
