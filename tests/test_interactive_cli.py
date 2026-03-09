"""Kando v0 interactive CLI guardrail tests: help surface and unknown command message."""
from __future__ import annotations

from pathlib import Path

from lumos_core.interactive_cli import (
    HELP_TEXT,
    UNKNOWN_CMD_MSG,
    normalize_command,
)

# Resmî komut yüzeyi (RELEASE_CHECKLIST_KANDO_V0 / SMOKE_KANDO_V0 ile uyumlu).
OFFICIAL_COMMAND_LINE = "Kando v0 resmî komutlar: kilit | kamera | alias | durum | help | exit"


class TestKandoV0InteractiveCliGuardrails:
    """Guardrails: help çıktısı resmî yüzeyle uyumlu, bilinmeyen komut net mesaj."""

    def test_help_text_matches_official_command_surface(self) -> None:
        """Interactive CLI help çıktısı resmî komut yüzeyiyle uyumlu olmalı."""
        assert OFFICIAL_COMMAND_LINE in HELP_TEXT, (
            "HELP_TEXT must contain the official command surface so help output stays in sync."
        )
        assert "kilit" in HELP_TEXT and "kamera" in HELP_TEXT and "alias" in HELP_TEXT
        assert "durum" in HELP_TEXT and "help" in HELP_TEXT and "exit" in HELP_TEXT

    def test_unknown_command_normalized_as_unknown(self) -> None:
        """Bilinmeyen komut normalize_command ile 'unknown' dönmeli (Adım ne, xyz, vb.)."""
        base = Path(".")
        aliases: dict = {}
        assert normalize_command("xyz", base, aliases) == ("unknown", [])
        assert normalize_command("Adım ne", base, aliases) == ("unknown", [])
        assert normalize_command("rastgele girdi", base, aliases) == ("unknown", [])

    def test_unknown_command_message_is_unsupported_help(self) -> None:
        """Bilinmeyen komut net biçimde 'Desteklenmeyen komut. help yazın.' döndürmeli."""
        assert UNKNOWN_CMD_MSG == "Desteklenmeyen komut. help yazın."
