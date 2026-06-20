"""Tam mod ses-only gönderim — panel.astro bilgilendirici yanıt wiring."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"

PANEL_FULL_AUDIO_REPLY = (
    "Tam modda ses kaydı yalnızca bu cihazda görünür; dış köprüye iletilmez."
)
PANEL_FULL_AUDIO_HINT = (
    "Tam modda ses kaydı dış köprüye iletilmez; metin ekleyin veya «Ses metne çevir» kullanın."
)


def test_panel_full_audio_reply_constants_present() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    assert PANEL_FULL_AUDIO_REPLY in text
    assert PANEL_FULL_AUDIO_HINT in text


def test_panel_full_audio_reply_on_send_path() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    block = text.split("if (hasAudio && !outgoingMessage && !hasPhoto)", 1)[1].split("return;", 1)[0]
    assert 'appendBubble("lumos", PANEL_FULL_AUDIO_REPLY)' in block
    assert "setSendHint(PANEL_FULL_AUDIO_HINT)" in block


def test_panel_full_audio_reply_on_attach_path() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    attach_block = text.split('appendUserComposeBubble("Ses dosyası eklendi"', 1)[1].split(
        "input.blur();", 1
    )[0]
    assert 'appendBubble("lumos", PANEL_FULL_AUDIO_REPLY)' in attach_block
