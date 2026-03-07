"""
Minimal memory manager for Lumos v1: facade over session and user memory.
Session = temporary (active chat only). User = persistent local file. No background learning.
"""
from __future__ import annotations

from pathlib import Path

from lumos_core.memory.session_memory import SessionMemory
from lumos_core.memory.user_memory import (
    add_approved_preference as _add_approved_preference,
    load_approved_preferences,
)
from lumos_core.user_identity import UserIdentity, load as load_user_identity


def create_session_memory(
    max_messages: int = 10,
    max_summary_chars: int = 500,
) -> SessionMemory:
    """Create a new session memory for an active chat. Bounded window + rolling summary; not persisted."""
    return SessionMemory(max_messages=max_messages, max_summary_chars=max_summary_chars)


def load_user_profile(base_dir: str | Path | None = None) -> tuple[UserIdentity, list[dict[str, str]]]:
    """
    Load user profile: identity (name, address_mode, preferred_address) and approved preferences.
    Identity from .lumos/user_preferences.json; approved preferences from .lumos/user_memory.json.
    """
    user = load_user_identity(base_dir)
    prefs = load_approved_preferences(base_dir)
    return user, prefs


def add_approved_preference(key: str, value: str, base_dir: str | Path | None = None) -> None:
    """
    Add one user-approved preference. Call only after explicit user approval.
    Persisted to .lumos/user_memory.json.
    """
    _add_approved_preference(key, value, base_dir)


# Explicit memory-save intent: "bunu hatırla: ..." (user-approved only)
_MEMORY_SAVE_PREFIX = "bunu hatırla:"
_MAX_KEY_LEN = 32


def parse_memory_save_intent(message: str) -> str | None:
    """
    If message is an explicit memory-save intent ("bunu hatırla: ..."), return the content to store; else None.
    Used by CLI to avoid sending to the provider; content is stored via add_approved_preference only after this.
    """
    msg = (message or "").strip()
    if not msg.lower().startswith(_MEMORY_SAVE_PREFIX.lower()):
        return None
    after = msg.split(":", 1)[1].strip() if ":" in msg else ""
    return after if after else None


def preference_key_from_value(value: str) -> str:
    """
    Derive a stable key from a preference value for storage.
    Used when the user says "bunu hatırla: X" and we store key=derived, value=X.
    """
    raw = (value or "").strip()[:50].lower().replace(" ", "_")
    key = "".join(c for c in raw if c.isalnum() or c == "_")
    return key[: _MAX_KEY_LEN] if key else "pref"


def format_user_memory_for_context(user: UserIdentity, approved_preferences: list[dict[str, str]]) -> str:
    """
    Format user profile and approved preferences as a short string for system/context.
    Empty string if nothing to add. Used to inject into prompts when present.
    """
    parts: list[str] = []
    if (user.name or "").strip():
        parts.append(f"User's name: {user.name.strip()}")
    if user.address_mode and user.address_mode != "adaptive":
        parts.append(f"Address mode: {user.address_mode}")
    if (user.preferred_address or "").strip():
        parts.append(f"Preferred address: {user.preferred_address.strip()}")
    for p in approved_preferences:
        k, v = p.get("key", ""), p.get("value", "")
        if k and v:
            parts.append(f"{k}: {v}")
    if not parts:
        return ""
    return "Remembered (user-approved): " + "; ".join(parts)


def build_chat_context(
    session_memory: SessionMemory,
    user: UserIdentity,
    approved_preferences: list[dict[str, str]],
) -> dict[str, object]:
    """
    Build chat context for one turn: system prompt suffix (user memory + session summary) and recent messages.
    Returns kwargs to pass to ai_router.route(): chat_context_suffix, recent_messages.
    All chat context is assembled here so the router only appends one string.
    """
    parts: list[str] = []
    user_memory_str = format_user_memory_for_context(user, approved_preferences)
    if user_memory_str and user_memory_str.strip():
        parts.append(user_memory_str.strip())
    session_summary = (session_memory.get_session_summary() or "").strip()
    if session_summary:
        parts.append("Session context (earlier in this chat): " + session_summary)
    chat_context_suffix = "\n\n".join(parts) if parts else ""
    return {
        "chat_context_suffix": chat_context_suffix or None,
        "recent_messages": session_memory.get_recent_messages(),
    }
