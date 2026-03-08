"""Tests for AI router: routing and chat context (recent_messages) passed to provider."""
from __future__ import annotations

from typing import Any

from lumos_core.ai_router import AIRouter, RouteResult
from lumos_core.ai_providers.base import BaseAIProvider


class _CaptureProvider(BaseAIProvider):
    """Provider that records kwargs passed to complete() for testing session memory wiring."""
    name = "Capture"
    is_stub = True

    def __init__(self) -> None:
        self.last_kwargs: dict[str, Any] = {}

    def complete(self, prompt: str, **kwargs: Any) -> str:
        self.last_kwargs = dict(kwargs)
        return "ok"


class TestAIRouterChatContext:
    """Router passes chat_context.recent_messages to the provider."""

    def test_route_passes_recent_messages_to_provider(self) -> None:
        """When chat_context contains recent_messages, provider.complete() receives them."""
        router = AIRouter()
        cap = _CaptureProvider()
        router.register_provider("openai", cap)
        chat_context = {
            "chat_context_suffix": "User's name: Test",
            "recent_messages": [
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "4."},
            ],
        }
        result = router.route("What is 3+3?", provider="openai", chat_context=chat_context)
        assert isinstance(result, RouteResult)
        assert result.text == "ok"
        assert cap.last_kwargs.get("recent_messages") == [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4."},
        ]

    def test_route_with_empty_recent_messages(self) -> None:
        """When chat_context has empty recent_messages, provider receives empty list."""
        router = AIRouter()
        cap = _CaptureProvider()
        router.register_provider("openai", cap)
        chat_context = {"chat_context_suffix": None, "recent_messages": []}
        router.route("Hello", provider="openai", chat_context=chat_context)
        assert cap.last_kwargs.get("recent_messages") == []
