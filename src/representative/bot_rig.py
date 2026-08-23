"""In-meeting interpreter rig: Recall inbound audio → core → bot voice out.

Prova 1 teşhisi (2026-08-17, kurucu): join/disclosure PASS; "Meet sesi →
STT → çeviri → TTS → bota geri ses" zinciri BAĞLI DEĞİLDİ. Bu modül o kulağı
bağlar:

    Recall realtime_endpoints (websocket push, 16k PCM)
      → ngrok tüneli → yerel ws sunucu (bu süreç)
      → 16k→24k → RealtimeSTTStream → filtreler → InterpreterPipeline
      → RecallSpeaker (chunked OpenAI TTS mp3 → output_audio)

Half-duplex: kapı yalnız o an giden klip (+echo kuyruğu) boyunca kapalı;
uzun paragrafın tamamı için kuyruk tutulmaz. Yeni söz kuyruktaki kalan
klipleri iptal eder (barge-in). Echo için mevcut klip bitene kadar dinleme
kapalı kalır.
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
from representative.avatar import (
    AvatarStateController,
    MeetAvatarAssets,
    load_meet_avatar_assets,
)
from representative.meeting_ingress import (
    DISCLOSURE_LINE_EN,
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
    undetected_language_record,
)
from representative.repair import bilingual_repair_line
from representative.routing import Direction, DirectionRouter
from representative.segmentation import Fragment, UtteranceCoalescer
from representative.stt import LUMOS_TERMS_PROMPT
from representative.transcript_view import (
    attribution_note,
    format_heard,
    format_telemetry,
    format_translation,
)
from representative.tts_playback import ChunkedTtsPlayer, estimate_speech_seconds

RECALL_INBOUND_RATE = 16000

# Recall bot durumları: oturumun kendiliğinden kapanacağı uç durumlar
TERMINAL_BOT_STATUSES = frozenset({"call_ended", "done", "fatal"})
WAITING_ROOM_TIMEOUT_S = 300  # bekleme odasında 5 dk kabul edilmezse vazgeç
# V1 sesli beyan yalnız İngilizce (kurucu kararı 2026-08-20): tek ses akışında
# iki dil süreyi uzatıyor ve anlaşılırlığı düşürüyordu. TR metni yazılı kanal için
# saklanıyor, seslendirilmiyor.
DISCLOSURE_GUARD_S = estimate_speech_seconds(DISCLOSURE_LINE_EN) + 1.0


def is_terminal_status(code: str | None) -> bool:
    return code in TERMINAL_BOT_STATUSES


class DisclosureInputGuard:
    """Drop inbound audio while Recall plays the automatic disclosure."""

    def __init__(self, duration_s: float = DISCLOSURE_GUARD_S) -> None:
        self._duration_s = duration_s
        self._deadline: float | None = None

    def mark_connected(self, now: float) -> None:
        if self._deadline is None:
            self._deadline = now + self._duration_s

    def allows_audio(self, now: float) -> bool:
        return self._deadline is not None and now >= self._deadline


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


def build_realtime_endpoint(wss_url: str) -> dict[str, Any]:
    if not wss_url.startswith("wss://"):
        raise ValueError("realtime endpoint wss:// olmalı (fail-closed)")
    return {"type": "websocket", "url": wss_url, "events": ["audio_mixed_raw.data"]}


class RecallSpeaker:
    """Chunked TTS: first Meet clip defines first-audio; rest is barge-in-safe.

    Recall output_audio takes a whole MP3 — true PCM streaming is not available.
    Short sentence chunks cut time-to-first-audio and stop the half-duplex gate
    from covering the entire paragraph.
    """

    def __init__(
        self,
        ingress: RecallMeetingIngress,
        bot_id: str,
        gate: HalfDuplexGate,
        avatar_assets: MeetAvatarAssets,
    ) -> None:
        from openai import OpenAI

        self._client = OpenAI()
        self._ingress = ingress
        self._bot_id = bot_id
        self._gate = gate
        self._avatar = AvatarStateController(
            publish=lambda jpeg: ingress.show_avatar(bot_id, jpeg),
            assets=avatar_assets,
            on_error=lambda exc: print(
                f"avatar güncellenemedi: {type(exc).__name__} (çeviri sürüyor)"
            ),
        )
        self._player = ChunkedTtsPlayer(
            synthesize=self._synthesize,
            deliver=self._deliver,
            gate=gate,
            hold_after_deliver=True,
        )

    def _synthesize(self, text: str, _lang: str) -> bytes:
        resp = self._client.audio.speech.create(
            model="gpt-4o-mini-tts", voice="onyx", input=text, response_format="mp3"
        )
        return resp.content

    def _deliver(self, payload: bytes, _text: str, _lang: str) -> None:
        # speaking durumu GERÇEK oynatma başlangıcına bağlanır. speak() bloklayan
        # bir yüklemedir; timer ondan önce kurulursa sayaç ağ süresi boyunca işler
        # ve Meet hâlâ sesi çalarken avatar idle'a döner. Chunked TTS'te bu klipler
        # arası idle titremesine dönüşür.
        self._ingress.speak(self._bot_id, base64.b64encode(payload).decode())
        self._avatar.speaking_for(estimate_speech_seconds(_text))

    def barge_in(self) -> int:
        self._avatar.idle()
        return self._player.barge_in()

    def speak(self, text: str, lang: str):
        return self._player.speak(text, lang)


TUNNEL_PROBE_EVENT = "lumos.tunnel_probe"


def verify_tunnel(
    public_wss: str,
    received: "threading.Event",
    timeout_s: float = 45.0,
) -> None:
    """Fail-closed tünel öz-testi (canlı insan testi 2 FAIL dersi, 2026-08-17):
    bot yaratılmadan ÖNCE genel wss adresine dışarıdan bağlanıp işaret
    mesajının yerel sunucuya ulaştığı kanıtlanır. Ulaşmazsa bot HİÇ
    yaratılmaz — sessiz altyapı arızası (ölü/yarışan tünel ajanı) toplantıya
    'sağır bot' sokmak yerine sert hataya dönüşür."""
    import socket as _socket

    from websockets.sync.client import connect

    host = public_wss.removeprefix("wss://").split("/")[0]

    def _open():
        try:
            return connect(public_wss, open_timeout=10)
        except _socket.gaierror:
            # Canlı bulgu (2026-08-17): macOS sistem çözücüsü taze quick-tunnel
            # adlarını çözemeyebiliyor (negatif önbellek/filtre) — DNS sunucusu
            # çözerken getaddrinfo düşüyor. Recall kendi altyapısından çözer;
            # öz-testin yanlış-negatif vermemesi için 1.1.1.1'den IP alıp SNI
            # korumalı doğrudan bağlanılır.
            out = subprocess.run(
                ["dig", "+short", host, "@1.1.1.1"], capture_output=True, text=True, timeout=10
            ).stdout
            ip = next((line for line in out.splitlines() if line and line[0].isdigit()), None)
            if not ip:
                raise
            sock = _socket.create_connection((ip, 443), timeout=10)
            return connect(public_wss, sock=sock, server_hostname=host, open_timeout=10)

    deadline = time.monotonic() + timeout_s
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with _open() as ws:
                ws.send(json.dumps({"event": TUNNEL_PROBE_EVENT}))
                if received.wait(timeout=10):
                    return
                last_exc = RuntimeError("probe yerel sunucuya ulaşmadı")
        except Exception as exc:
            last_exc = exc
        time.sleep(3)
    raise RuntimeError(
        f"TÜNEL ÖZ-TESTİ BAŞARISIZ ({type(last_exc).__name__}: {last_exc}) — "
        "bot yaratılmadı. Tünel ajanlarını temizleyip yeniden dene."
    ) from last_exc


def start_cloudflared(port: int) -> tuple[subprocess.Popen, str]:
    """Birincil tünel (2026-08-17 kök neden: ngrok ücretsiz katman ara sayfası
    ERR_NGROK_6030 ile tarayıcı-olmayan ws istemcilerini 400'lüyor — Recall
    bağlanamadı). cloudflared quick tunnel ws'i ara sayfasız geçirir."""
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 30
    url = None
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        if ".trycloudflare.com" in line:
            for token in line.replace("|", " ").split():
                if token.startswith("https://") and ".trycloudflare.com" in token:
                    url = token.strip()
                    break
        if url:
            threading.Thread(  # boru dolmasın diye kalan logu tüket
                target=lambda: [None for _ in proc.stdout], daemon=True
            ).start()
            return proc, url.replace("https://", "wss://")
    proc.terminate()
    raise RuntimeError("cloudflared tüneli açılamadı")


def start_ngrok(port: int) -> tuple[subprocess.Popen, str]:
    # Yarışan ajan temizliği: aynı sabit alan adı için ikinci bir ngrok
    # ajanı kenarın ws bağlantılarını 400 ile reddetmesine yol açtı
    subprocess.run(["pkill", "-9", "-f", "ngrok http"], check=False)
    for _ in range(50):
        try:
            urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=1)
            time.sleep(0.1)
        except Exception:
            break
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


def start_verified_tunnel(
    port: int,
    probe_received: threading.Event,
    attempts: int = 3,
) -> tuple[subprocess.Popen, str]:
    """Create and verify a tunnel before bot creation; rotate flaky DNS names."""
    if attempts < 1:
        raise ValueError("tunnel attempts must be positive")
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        proc: subprocess.Popen | None = None
        probe_received.clear()
        try:
            try:
                proc, wss_url = start_cloudflared(port)
            except (FileNotFoundError, RuntimeError) as exc:
                print(f"cloudflared yok/başarısız ({exc}) — ngrok'a düşülüyor")
                proc, wss_url = start_ngrok(port)
            print(f"tünel: {wss_url}")
            verify_tunnel(wss_url, probe_received)
            return proc, wss_url
        except Exception as exc:
            last_exc = exc
            if proc is not None:
                proc.terminate()
            if attempt < attempts:
                print(f"tünel öz-testi başarısız — yeni adres deneniyor ({attempt}/{attempts})")
    raise RuntimeError(f"{attempts} tünel denemesi de doğrulanamadı; bot yaratılmadı") from last_exc


def main(argv: list[str] | None = None) -> int:
    from websockets.sync.server import serve  # openai[realtime] ile kurulu

    from representative.local_rig import OpenAITranslator
    from representative.realtime_stt import RealtimeSTTStream
    from representative.terms import TermCorrector, is_prompt_echo

    parser = argparse.ArgumentParser(description="Faz 0 toplantı-içi tercüman rig'i")
    parser.add_argument("--meeting-url")
    parser.add_argument("--source-lang", default="tr", choices=("tr", "en"))
    parser.add_argument("--target-lang", default="en", choices=("tr", "en"))
    parser.add_argument(
        "--direction",
        default="auto",
        choices=("auto", "fixed"),
        help="auto (varsayılan): yön her söz için duyulan dile göre belirlenir "
        "— karşı taraf İngilizce konuşunca EN→TR'ye kendiliğinden döner; "
        "--source/--target yalnız dil tespit edilemeyen kısa sözlerde geçerli "
        "varsayılan yöndür. fixed: canlı insan testi 4'teki eski tek-yön davranışı",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--jsonl-out", default="prova_bot.jsonl")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="BOTSUZ ön uçuş: env + tünel öz-testi + çevirmen/STT bağlantısı "
        "doğrulanır, Recall botu YARATILMAZ, toplantı linki gerekmez. Canlı "
        "provadan önce koş — geçmişte canlı testi yakan hatalar burada görünür",
    )
    parser.add_argument(
        "--keep-media",
        action="store_true",
        help="Varsayılan davranış oturum sonunda erken delete_media'dır "
        "(kurucu şartı); teşhis gerekiyorsa bu bayrakla 24h penceresi korunur",
    )
    args = parser.parse_args(argv)
    if args.source_lang == args.target_lang:
        parser.error("source and target languages must differ")
    if not args.preflight and not args.meeting_url:
        parser.error("--meeting-url zorunlu (yalnız --preflight ile atlanabilir)")
    missing = [v for v in ("RECALL_API_KEY", "RECALL_REGION_URL", "OPENAI_API_KEY")
               if not os.environ.get(v)]
    if missing:
        # Fail-loud: eksik anahtar canlı koşuda tünelden sonra patlamasın.
        parser.error("eksik ortam değişkeni: " + ", ".join(missing))

    gate = HalfDuplexGate()
    inbound: queue.Queue[bytes] = queue.Queue()
    probe_received = threading.Event()
    disclosure_guard = DisclosureInputGuard()
    dropped_unknown = 0

    def on_ws(conn) -> None:
        nonlocal dropped_unknown
        first = True
        for raw in conn:
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                dropped_unknown += 1
                continue
            if msg.get("event") == TUNNEL_PROBE_EVENT:
                probe_received.set()
                continue
            if first:
                print("Recall websocket bağlandı.")
                disclosure_guard.mark_connected(time.monotonic())
                first = False
            b64 = extract_audio_b64(msg)
            if b64 is None:
                dropped_unknown += 1
                continue
            if disclosure_guard.allows_audio(time.monotonic()) and gate.listening:
                inbound.put(base64.b64decode(b64))

    server = serve(on_ws, "127.0.0.1", args.port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    ngrok_proc, wss_url = start_verified_tunnel(args.port, probe_received)
    print("tünel öz-testi: GEÇTİ (uçtan uca ws doğrulandı)")

    if args.preflight:
        # Botsuz ön uçuş: pahalı olan her şey (tünel, anahtarlar, çevirmen,
        # akışlı STT oturumu) burada denenir; Recall botu YARATILMAZ.
        from representative.local_rig import OpenAITranslator as _T
        from representative.realtime_stt import RealtimeSTTStream as _S

        warm = _T().translate(
            Utterance(text="Merhaba.", source_lang="tr", target_lang="en", speech_end_ts=0.0)
        )
        print(f"çevirmen: GEÇTİ (örnek çıktı: {warm.text[:40]!r})")
        probe_stt = _S(language=None, prompt=LUMOS_TERMS_PROMPT)
        probe_stt.start()
        probe_stt.stop()
        print("akışlı STT oturumu: GEÇTİ")
        if ngrok_proc is not None:
            ngrok_proc.terminate()
        print("\nÖN UÇUŞ TAMAM — canlı prova için hazır (bot yaratılmadı).")
        return 0

    ingress = RecallMeetingIngress(
        REHEARSAL_RETENTION, os.environ["RECALL_REGION_URL"]
    )
    avatar_assets = load_meet_avatar_assets()
    from openai import OpenAI

    disclosure = OpenAI().audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="onyx",
        input=DISCLOSURE_LINE_EN,
        response_format="mp3",
    )
    payload = build_recall_bot_payload(
        args.meeting_url,
        REHEARSAL_RETENTION,
        internal_ref="faz0-bot-prova",
        disclosure_mp3_b64=base64.b64encode(disclosure.content).decode(),
        avatar_idle_jpeg_b64=avatar_assets.idle_jpeg_b64,
    )
    # Prova 2 canlı doğrulaması: realtime olayları için audio_mixed_raw
    # artefact'ı açıkça konfigüre edilmeli (Recall 400 gövdesinden)
    payload["recording_config"]["audio_mixed_raw"] = {}
    payload["recording_config"]["realtime_endpoints"] = [build_realtime_endpoint(wss_url)]
    bot_id = str(ingress._request("POST", "/api/v1/bot/", payload)["id"])
    print(f"bot: {bot_id} — Meet'te katılma isteğini kabul et.")

    # Oturum otomasyonu (2026-08-17): toplantı bitişini Recall durumundan
    # algıla → kendiliğinden kapan. Bekleme odasında 5 dk kabul edilmezse
    # sessizce asılı kalma, gürültülü vazgeç (fail-loud).
    stop_event = threading.Event()
    end_reason: list[str] = []

    def poll_bot_status() -> None:
        waiting_since: float | None = None
        while not stop_event.is_set():
            try:
                info = ingress._request("GET", f"/api/v1/bot/{bot_id}/")
                changes = info.get("status_changes", [])
                code = changes[-1]["code"] if changes else None
            except Exception:
                time.sleep(15)
                continue
            if is_terminal_status(code):
                end_reason.append(str(code))
                stop_event.set()
                return
            if code == "in_waiting_room":
                waiting_since = waiting_since or time.monotonic()
                if time.monotonic() - waiting_since > WAITING_ROOM_TIMEOUT_S:
                    end_reason.append("waiting_room_timeout")
                    stop_event.set()
                    return
            else:
                waiting_since = None
            time.sleep(15)

    threading.Thread(target=poll_bot_status, daemon=True).start()

    transcript = BilingualTranscript()
    router = DirectionRouter(
        Direction(args.source_lang, args.target_lang),
        bidirectional=args.direction == "auto",
    )
    translator = OpenAITranslator()
    translator.translate(  # ısıtma
        Utterance(text="Merhaba.", source_lang=args.source_lang,
                  target_lang=args.target_lang, speech_end_ts=0.0)
    )
    speaker = RecallSpeaker(ingress, bot_id, gate, avatar_assets)
    pipeline = InterpreterPipeline(
        translator=translator,
        tts=speaker,
        gate=ConfidenceGate(0.8),
        transcript=transcript,
        on_flag=lambda r: print(f"  ⚠ düşük güven ({r.flag_reason})"),
        on_record=lambda r: BilingualTranscript.append_jsonl(args.jsonl_out, r),
    )
    # auto yönde dil sabitlenmez: sağlayıcı duyduğu dili kendisi tespit eder,
    # yön kararını router metinden verir (canlı insan testi 4 papağan bulgusu).
    stt = RealtimeSTTStream(
        language=None if args.direction == "auto" else args.source_lang,
        prompt=LUMOS_TERMS_PROMPT,
    )
    stt.start()
    corrector = TermCorrector()
    suppressor = RepeatSuppressor()
    recent: deque[str] = deque(maxlen=4)

    def pump_audio() -> None:
        while True:
            stt.feed(resample_16k_to_24k(inbound.get()))

    threading.Thread(target=pump_audio, daemon=True).start()
    print("Tercüman hattı canlı — toplantı bitince kendiliğinden kapanır; Ctrl+C: kill-switch.")
    print(attribution_note())
    # Parça birleştirme (2026-08-23): VAD'in ortadan kestiği yarım sözler
    # ayrı ayrı çevrilmesin. Kuyruk zaman aşımı hold_s'ten kısa tutulur ki
    # bekleyen parça zamanında yayımlansın.
    coalescer = UtteranceCoalescer()
    try:
        while not stop_event.is_set():
            try:
                utt = stt.utterances.get(timeout=0.2)
            except queue.Empty:
                segments = coalescer.due(time.monotonic())
            else:
                if not utt.text or is_prompt_echo(utt.text, LUMOS_TERMS_PROMPT):
                    continue
                heard = corrector.correct(utt.text)
                if suppressor.should_drop(heard, time.monotonic()):
                    continue
                segments = coalescer.offer(
                    Fragment(
                        text=heard,
                        speech_end_ts=utt.speech_end_ts,
                        stt_final_ts=time.monotonic(),
                    )
                )
            for segment in segments:
                heard = segment.text
                decision = router.route(heard)
                if decision.reason == "fallback_unknown":
                    # Kurucu kararı 2026-08-23: dil belirlenemezse sessizce
                    # varsayılan yöne (TR) düşülmez — hangi dili konuştuğu
                    # bilinmediği için iki dilli tekrar isteği gider. İstek ortak
                    # ses kanalına basılır: toplantıdaki herkes duyar.
                    # (Birleştirmeden SONRA bakılır: parça birleşince dil
                    # sinyali güçlenebilir, gereksiz tekrar isteği çıkmasın.)
                    print()
                    print(f"Duyulan (?): {heard}")
                    print("   Lumos: dil belirlenemedi — tekrar istendi")
                    pipeline.interrupt_playback()
                    speaker.speak(bilingual_repair_line(), args.source_lang)
                    now = time.monotonic()
                    unrouted = undetected_language_record(
                        heard,
                        latency_ms=max(0.0, (now - segment.speech_end_ts) * 1000.0),
                        recorded_at=now,
                    )
                    transcript.append(unrouted)
                    BilingualTranscript.append_jsonl(args.jsonl_out, unrouted)
                    continue
                merge_note = f"  (+{segment.parts - 1} parça)" if segment.merged else ""
                print()
                print(format_heard(decision.direction.source_lang, heard) + merge_note)
                # Barge-in: yeni söz gelince kuyruktaki klipler düşer (chunked TTS).
                pipeline.interrupt_playback()
                record = pipeline.process(
                    Utterance(
                        text=heard,
                        source_lang=decision.direction.source_lang,
                        target_lang=decision.direction.target_lang,
                        speech_end_ts=segment.speech_end_ts,
                        context=tuple(recent),
                        stt_final_ts=segment.stt_final_ts,
                    )
                )
                recent.append(heard)
                print(format_translation(record))
                print(format_telemetry(record, decision.reason))
    except KeyboardInterrupt:
        end_reason.append("kill_switch")
    finally:
        stop_event.set()
        reason = end_reason[0] if end_reason else "bilinmiyor"
        print(f"\noturum kapanıyor (sebep: {reason})...")
        try:
            ingress.kill(bot_id)
        except Exception as exc:
            print(f"leave_call: {type(exc).__name__} (bot zaten çıkmış olabilir)")
        stt.stop()
        ngrok_proc.terminate()
        if not args.keep_media:
            # Kurucu şartı: sorunsuz oturum sonrası 24h beklenmez, erken sil.
            # Çıkış anında medya işleniyor olabilir → kısa bekleme + yeniden dene.
            deleted = False
            for _ in range(6):
                try:
                    ingress.delete_media(bot_id)
                    deleted = True
                    break
                except Exception:
                    time.sleep(5)
            print("medya erken silme:", "OK" if deleted else
                  f"BAŞARISIZ — elle: delete_media bot_id={bot_id}")
        print(transcript.to_markdown())
        summary = summarize_latencies_ms(transcript)
        print(summary)
        if summary["first_audio_budget_pass"]:
            print(
                "first-audio bütçe: p50≤2.5s p90≤4s — bu örnek geçti "
                "(canlı Meet değilse PASS deme)"
            )
        else:
            print(
                "first-audio bütçe: FAIL — PASS deme "
                f"(p50={summary['p50_ms']:.0f} p90={summary['p90_ms']:.0f} ms; "
                f"en büyük bekleme: {summary['largest_wait'] or 'yok'})"
            )
        print(f"(bilinmeyen/düşürülen ws mesajı: {dropped_unknown})")
        if coalescer.dropped_fillers:
            print(f"(elenen dolgu parçası: {len(coalescer.dropped_fillers)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
