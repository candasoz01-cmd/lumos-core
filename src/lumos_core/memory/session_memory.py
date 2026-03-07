"""
Minimal session memory for Lumos v1: temporary in-process only.
Bounded window of 10 recent messages plus a compact rolling summary of older context.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from lumos_core.context.context import Context

_MAX_RECENT_MESSAGES = 10
_MAX_SUMMARY_CHARS = 500
_TRUNC_LEN = 50


def _trunc(s: str, max_len: int = _TRUNC_LEN) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3].rstrip() + "..."


def _append_to_rolling_summary(summary: str, lines: list[str], max_chars: int) -> str:
    new = "\n".join(lines)
    combined = (summary + "\n" + new).strip() if summary else new
    if len(combined) <= max_chars:
        return combined
    tail = combined[-max_chars:]
    idx = tail.find("\n")
    if idx >= 0:
        return tail[idx + 1 :].lstrip()
    return tail


@dataclass
class SessionMemory:
    """Temporary memory: last N messages (bounded window) + compact rolling summary of older context."""

    max_messages: int = _MAX_RECENT_MESSAGES
    max_summary_chars: int = _MAX_SUMMARY_CHARS
    _messages: list[dict[str, str]] = field(default_factory=list)
    _summary: str = ""

    def add_turn(self, user_content: str, assistant_content: str) -> None:
        """Append one user/assistant turn. Keep last max_messages; fold older into rolling summary."""
        user_content = (user_content or "").strip()
        assistant_content = (assistant_content or "").strip()
        if user_content:
            self._messages.append({"role": "user", "content": user_content})
        if assistant_content:
            self._messages.append({"role": "assistant", "content": assistant_content})
        while len(self._messages) > self.max_messages:
            dropped: list[dict[str, str]] = []
            to_remove = len(self._messages) - self.max_messages
            for _ in range(to_remove):
                if self._messages:
                    dropped.append(self._messages.pop(0))
            if dropped:
                line_parts: list[str] = []
                i = 0
                while i < len(dropped):
                    u = dropped[i].get("content", "") if dropped[i].get("role") == "user" else ""
                    a = ""
                    if i + 1 < len(dropped) and dropped[i + 1].get("role") == "assistant":
                        a = dropped[i + 1].get("content", "")
                        i += 1
                    line_parts.append(f"User: {_trunc(u)} | Assistant: {_trunc(a)}")
                    i += 1
                self._summary = _append_to_rolling_summary(
                    self._summary, line_parts, self.max_summary_chars
                )

    def get_recent_messages(self) -> list[dict[str, str]]:
        """Return the bounded window of recent messages for the provider (up to max_messages)."""
        return list(self._messages)

    def get_session_summary(self) -> str:
        """Return compact rolling summary of earlier context (empty if none)."""
        return self._summary

    def clear(self) -> None:
        """Clear session memory. Call when session ends or user requests reset."""
        self._messages.clear()
        self._summary = ""

    def enrich(self, ctx: Context) -> Context:
        """Set short_context from recent user messages for backward compatibility."""
        user_msgs = [m["content"] for m in self._messages if m.get("role") == "user"]
        ctx.short_context = " | ".join(user_msgs) if user_msgs else ""
        return ctx
