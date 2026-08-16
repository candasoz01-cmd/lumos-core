"""STT model benchmark for the Representative Faz 0 latency budget (macOS dev tool).

Synthesizes Turkish test sentences with `say -v Yelda`, runs them through
FasterWhisperSTT for each model size, and reports warm latency + exact text.
Needs: .[representative] deps, macOS say/afconvert. Not a CI test.

Usage: PYTHONPATH=src .venv/bin/python scripts/representative_stt_bench.py [sizes...]
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

SENTENCES = {
    "S1-normal": "Toplantıyı yarın saat üçe alalım ve teklifi birlikte gözden geçirelim.",
    "S2-taahhut": "Sözleşmeyi elli bin dolara imzalayacağız ve teslimat bir Ekim'de olacak.",
    "S3-uzun": (
        "Lumos temsilcisi toplantıya katılıp konuşmaları Türkçeden İngilizceye "
        "çevirecek ve düşük güvenli cümleleri işaretleyecek."
    ),
    # Test 3'te (2026-08-14) sahada başarısız olan E-sınıfı vakalar:
    "S4-yuzde": "Ödemenin yüzde kırkı peşin, kalanı teslimatta ödenecek.",
    "S5-marka": "Hukuki sorumluluğu We Lock AI olarak biz üstleniyoruz.",
}


def synth(text: str, out_dir: Path, name: str) -> bytes:
    aiff = out_dir / f"{name}.aiff"
    wav = out_dir / f"{name}.wav"
    subprocess.run(["say", "-v", "Yelda", "-o", str(aiff), text], check=True)
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(wav)],
        check=True,
    )
    with wave.open(str(wav)) as w:
        return w.readframes(w.getnframes())


def main() -> int:
    from representative.stt import FasterWhisperSTT

    sizes = sys.argv[1:] or ["tiny", "base", "small"]
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        audio = {name: synth(text, out_dir, name) for name, text in SENTENCES.items()}
        for size in sizes:
            t0 = time.monotonic()
            stt = FasterWhisperSTT(model_size=size, language="tr")
            load_s = time.monotonic() - t0
            print(f"\n=== model={size} (yükleme {load_s:.1f}s)")
            for name, pcm in audio.items():
                stt.transcribe(pcm)  # warm-up: ilk çağrı önbellek/ısınma içerir
                t1 = time.monotonic()
                result = stt.transcribe(pcm)
                warm_s = time.monotonic() - t1
                secs = len(pcm) / 2 / 16000
                match = "AYNI" if result.text.strip() == SENTENCES[name] else "FARK"
                print(f"{name}: {warm_s:.2f}s / {secs:.1f}s ses → [{match}] {result.text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
