"""Text-mode local rig: exercises translate → gate → TTS without STT.

Developer harness only (slice doc, Aşama A) — never a user-facing surface.
Reads one Turkish line per prompt from stdin, translates to English, speaks
via macOS `say`, prints the flag state and latency, and dumps the bilingual
transcript on exit.

Usage:
    python -m representative.local_rig --translator mock
    python -m representative.local_rig --translator openai  # needs OPENAI_API_KEY
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

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
    """macOS `say` output — measurement-grade only, not the product voice."""

    def __init__(self, voice: str | None = None) -> None:
        self._voice = voice

    def speak(self, text: str, lang: str) -> None:
        cmd = ["say"]
        if self._voice:
            cmd += ["-v", self._voice]
        subprocess.run(cmd + [text], check=False)


def build_translator(name: str) -> Translator:
    if name == "mock":
        return MockTranslator()
    if name == "openai":
        return OpenAITranslator()
    raise ValueError(f"unknown translator: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Representative Faz 0 text-mode rig")
    parser.add_argument("--translator", default="mock", choices=("mock", "openai"))
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--voice", default=None, help="macOS say voice name")
    args = parser.parse_args(argv)

    transcript = BilingualTranscript()
    pipeline = InterpreterPipeline(
        translator=build_translator(args.translator),
        tts=SayTTS(voice=args.voice),
        gate=ConfidenceGate(args.threshold),
        transcript=transcript,
        on_flag=lambda r: print(f"  ⚠ düşük güven ({r.flag_reason})"),
    )

    print("TR cümle yaz, boş satır = çık.")
    while True:
        try:
            line = input("TR> ").strip()
        except EOFError:
            break
        if not line:
            break
        record = pipeline.process(
            Utterance(
                text=line,
                source_lang="tr",
                target_lang="en",
                speech_end_ts=time.monotonic(),
            )
        )
        print(f"EN> {record.translated_text}  ({record.latency_ms:.0f} ms)")

    print("\n--- transcript ---")
    print(transcript.to_markdown())
    print(summarize_latencies_ms(transcript))
    return 0


if __name__ == "__main__":
    sys.exit(main())
