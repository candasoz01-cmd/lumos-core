"""Tests for Lumos system prompt module."""
from __future__ import annotations

from lumos_core.system_prompt import get_system_prompt


class TestGetSystemPrompt:
    """Verify get_system_prompt behavior."""

    def test_without_user_name_returns_base_prompt(self) -> None:
        """When user_name is None or empty, return base Lumos personality only."""
        out = get_system_prompt(None)
        assert "You are Lumos." in out
        assert "transparent and honest" in out
        assert "explicit user approval" in out
        assert "explain reasoning" in out
        assert "user control and safety" in out
        assert "address the user naturally" in out
        assert "user's name" not in out

    def test_empty_string_no_name_line(self) -> None:
        """Empty string user_name is treated as no name."""
        out = get_system_prompt("")
        assert "You are Lumos." in out
        assert "user's name is" not in out

    def test_whitespace_only_no_name_line(self) -> None:
        """Whitespace-only user_name is treated as no name."""
        out = get_system_prompt("   ")
        assert "You are Lumos." in out
        assert "user's name is" not in out

    def test_with_user_name_includes_name(self) -> None:
        """When user_name is set, prompt includes it for addressing the user."""
        out = get_system_prompt("Alice")
        assert "You are Lumos." in out
        assert "user's name is Alice" in out or "Alice" in out

    def test_user_name_stripped(self) -> None:
        """user_name is stripped before inclusion."""
        out = get_system_prompt("  Bob  ")
        assert "Bob" in out
        assert "  Bob  " not in out
