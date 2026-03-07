"""
AI Router for Lumos: route prompts to multiple AI providers.

Uses the provider registry (ai_providers.registry) so providers can be
registered dynamically. Real providers are registered when configured
(e.g. OPENAI_API_KEY); others use stubs.
"""
from __future__ import annotations

from typing import Any

from lumos_core.ai_providers.base import AIProvider
from lumos_core.ai_providers.registry import ensure_builtins, get_provider, list_providers
from lumos_core.system_prompt import get_system_prompt


class RouteResult:
    """Result of a routed request: response text and whether it came from a stub provider."""

    __slots__ = ("text", "is_stub")

    def __init__(self, text: str, is_stub: bool) -> None:
        self.text = text
        self.is_stub = is_stub


class AIRouter:
    """
    Routes prompts to the appropriate AI provider via the registry.

    Usage:
        router = AIRouter()
        result = router.route("Explain quantum computing", provider="openai")
    """

    def __init__(self) -> None:
        ensure_builtins()

    def register_provider(self, name: str, provider: AIProvider) -> None:
        """Register a provider for routing. Use this to add or override providers in tests or plugins."""
        from lumos_core.ai_providers.registry import register
        register(name, lambda: provider)

    def route(self, prompt: str, provider: str, **kwargs: Any) -> RouteResult:
        """
        Route the prompt to the given provider and return the response.

        Chat context (user memory, session summary, recent messages) must be passed only via
        chat_context=..., built by memory_manager.build_chat_context(). All context is wired
        through the memory manager; raw user_memory_context/session_summary/recent_messages
        are ignored.

        :param prompt: User prompt to send to the AI.
        :param provider: Provider name (e.g. 'openai', 'gemini', 'anthropic').
        :param kwargs: user_name, chat_context (from build_chat_context), and optional provider options.
        :return: RouteResult with response text and is_stub flag.
        :raises ValueError: If provider is not supported or not available (e.g. API key missing).
        """
        key = provider.lower().strip()
        impl = get_provider(key)
        if impl is None:
            supported = ", ".join(list_providers())
            raise ValueError(f"Unknown provider '{provider}'. Supported: {supported}")
        # Allow stub providers to return placeholder response; require real config for non-stub (e.g. openai).
        if not getattr(impl, "is_stub", False) and not impl.is_available:
            raise ValueError(
                f"Provider '{provider}' is not available (e.g. API key not set)."
            )
        user_name = kwargs.pop("user_name", None)
        # Chat context only via memory_manager.build_chat_context()
        kwargs.pop("user_memory_context", None)
        kwargs.pop("session_summary", None)
        kwargs.pop("recent_messages", None)
        chat_context = kwargs.pop("chat_context", None)
        if isinstance(chat_context, dict):
            chat_context_suffix = chat_context.get("chat_context_suffix")
            kwargs["recent_messages"] = chat_context.get("recent_messages", [])
        else:
            chat_context_suffix = None
            kwargs.setdefault("recent_messages", [])
        lumos_system_prompt = get_system_prompt(user_name)
        if chat_context_suffix and (chat_context_suffix := (chat_context_suffix or "").strip()):
            lumos_system_prompt = lumos_system_prompt + "\n\n" + chat_context_suffix
        text = impl.complete(prompt, system_prompt=lumos_system_prompt, **kwargs)
        is_stub = getattr(impl, "is_stub", True)
        return RouteResult(text=text, is_stub=is_stub)
