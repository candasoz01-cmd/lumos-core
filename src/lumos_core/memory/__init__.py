"""
Lumos memory layer (v1): session (temporary) and user (persistent, approved-only).

- session_memory: in-process only, last N turns during active chat.
- user_memory: local file (.lumos/user_memory.json), small list of user-approved preferences.
- memory_manager: facade (create_session_memory, load_user_profile, add_approved_preference).
"""

from lumos_core.memory.session_memory import SessionMemory
from lumos_core.memory.user_memory import (
    add_approved_preference,
    load_approved_preferences,
    remove_approved_preference,
    save_approved_preferences,
)
from lumos_core.memory.memory_manager import (
    build_chat_context,
    create_session_memory,
    format_user_memory_for_context,
    load_user_profile,
)

__all__ = [
    "SessionMemory",
    "load_approved_preferences",
    "save_approved_preferences",
    "add_approved_preference",
    "remove_approved_preference",
    "create_session_memory",
    "load_user_profile",
    "format_user_memory_for_context",
    "build_chat_context",
]
