"""Tests for the minimal v1 memory layer: session (temporary) and user (persistent, approved-only)."""
from __future__ import annotations

import tempfile
from unittest.mock import patch

from lumos_core.context.context import Context
from lumos_core.memory.session_memory import SessionMemory
from lumos_core.memory.user_memory import (
    add_approved_preference,
    load_approved_preferences,
    remove_approved_preference,
    save_approved_preferences,
)
from lumos_core.memory.memory_manager import (
    add_approved_preference as add_approved_preference_mm,
    apply_memory_save,
    build_chat_context,
    create_session_memory,
    format_user_memory_for_context,
    is_ask_my_name_intent,
    parse_memory_save_intent,
    parse_name_from_content,
    preference_key_from_value,
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

    def test_format_user_memory_for_context_skips_name_like_preferences(self) -> None:
        """Name is canonical in user_preferences only; name-like entries in user_memory are not output."""
        user = UserIdentity(name="Alex", address_mode="adaptive")
        prefs = [
            {"key": "lang", "value": "Python"},
            {"key": "adm_can", "value": "Adım Can"},
        ]
        out = format_user_memory_for_context(user, prefs)
        assert "Alex" in out
        assert "Python" in out
        assert "Adım Can" not in out and "adm_can" not in out

    def test_format_user_memory_for_context_name_only_from_user_preferences(self) -> None:
        """Name is never read from user_memory; only user_preferences.name is used for 'Adım ne?' context."""
        user = UserIdentity(name="", address_mode="adaptive")  # no name in user_preferences
        prefs = [{"key": "adm_can", "value": "Adım Can"}]  # name-like in user_memory
        out = format_user_memory_for_context(user, prefs)
        assert "Can" not in out and "Adım Can" not in out
        assert "adm_can" not in out

    def test_build_chat_context_includes_recent_messages_from_session(self) -> None:
        """Chat session memory: build_chat_context passes recent_messages to router."""
        user = UserIdentity()
        session = create_session_memory(max_messages=10)
        session.add_turn("What is 2+2?", "4.")
        ctx = build_chat_context(user, [], session_memory=session)
        assert "recent_messages" in ctx
        recent = ctx["recent_messages"]
        assert len(recent) == 2
        assert recent[0]["role"] == "user" and recent[0]["content"] == "What is 2+2?"
        assert recent[1]["role"] == "assistant" and recent[1]["content"] == "4."
        ctx_no_session = build_chat_context(user, [], session_memory=None)
        assert ctx_no_session["recent_messages"] == []

    def test_run_chat_passes_session_memory_to_router(self) -> None:
        """Chat CLI uses session memory: second provider call receives recent_messages from first turn."""
        from lumos_core.ai_router import AIRouter
        from lumos_core.ai_providers.base import BaseAIProvider
        from lumos_core.cli import run_chat

        class _CaptureAllProvider(BaseAIProvider):
            name = "CaptureAll"
            is_stub = True

            def __init__(self) -> None:
                self.all_kwargs: list[dict] = []

            def complete(self, prompt: str, **kwargs: object) -> str:
                self.all_kwargs.append(dict(kwargs))
                return "assistant reply"

        router = AIRouter()
        cap = _CaptureAllProvider()
        router.register_provider("openai", cap)
        inputs = ["first user message", "second user message", "exit"]
        with patch("lumos_core.cli.input", side_effect=inputs):
            with patch("lumos_core.memory.memory_manager.load_user_profile", return_value=(UserIdentity(), [])):
                run_chat(provider="openai", router=router)
        assert len(cap.all_kwargs) >= 2
        first_call = cap.all_kwargs[0]
        second_call = cap.all_kwargs[1]
        assert first_call.get("recent_messages") == []
        recent = second_call.get("recent_messages") or []
        assert len(recent) == 2
        assert recent[0]["role"] == "user" and recent[0]["content"] == "first user message"
        assert recent[1]["role"] == "assistant" and recent[1]["content"] == "assistant reply"


class TestMemorySaveIntent:
    """Explicit memory-save only: 'bunu hatırla...' -> name to user_preferences.name, else to user_memory. No auto-save."""

    def test_parse_memory_save_intent_detects_prefix(self) -> None:
        assert parse_memory_save_intent("bunu hatırla: Ben Türkçe konuşurum") == "Ben Türkçe konuşurum"
        assert parse_memory_save_intent("bunu hatırla: Adım Can") == "Adım Can"
        assert parse_memory_save_intent("bunu hatırla: Kahveyi sade severim") == "Kahveyi sade severim"
        assert parse_memory_save_intent("  bunu hatırla: x  ") == "x"

    def test_parse_memory_save_intent_variations(self) -> None:
        """Space before colon, or no colon: still detected as explicit memory-save."""
        assert parse_memory_save_intent("bunu hatırla : Ben Türkçe konuşurum") == "Ben Türkçe konuşurum"
        assert parse_memory_save_intent("bunu hatırla  :  x") == "x"
        assert parse_memory_save_intent("bunu hatırla Kahveyi sade severim") == "Kahveyi sade severim"
        assert parse_memory_save_intent("  bunu hatırla  something  ") == "something"

    def test_parse_memory_save_intent_robust_variations(self) -> None:
        """Extra spaces between words, around colon; case-insensitive; no false positives."""
        assert parse_memory_save_intent("bunu  hatırla  foo") == "foo"
        assert parse_memory_save_intent("bunu   hatırla   :   bar") == "bar"
        assert parse_memory_save_intent("BUNU HATIRLA: uppercase") == "uppercase"
        assert parse_memory_save_intent("Bunu Hatırla : mixed") == "mixed"
        assert parse_memory_save_intent("bunu hatırla\ntwo lines") == "two lines"
        # No content after prefix -> None
        assert parse_memory_save_intent("bunu hatırla") is None
        assert parse_memory_save_intent("bunu hatırla:") is None
        assert parse_memory_save_intent("bunu hatırla :") is None
        assert parse_memory_save_intent("bunu hatırla   :   ") is None
        # Unrelated text not detected
        assert parse_memory_save_intent("lütfen bunu hatırla: x") is None
        assert parse_memory_save_intent("bunu hatırlamak istiyorum") is None

    def test_parse_memory_save_intent_returns_none_for_other_messages(self) -> None:
        assert parse_memory_save_intent("hello") is None
        assert parse_memory_save_intent("bunu hatırla") is None  # no content after prefix
        assert parse_memory_save_intent("bunu hatırla:") is None  # empty content
        assert parse_memory_save_intent("bunu hatırla :") is None  # only space and colon
        assert parse_memory_save_intent("") is None

    def test_parse_memory_save_intent_new_variations(self) -> None:
        """Space before/after colon, no colon, tabs, trailing spaces only -> robust detection."""
        assert parse_memory_save_intent("bunu hatırla : Ben Türkçe konuşurum") == "Ben Türkçe konuşurum"
        assert parse_memory_save_intent("bunu hatırla  ... my preference") == "... my preference"
        assert parse_memory_save_intent("bunu hatırla\t: x") == "x"
        assert parse_memory_save_intent("bunu hatırla\nnewline content") == "newline content"
        assert parse_memory_save_intent("  bunu hatırla  something  ") == "something"
        # No content after prefix (trailing spaces only) -> None
        assert parse_memory_save_intent("bunu hatırla  ") is None
        assert parse_memory_save_intent("bunu hatırla   :   ") is None

    def test_parse_memory_save_intent_requested_variations(self) -> None:
        """Explicit variations: 'bunu hatırla : ...' and 'bunu hatırla ...' (with or without colon)."""
        # Space before colon
        assert parse_memory_save_intent("bunu hatırla : kahveyi sade severim") == "kahveyi sade severim"
        assert parse_memory_save_intent("bunu hatırla  :  tercih") == "tercih"
        # No colon: content immediately after optional spaces
        assert parse_memory_save_intent("bunu hatırla Adım Can") == "Adım Can"
        assert parse_memory_save_intent("bunu hatırla  ben Türkçe konuşurum") == "ben Türkçe konuşurum"
        # Combined: leading space on message, space before colon
        assert parse_memory_save_intent("  bunu hatırla : x  ") == "x"

    def test_parse_memory_save_intent_none_and_empty(self) -> None:
        """Empty string returns None; no crash."""
        assert parse_memory_save_intent("") is None

    def test_preference_key_from_value(self) -> None:
        assert preference_key_from_value("Ben Türkçe konuşurum")  # non-empty key
        assert preference_key_from_value("Adım Can")
        key = preference_key_from_value("Kahveyi sade severim")
        assert key == "kahveyi_sade_severim" or "kahveyi" in key

    def test_parse_name_from_content(self) -> None:
        assert parse_name_from_content("Adım Can") == "Can"
        assert parse_name_from_content("Adım  Can") == "Can"
        assert parse_name_from_content("Benim adım Can") == "Can"
        assert parse_name_from_content("BENIM ADIM Ali") == "Ali"
        assert parse_name_from_content("Kahveyi sade severim") is None
        assert parse_name_from_content("adım ne?") is None  # ask-intent, not set-name
        assert parse_name_from_content("adim ne?") is None
        assert parse_name_from_content("") is None

    def test_is_ask_my_name_intent(self) -> None:
        """'Adım ne?' / 'adım ne' -> True; answer must come from user_preferences.name only."""
        assert is_ask_my_name_intent("Adım ne?") is True
        assert is_ask_my_name_intent("adım ne") is True
        assert is_ask_my_name_intent("  Adım ne  ?  ") is True
        assert is_ask_my_name_intent("Adım ne") is True
        assert is_ask_my_name_intent("Adım Can") is False
        assert is_ask_my_name_intent("adım ne değil") is False
        assert is_ask_my_name_intent("adim ne?") is True  # ASCII i (e.g. from shell)
        assert is_ask_my_name_intent("") is False

    def test_apply_memory_save_name_writes_user_preferences(self) -> None:
        """'Adım X' / 'Benim adım X' -> user_preferences.name only, not user_memory."""
        from lumos_core.user_identity import load as load_user_identity
        with tempfile.TemporaryDirectory() as tmp:
            assert apply_memory_save("Adım Can", base_dir=tmp) == "name"
            user = load_user_identity(base_dir=tmp)
            assert user.name == "Can"
            assert apply_memory_save("Benim adım Ali", base_dir=tmp) == "name"
            user = load_user_identity(base_dir=tmp)
            assert user.name == "Ali"
            prefs = load_approved_preferences(base_dir=tmp)
            assert not any(p.get("value", "").startswith("Adım") or "adım" in (p.get("value") or "").lower() for p in prefs)

    def test_apply_memory_save_preference_writes_user_memory(self) -> None:
        """Non-name content -> user_memory as before."""
        with tempfile.TemporaryDirectory() as tmp:
            assert apply_memory_save("Kahveyi sade severim", base_dir=tmp) == "preference"
            prefs = load_approved_preferences(base_dir=tmp)
            assert len(prefs) == 1
            assert "Kahveyi" in prefs[0]["value"]

    def test_memory_save_roundtrip(self) -> None:
        """Parse intent -> derive key -> add_approved_preference -> load: preference is stored."""
        with tempfile.TemporaryDirectory() as tmp:
            content = "Ben Türkçe konuşurum"
            key = preference_key_from_value(content)
            add_approved_preference_mm(key, content, base_dir=tmp)
            prefs = load_approved_preferences(base_dir=tmp)
            assert len(prefs) == 1
            assert prefs[0]["key"] == key
            assert prefs[0]["value"] == content

    def test_run_ask_adim_ne_returns_name_from_user_preferences(self) -> None:
        """'Adım ne?' is answered only from user_preferences.name; no user_memory read for name."""
        from io import StringIO
        from lumos_core.cli import run_ask
        user_with_name = UserIdentity(name="Can", address_mode="adaptive")
        user_no_name = UserIdentity(name="", address_mode="adaptive")
        with patch("lumos_core.user_identity.load", return_value=user_with_name):
            out = StringIO()
            with patch("sys.stdout", out):
                run_ask("Adım ne?")
            assert "Adın Can" in out.getvalue()
        with patch("lumos_core.user_identity.load", return_value=user_no_name):
            out = StringIO()
            with patch("sys.stdout", out):
                run_ask("Adım ne?")
            assert "İsmin kayıtlı değil" in out.getvalue()
