"""Tests for the minimal v1 memory layer: session (temporary) and user (persistent, approved-only)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lumos_core.context.context import Context
from lumos_core.memory.session_memory import SessionMemory
from lumos_core.memory.user_memory import (
    add_approved_preference,
    load_approved_preferences,
    remove_approved_preference,
    save_approved_preferences,
)
from lumos_core.memory.memory_manager import (
    create_session_memory,
    format_user_memory_for_context,
    load_user_profile,
)
from lumos_core.user_identity import UserIdentity


class TestSessionMemory:
    """Session memory is temporary: 10-message window + rolling summary."""

    def test_add_turn_and_get_recent_messages(self) -> None:
        session = SessionMemory(max_messages=10)
        assert session.get_recent_messages() == []
        session.add_turn("Hello", "Hi there.")
        assert len(session.get_recent_messages()) == 2
        session.add_turn("What is 2+2?", "4.")
        assert len(session.get_recent_messages()) == 4
        msgs = session.get_recent_messages()
        assert msgs[0]["role"] == "user" and msgs[0]["content"] == "Hello"
        assert msgs[1]["role"] == "assistant" and msgs[1]["content"] == "Hi there."

    def test_bounded_window_10_messages(self) -> None:
        session = SessionMemory(max_messages=10)
        for i in range(8):
            session.add_turn(f"q{i}", f"A{i}")
        recent = session.get_recent_messages()
        assert len(recent) == 10  # window never exceeds 10
        # Oldest kept are from later turns (q4..q7 or similar)
        assert recent[0]["role"] in ("user", "assistant")
        assert recent[-1]["content"] == "A7"

    def test_rolling_summary_when_window_exceeded(self) -> None:
        session = SessionMemory(max_messages=6, max_summary_chars=300)
        session.add_turn("First question", "First answer")
        session.add_turn("Second question", "Second answer")
        session.add_turn("Third question", "Third answer")
        session.add_turn("Fourth question", "Fourth answer")  # 8 messages -> trim to 6, 2 go to summary
        assert session.get_session_summary() != ""
        assert "First" in session.get_session_summary() or "User:" in session.get_session_summary()
        assert len(session.get_recent_messages()) == 6

    def test_clear(self) -> None:
        session = SessionMemory(max_messages=10)
        session.add_turn("x", "y")
        session.clear()
        assert session.get_recent_messages() == []
        assert session.get_session_summary() == ""

    def test_enrich_sets_short_context(self) -> None:
        session = SessionMemory(max_messages=10)
        session.add_turn("first", "resp1")
        session.add_turn("second", "resp2")
        ctx = Context(message="third")
        session.enrich(ctx)
        assert "first" in ctx.short_context and "second" in ctx.short_context


class TestUserMemory:
    """User memory is persistent; only approved preferences. Local file only."""

    def test_load_empty_when_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prefs = load_approved_preferences(base_dir=tmp)
            assert prefs == []

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            save_approved_preferences([{"key": "lang", "value": "Python"}], base_dir=tmp)
            prefs = load_approved_preferences(base_dir=tmp)
            assert len(prefs) == 1
            assert prefs[0]["key"] == "lang" and prefs[0]["value"] == "Python"

    def test_add_approved_preference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            add_approved_preference("theme", "dark", base_dir=tmp)
            prefs = load_approved_preferences(base_dir=tmp)
            assert len(prefs) == 1
            assert prefs[0]["key"] == "theme" and prefs[0]["value"] == "dark"
            add_approved_preference("theme", "light", base_dir=tmp)
            prefs = load_approved_preferences(base_dir=tmp)
            assert len(prefs) == 1
            assert prefs[0]["value"] == "light"

    def test_remove_approved_preference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            add_approved_preference("a", "1", base_dir=tmp)
            add_approved_preference("b", "2", base_dir=tmp)
            remove_approved_preference("a", base_dir=tmp)
            prefs = load_approved_preferences(base_dir=tmp)
            assert len(prefs) == 1 and prefs[0]["key"] == "b"


class TestMemoryManager:
    """Facade: session + user profile (identity + approved prefs)."""

    def test_create_session_memory(self) -> None:
        session = create_session_memory(max_messages=10)
        assert isinstance(session, SessionMemory)
        assert session.max_messages == 10

    def test_format_user_memory_for_context_empty(self) -> None:
        user = UserIdentity()
        out = format_user_memory_for_context(user, [])
        assert out == ""

    def test_format_user_memory_for_context_with_name_and_prefs(self) -> None:
        user = UserIdentity(name="Alex", address_mode="adaptive")
        prefs = [{"key": "lang", "value": "Python"}]
        out = format_user_memory_for_context(user, prefs)
        assert "Alex" in out
        assert "lang" in out and "Python" in out
        assert "Remembered (user-approved)" in out
