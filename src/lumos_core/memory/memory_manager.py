"""
Minimal memory manager for Lumos v1: facade over session and user memory.
Session = temporary (active chat only). User = persistent local file. No background learning.
"""
from __future__ import annotations

import re
from pathlib import Path

from lumos_core.memory.session_memory import SessionMemory
from lumos_core.memory.user_memory import (
    add_approved_preference as _add_approved_preference,
    load_approved_preferences,
)
from lumos_core.user_identity import UserIdentity, load as load_user_identity, save as save_user_identity


def _is_name_like_value(value: str) -> bool:
    """True if value looks like a stored name phrase (Adım X / Benim adım X). Used to skip outputting name from user_memory."""
    v = (value or "").strip().lower()
    return v.startswith("adım ") or v.startswith("benim adım ")


def parse_name_from_content(content: str) -> str | None:
    """
    If content is a name phrase ("Adım X" or "Benim adım X"), return the name part; else None.
    Canonical name storage is user_preferences.name; this supports routing memory-save to it.
    Supports both Turkish (ı) and ASCII (i) spellings for prefix matching (e.g. "BENIM ADIM X").
    """
    c = (content or "").strip()
    if not c:
        return None
    low = c.lower().replace("\u0131", "i")  # dotless ı -> i for prefix match
    if low.startswith("adim "):
        name = c[5:].strip()
        return name if name else None
    if low.startswith("benim adim "):
        name = c[11:].strip()
        return name if name else None
    return None


def is_ask_my_name_intent(message: str) -> bool:
    """True if message is asking for the user's name (e.g. 'Adım ne?'). Answer from user_preferences.name only."""
    m = (message or "").strip().lower().rstrip("?").strip()
    return m == "adım ne"


def apply_memory_save(content: str, base_dir: str | Path | None = None) -> str:
    """
    Apply explicit memory-save content: if name phrase ("Adım X" / "Benim adım X")
    -> user_preferences.name only; else -> user_memory. Returns "name" or "preference".
    """
    name = parse_name_from_content(content)
    if name:
        # Name phrase -> user_preferences.name only; do not write name to user_memory.
        user = load_user_identity(base_dir)
        user.name = name
        save_user_identity(user, base_dir)
        return "name"
    key = preference_key_from_value(content)
    _add_approved_preference(key, content, base_dir)
    return "preference"


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


# Explicit memory-save intent: "bunu hatırla" at start + optional colon/spaces + content (user-approved only).
# No automatic saving; CLI stores only when this returns non-empty content.
#
# Detection logic:
# 1. Normalize: strip leading/trailing whitespace from the message.
# 2. Prefix: literal "bunu" + one-or-more whitespace + "hatırla" with word boundary (\b) so we do not match
#    "bunu hatırlamak" or "bunu hatırlayalım". Then optional whitespace, then optional colon (with optional
#    surrounding whitespace), then optional trailing whitespace. So we match: "bunu hatırla: x", "bunu hatırla : x",
#    "bunu hatırla x", "bunu  hatırla  :  x", "bunu hatırla\nx", "bunu hatırla\t: x", etc.
# 3. Content: everything after the matched prefix, stripped. If content is empty or only whitespace, return None.
# 4. Must match at start (after strip); "lütfen bunu hatırla" does not match (phrase not at start).
_MEMORY_SAVE_PREFIX = re.compile(
    r"bunu\s+hatırla\b\s*(?::\s*)?\s*",
    re.IGNORECASE | re.DOTALL,
)
_MAX_KEY_LEN = 32


def parse_memory_save_intent(message: str) -> str | None:
    """
    If message is an explicit memory-save intent ("bunu hatırla ..." at start), return the content to store; else None.
    Supports: "bunu hatırla: x", "bunu hatırla : x", "bunu hatırla x", "bunu  hatırla  something", tabs/newlines.
    Requires the exact phrase at start (after strip); no content or only whitespace after prefix returns None.
    Only explicit user phrasing triggers this; no automatic memory saving.
    """
    if not message:
        return None
    msg = message.strip()
    if not msg:
        return None
    m = _MEMORY_SAVE_PREFIX.match(msg)
    if not m:
        return None
    content = msg[m.end() :].strip()
    return content if content else None


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
    Name is read only from user (user_preferences.name). user_memory (approved_preferences)
    is never used for name; name-like entries are excluded so "Adım ne?" is answered only from user_preferences.
    """
    parts: list[str] = []
    # Name only from user_preferences; never from user_memory (approved_preferences).
    if (user.name or "").strip():
        parts.append(f"User's name: {user.name.strip()}")
    if user.address_mode and user.address_mode != "adaptive":
        parts.append(f"Address mode: {user.address_mode}")
    if (user.preferred_address or "").strip():
        parts.append(f"Preferred address: {user.preferred_address.strip()}")
    # user_memory is not used for name; exclude name-like entries from context.
    prefs_for_context = [p for p in approved_preferences if not _is_name_like_value(p.get("value", ""))]
    for p in prefs_for_context:
        k, v = p.get("key", ""), p.get("value", "")
        if k and v:
            parts.append(f"{k}: {v}")
    if not parts:
        return ""
    return "Remembered (user-approved): " + "; ".join(parts)


def build_chat_context(
    user: UserIdentity,
    approved_preferences: list[dict[str, str]],
    session_memory: SessionMemory | None = None,
) -> dict[str, object]:
    """
    Build chat context for one turn. Single entry point: all context is assembled here and
    passed to the router as chat_context=... so chat context is wired only through the memory manager.

    - For ask (no session): pass session_memory=None → suffix = user memory only, recent_messages = [].
    - For chat: pass session_memory → suffix = user memory + session summary, recent_messages from session.

    Returns dict to pass as chat_context= to ai_router.route(): chat_context_suffix, recent_messages.
    """
    parts: list[str] = []
    user_memory_str = format_user_memory_for_context(user, approved_preferences)
    if user_memory_str and user_memory_str.strip():
        parts.append(user_memory_str.strip())
    if session_memory is not None:
        session_summary = (session_memory.get_session_summary() or "").strip()
        if session_summary:
            parts.append("Session context (earlier in this chat): " + session_summary)
    chat_context_suffix = "\n\n".join(parts) if parts else ""
    recent_messages = (
        session_memory.get_recent_messages() if session_memory is not None else []
    )
    return {
        "chat_context_suffix": chat_context_suffix or None,
        "recent_messages": recent_messages,
    }
