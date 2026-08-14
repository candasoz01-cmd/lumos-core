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

from representative.audio import HalfDuplexGate, SegmenterConfig, UtteranceSegmenter
from representative.pipeline import (
    BilingualTranscript,
    ConfidenceGate,
    InterpreterPipeline,
    TranslationResult,
    Translator,
    Utterance,
    summarize_latencies_ms,
)


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
        "commitments. Reply with the translation on the first line and "
        "'confidence: <0-1>' on the second."
    )

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI  # deferred: only needed for the real rig

        self._client = OpenAI()
        self._model = model

    def translate(self, utterance: Utterance) -> TranslationResult:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": self._PROMPT.format(
                        src=utterance.source_lang, dst=utterance.target_lang
                    ),
                },
                {"role": "user", "content": utterance.text},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        lines = raw.splitlines()
        confidence: float | None = None
        text = raw
        if len(lines) >= 2 and lines[-1].lower().startswith("confidence:"):
            text = "\n".join(lines[:-1]).strip()
            try:
                confidence = max(0.0, min(1.0, float(lines[-1].split(":", 1)[1])))
            except ValueError:
                confidence = None
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
    pipeline: InterpreterPipeline, segmenter, stt, sample_rate: int, src_lang: str, dst_lang: str
) -> None:
    """Blocking mic loop: capture → endpoint → STT → pipeline."""
    import queue

    import sounddevice as sd  # optional dep, deferred

    frames: queue.Queue[bytes] = queue.Queue()

    def on_audio(indata, _frames, _time, _status) -> None:
        frames.put(bytes(indata))

    frame_len = int(sample_rate * 0.03)  # 30 ms
    print(f"Mikrofon açık — {src_lang.upper()} konuş; Ctrl+C ile çık.")
    with sd.RawInputStream(
        samplerate=sample_rate,
        blocksize=frame_len,
        dtype="int16",
        channels=1,
        callback=on_audio,
    ):
        while True:
            utterance_pcm = segmenter.feed(frames.get())
            if utterance_pcm is None:
                continue
            heard = stt.transcribe(utterance_pcm, sample_rate)
            if not heard.text:
                continue
            print(f"{src_lang.upper()}(duyulan)> {heard.text}")
            record = pipeline.process(
                Utterance(
                    text=heard.text,
                    source_lang=src_lang,
                    target_lang=dst_lang,
                    speech_end_ts=time.monotonic(),
                )
            )
            print(f"{dst_lang.upper()}> {record.translated_text}  ({record.latency_ms:.0f} ms)")


def build_translator(name: str) -> Translator:
    if name == "mock":
        return MockTranslator()
    if name == "openai":
        return OpenAITranslator()
    raise ValueError(f"unknown translator: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Representative Faz 0 local rig")
    parser.add_argument("--translator", default="mock", choices=("mock", "openai"))
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--voice", default=None, help="macOS say voice name")
    parser.add_argument("--audio", action="store_true", help="microphone mode (Aşama B)")
    parser.add_argument("--stt-model", default="small", help="faster-whisper model size")
    parser.add_argument("--source-lang", default="tr", choices=("tr", "en"))
    parser.add_argument("--target-lang", default="en", choices=("tr", "en"))
    parser.add_argument("--jsonl-out", default=None, help="prova ölçüm kaydı (jsonl) yolu")
    args = parser.parse_args(argv)
    if args.source_lang == args.target_lang:
        parser.error("source and target languages must differ")

    duplex_gate = HalfDuplexGate()
    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=build_translator(args.translator),
        tts=SayTTS(voice=args.voice, gate=duplex_gate),
        gate=ConfidenceGate(args.threshold),
        transcript=transcript,
        on_flag=lambda r: print(f"  ⚠ düşük güven ({r.flag_reason})"),
    )

    src_lang, dst_lang = args.source_lang, args.target_lang
    if args.audio:
        from representative.stt import LUMOS_TERMS_PROMPT, FasterWhisperSTT

        config = SegmenterConfig()
        segmenter = UtteranceSegmenter(config, gate=duplex_gate)
        stt = FasterWhisperSTT(
            model_size=args.stt_model, language=src_lang, initial_prompt=LUMOS_TERMS_PROMPT
        )
        try:
            run_audio_mode(pipeline, segmenter, stt, config.sample_rate, src_lang, dst_lang)
        except KeyboardInterrupt:
            pass
    else:
        print(f"{src_lang.upper()} cümle yaz, boş satır = çık.")
        while True:
            try:
                line = input(f"{src_lang.upper()}> ").strip()
            except EOFError:
                break
            if not line:
                break
            record = pipeline.process(
                Utterance(
                    text=line,
                    source_lang=src_lang,
                    target_lang=dst_lang,
                    speech_end_ts=time.monotonic(),
                )
            )
            print(f"{dst_lang.upper()}> {record.translated_text}  ({record.latency_ms:.0f} ms)")

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
