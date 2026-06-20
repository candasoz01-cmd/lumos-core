"""Tam mod ses-only gönderim — panel.astro bilgilendirici yanıt wiring."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"


def test_panel_full_audio_reply_on_send_path() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    block = text.split("if (hasAudio && !outgoingMessage && !hasPhoto)", 1)[1].split("return;", 1)[0]
    assert 'panelT("panel.modules.chat.compose.hints.fullAudioReply")' in block
    assert 'setSendHint(panelT("panel.modules.chat.compose.hints.fullAudioHint"))' in block


def test_panel_full_audio_reply_on_attach_path() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    attach_block = text.split('appendUserComposeBubble("Ses dosyası eklendi"', 1)[1].split(
        "input.blur();", 1
    )[0]
    assert 'panelT("panel.modules.chat.compose.hints.fullAudioReply")' in attach_block
    assert 'setSendHint(panelT("panel.modules.chat.compose.hints.fullAudioHint"))' in attach_block
