"""Local rig: exercises the interpreter chain without a meeting.

Developer harness only — never a user-facing surface.
Text mode (Aşama A): stdin TR line → translate → gate → TTS.
Audio mode (Aşama B): microphone → segmenter (half-duplex gate) → STT →
translate → gate → TTS. Needs the optional deps: pip install .[representative]

Usage:
    python -m representative.local_rig --translator mock
    python -m representative.local_rig --translator openai  # needs OPENAI_API_KEY
    python -m representative.local_rig --audio --translator openai
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from representative.audio import (
    HalfDuplexGate,
    RepeatSuppressor,
    SegmenterConfig,
    UtteranceSegmenter,
    calibrate_rms_threshold,
)
from representative.pipeline import (
    BilingualTranscript,
    ConfidenceGate,
    InterpreterPipeline,
    TranslationResult,
    Translator,
    Utterance,
    summarize_latencies_ms,
)
from representative.routing import Direction, DirectionRouter


class MockTranslator:
    """Deterministic offline stand-in; marks itself clearly as non-translation."""

    def translate(self, utterance: Utterance) -> TranslationResult:
        return TranslationResult(
            text=f"[mock {utterance.source_lang}->{utterance.target_lang}] {utterance.text}",
            confidence=0.99,
            provider="mock",
        )


class OpenAITranslator:
    """Minimal adapter over the existing `openai` dependency.

    Asks for a translation plus a 0-1 self-assessed confidence; if the
    confidence line cannot be parsed the result carries None and the gate
    flags it (slice test T2 behaviour).
    """

    _PROMPT = (
        "Translate the user's utterance from {src} to {dst} for a live business "
        "meeting. Preserve meaning exactly; do not add, soften, or omit "
        "commitments. Your output MUST be in {dst} — even if the input is "
        "partly or entirely in {dst} or mixes languages, never flip direction; "
        "if the input is already fully in {dst}, repeat it in {dst} unchanged. "
        "Your output is spoken aloud by a TTS voice: NEVER add commentary, "
        "apologies, questions, or explanations. If the input is fragmentary, "
        "garbled, or unintelligible, translate what is literally there as best "
        "you can and report a LOW confidence (0.3 or less) — do not guess a "
        "fluent meaning for garbage input. Brand-name repair, ONLY from this "
        "fixed list: Lumos, ChatLumos, We Lock AI, Lumos temsilcisi. Speech "
        "recognition often garbles these (e.g. 'Biolojik', 've lojistiği', "
        "'lojikal' for 'We Lock AI'); when the sentence context clearly refers "
        "to one of the listed brands, use the correct brand name in your "
        "translation and lower confidence to at most 0.7. NEVER apply this to "
        "ordinary words used in their real meaning (e.g. biology/biyolojik in "
        "a science context stays biology), and never repair anything outside "
        "the list. Reply with the translation on the first line and "
        "'confidence: <0-1>' on the second."
    )

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI  # deferred: only needed for the real rig

        self._client = OpenAI()
        self._model = model

    _MEETING_CONTEXT = (
        "Meeting context: this is a business meeting about the Lumos platform; "
        "the speakers represent the company We Lock AI and its products Lumos "
        "and ChatLumos."
    )

    @staticmethod
    def parse_reply(raw: str) -> tuple[str, float | None]:
        """Ayrıştırma test 7 bug'ına dayanıklı: model bazen yalnız güven satırı
        döndürüyor ya da güveni metinle aynı satıra yazıyor — 'confidence: X'
        deseni NEREDE olursa olsun metinden sökülür; kalan boşsa boş döner
        (pipeline boş çeviriyi seslendirmez)."""
        import re

        match = re.search(r"confidence\s*:\s*([0-9.]+)", raw, re.IGNORECASE)
        confidence: float | None = None
        if match:
            try:
                confidence = max(0.0, min(1.0, float(match.group(1))))
            except ValueError:
                confidence = None
        text = re.sub(r"confidence\s*:\s*[0-9.]+", "", raw, flags=re.IGNORECASE).strip()
        return text, confidence

    def translate(self, utterance: Utterance) -> TranslationResult:
        system = self._PROMPT.format(src=utterance.source_lang, dst=utterance.target_lang)
        system += "\n" + self._MEETING_CONTEXT
        if utterance.context:
            recent = "\n".join(f"- {line}" for line in utterance.context)
            system += (
                "\nRecent utterances in this conversation (background only — "
                "translate ONLY the new utterance):\n" + recent
            )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": utterance.text},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        text, confidence = self.parse_reply(raw)
        return TranslationResult(text=text, confidence=confidence, provider=self._model)


class SayTTS:
    """macOS `say` output — measurement-grade only, not the product voice.

    When a HalfDuplexGate is attached, the microphone is muted for the whole
    duration of speech so speaker output can never loop back in (T7).
    """

    def __init__(self, voice: str | None = None, gate: "HalfDuplexGate | None" = None) -> None:
        self._voice = voice
        self._gate = gate

    def speak(self, text: str, lang: str) -> None:
        cmd = ["say"]
        if self._voice:
            cmd += ["-v", self._voice]
        if self._gate is not None:
            with self._gate:
                subprocess.run(cmd + [text], check=False)
        else:
            subprocess.run(cmd + [text], check=False)


def run_audio_mode(
    pipeline: InterpreterPipeline,
    stt,
    duplex_gate: HalfDuplexGate,
    base_config: SegmenterConfig,
    router: DirectionRouter,
) -> None:
    """Blocking mic loop: capture → endpoint → STT → pipeline.

    Test 2 (2026-08-14) sertleştirmeleri:
    - Kapı kontrolü YAKALAMA anında (callback): TTS konuşurken gelen kareler
      kuyruğa hiç girmez — kuyruk birikmesi half-duplex kapıyı deliyordu ve
      rig kendi TTS sesini "duyup" çeviri döngüsüne giriyordu.
    - Her çeviriden sonra kuyruk boşaltılır (birikmiş yankı kuyruğu temizlenir).
    - Açılışta ~1 sn ortam gürültüsü ölçülür, eşik ona göre kalibre edilir.
    - Ardışık aynı metin penceresi içinde düşürülür (halüsinasyon spam'i).
    """
    import dataclasses
    import queue

    import sounddevice as sd  # optional dep, deferred

    frames: queue.Queue[bytes] = queue.Queue()

    def on_audio(indata, _frames, _time, _status) -> None:
        if duplex_gate.listening:
            frames.put(bytes(indata))

    def drain() -> None:
        while True:
            try:
                frames.get_nowait()
            except queue.Empty:
                return

    from representative.stt import LUMOS_TERMS_PROMPT
    from representative.terms import TermCorrector, is_prompt_echo

    from collections import deque

    frame_len = int(base_config.frame_ms * base_config.sample_rate // 1000)
    suppressor = RepeatSuppressor()
    corrector = TermCorrector()
    recent: deque[str] = deque(maxlen=4)
    with sd.RawInputStream(
        samplerate=base_config.sample_rate,
        blocksize=frame_len,
        dtype="int16",
        channels=1,
        callback=on_audio,
    ):
        print("Ortam gürültüsü ölçülüyor (1 sn — sessiz kal)...")
        calibration = [frames.get() for _ in range(1000 // base_config.frame_ms)]
        threshold = calibrate_rms_threshold(calibration, floor=base_config.rms_threshold)
        config = dataclasses.replace(base_config, rms_threshold=threshold)
        segmenter = UtteranceSegmenter(config, gate=duplex_gate)
        print(f"Eşik kalibre edildi: {threshold:.0f}")
        print("Mikrofon açık — TR veya EN konuş (yön kendiliğinden); Ctrl+C ile çık.")
        while True:
            utterance_pcm = segmenter.feed(frames.get())
            if utterance_pcm is None:
                continue
            # Söz-sonu damgası STT'den ÖNCE ve endpointing beklemesi kadar geriye
            # çekilir: algılanan gecikme konuşmacının sustuğu anda başlar.
            speech_end = time.monotonic() - config.end_silence_ms / 1000.0
            heard = stt.transcribe(utterance_pcm, config.sample_rate)
            if not heard.text:
                continue
            if is_prompt_echo(heard.text, LUMOS_TERMS_PROMPT):
                print(f"  (istem yankısı düşürüldü: {heard.text[:40]})")
                continue
            heard_text = corrector.correct(heard.text)
            if suppressor.should_drop(heard_text, time.monotonic()):
                print(f"  (tekrar düşürüldü: {heard_text[:40]})")
                continue
            if heard_text != heard.text:
                print(f"  (terim düzeltildi: {heard.text[:40]} → {heard_text[:40]})")
            decision = router.route(heard_text)
            print(f"{decision.direction.source_lang.upper()}(duyulan)> {heard_text}")
            record = pipeline.process(
                Utterance(
                    text=heard_text,
                    source_lang=decision.direction.source_lang,
                    target_lang=decision.direction.target_lang,
                    speech_end_ts=speech_end,
                    context=tuple(recent),
                )
            )
            recent.append(heard_text)
            print(f"{decision.direction.target_lang.upper()}> {record.translated_text}  "
                  f"({record.latency_ms:.0f} ms, yön: {decision.reason})")
            drain()


def build_translator(name: str) -> Translator:
    if name == "mock":
        return MockTranslator()
    if name == "openai":
        return OpenAITranslator()
    raise ValueError(f"unknown translator: {name}")


def run_realtime_audio_mode(
    pipeline: InterpreterPipeline,
    duplex_gate: HalfDuplexGate,
    router: DirectionRouter,
    vad_silence_ms: int = 800,
) -> None:
    """Streaming mic loop (kalem 3): capture 24k → realtime STT → pipeline.

    Endpointing sunucu VAD'dedir (yerel segmenter/kalibrasyon yok); half-duplex
    kuralı yakalama anında uygulanır: kapı kapalıyken kare websocket'e gitmez.
    """
    import queue as _queue
    from collections import deque

    import sounddevice as sd  # optional dep, deferred

    from representative.realtime_stt import SAMPLE_RATE, RealtimeSTTStream
    from representative.stt import LUMOS_TERMS_PROMPT
    from representative.terms import TermCorrector, is_prompt_echo

    suppressor = RepeatSuppressor()
    corrector = TermCorrector()
    recent: deque[str] = deque(maxlen=4)

    # Çift yönde dil sabitlenmez; yön kararı metinden verilir.
    stream = RealtimeSTTStream(
        language=None if router.bidirectional else router.default_direction.source_lang,
        prompt=LUMOS_TERMS_PROMPT,
        vad_silence_ms=vad_silence_ms,
    )
    stream.start()

    def on_audio(indata, _frames, _time, _status) -> None:
        if duplex_gate.listening:
            stream.feed(bytes(indata))

    frame_len = int(SAMPLE_RATE * 0.06)  # 60 ms
    print("Mikrofon açık (akışlı) — TR veya EN konuş (yön kendiliğinden); Ctrl+C ile çık.")
    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=frame_len,
            dtype="int16",
            channels=1,
            callback=on_audio,
        ):
            while True:
                try:
                    utt = stream.utterances.get(timeout=0.5)
                except _queue.Empty:
                    continue
                if not utt.text:
                    continue
                if is_prompt_echo(utt.text, LUMOS_TERMS_PROMPT):
                    print(f"  (istem yankısı düşürüldü: {utt.text[:40]})")
                    continue
                heard_text = corrector.correct(utt.text)
                if suppressor.should_drop(heard_text, time.monotonic()):
                    print(f"  (tekrar düşürüldü: {heard_text[:40]})")
                    continue
                if heard_text != utt.text:
                    print(f"  (terim düzeltildi: {utt.text[:40]} → {heard_text[:40]})")
                decision = router.route(heard_text)
                print(f"{decision.direction.source_lang.upper()}(duyulan)> {heard_text}")
                record = pipeline.process(
                    Utterance(
                        text=heard_text,
                        source_lang=decision.direction.source_lang,
                        target_lang=decision.direction.target_lang,
                        speech_end_ts=utt.speech_end_ts,
                        context=tuple(recent),
                    )
                )
                recent.append(heard_text)
                marker = "" if record.delivered else " [TESLİM EDİLMEDİ]"
                print(
                    f"{decision.direction.target_lang.upper()}> {record.translated_text}{marker}  "
                    f"({record.latency_ms:.0f} ms, yön: {decision.reason})"
                )
    finally:
        stream.stop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Representative Faz 0 local rig")
    parser.add_argument("--translator", default="mock", choices=("mock", "openai"))
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--voice", default=None, help="macOS say voice name")
    parser.add_argument("--audio", action="store_true", help="microphone mode (Aşama B)")
    parser.add_argument(
        "--stt-backend",
        default="realtime",
        choices=("cloud", "local", "realtime"),
        help="realtime=akışlı (VARSAYILAN — test 7/8 canlı kanıtı: medyan "
        "1.92/2.28s); cloud=toplu gpt-4o-mini-transcribe; local=faster-whisper",
    )
    parser.add_argument("--stt-model", default="small", help="faster-whisper model size (local)")
    parser.add_argument("--source-lang", default="tr", choices=("tr", "en"))
    parser.add_argument("--target-lang", default="en", choices=("tr", "en"))
    parser.add_argument(
        "--direction",
        default="auto",
        choices=("auto", "fixed"),
        help="auto (varsayılan): yön her söz için duyulan dile göre belirlenir; "
        "--source/--target yalnız dil tespit edilemeyen kısa sözlerde geçerli "
        "varsayılan yöndür. fixed: eski tek-yön davranışı",
    )
    parser.add_argument("--jsonl-out", default=None, help="prova ölçüm kaydı (jsonl) yolu")
    parser.add_argument(
        "--vad-silence-ms",
        type=int,
        default=800,
        help="realtime backend sunucu VAD sessizliği (test 7: 600ms ikinci-dil "
        "İngilizce temposunu fazla böldü; 800 varsayılan, prova ölçer)",
    )
    parser.add_argument(
        "--end-silence-ms",
        type=int,
        default=900,
        help="söz sonu sayılan sessizlik (test 3: 700ms cümle ortasında böldü, "
        "tarih kaybettirdi; +200ms gecikme pahasına bütünlük)",
    )
    args = parser.parse_args(argv)
    if args.source_lang == args.target_lang:
        parser.error("source and target languages must differ")

    duplex_gate = HalfDuplexGate()
    transcript = BilingualTranscript()

    def on_flag(r):
        print(f"  ⚠ düşük güven ({r.flag_reason})")

    translator = build_translator(args.translator)
    pipeline = InterpreterPipeline(
        translator=translator,
        tts=SayTTS(voice=args.voice, gate=duplex_gate),
        gate=ConfidenceGate(args.threshold),
        transcript=transcript,
        on_flag=on_flag,
        on_record=(
            (lambda r: BilingualTranscript.append_jsonl(args.jsonl_out, r))
            if args.jsonl_out
            else None
        ),
    )

    src_lang, dst_lang = args.source_lang, args.target_lang
    router = DirectionRouter(
        Direction(src_lang, dst_lang), bidirectional=args.direction == "auto"
    )
    if args.audio:
        import signal

        from representative.stt import LUMOS_TERMS_PROMPT, FasterWhisperSTT, OpenAICloudSTT

        def on_term(_sig, _frame):
            # SIGTERM'de de temiz kapanış (test 2: SIGINT engelli anlarda yakalanmadı)
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, on_term)
        if args.translator == "openai":
            # Isıtma (kalem 3): ilk gerçek söz soğuk TLS/oturum kurulumuna
            # (+~1.2 sn) denk gelmesin
            pipeline_warmup = Utterance(
                text="Merhaba.", source_lang=src_lang, target_lang=dst_lang, speech_end_ts=0.0
            )
            try:
                translator.translate(pipeline_warmup)
                print("Çevirmen ısıtıldı.")
            except Exception as exc:
                print(f"Isıtma başarısız (devam ediliyor): {type(exc).__name__}")
        if args.stt_backend == "realtime":
            try:
                run_realtime_audio_mode(pipeline, duplex_gate, router, args.vad_silence_ms)
            except KeyboardInterrupt:
                pass
            print("\n--- transcript ---")
            print(transcript.to_markdown())
            print(summarize_latencies_ms(transcript))
            if args.jsonl_out:
                with open(args.jsonl_out, "w", encoding="utf-8") as f:
                    f.write(transcript.to_jsonl() + "\n")
                print(f"ölçüm kaydı: {args.jsonl_out}")
            return 0
        # Çift yönde toplu STT'ye de dil verilmez (sağlayıcı kendisi tespit eder).
        stt_lang = None if args.direction == "auto" else src_lang
        if args.stt_backend == "cloud":
            stt = OpenAICloudSTT(language=stt_lang, prompt=LUMOS_TERMS_PROMPT)
        else:
            stt = FasterWhisperSTT(
                model_size=args.stt_model, language=stt_lang, initial_prompt=LUMOS_TERMS_PROMPT
            )
        base_config = SegmenterConfig(end_silence_ms=args.end_silence_ms)
        try:
            run_audio_mode(pipeline, stt, duplex_gate, base_config, router)
        except KeyboardInterrupt:
            pass
    else:
        label = "TR/EN" if router.bidirectional else src_lang.upper()
        print(f"{label} cümle yaz, boş satır = çık.")
        while True:
            try:
                line = input(f"{label}> ").strip()
            except EOFError:
                break
            if not line:
                break
            decision = router.route(line)
            record = pipeline.process(
                Utterance(
                    text=line,
                    source_lang=decision.direction.source_lang,
                    target_lang=decision.direction.target_lang,
                    speech_end_ts=time.monotonic(),
                )
            )
            print(f"{decision.direction.target_lang.upper()}> {record.translated_text}  "
                  f"({record.latency_ms:.0f} ms, yön: {decision.reason})")

    print("\n--- transcript ---")
    print(transcript.to_markdown())
    print(summarize_latencies_ms(transcript))
    if args.jsonl_out:
        with open(args.jsonl_out, "w", encoding="utf-8") as f:
            f.write(transcript.to_jsonl() + "\n")
        print(f"ölçüm kaydı: {args.jsonl_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
