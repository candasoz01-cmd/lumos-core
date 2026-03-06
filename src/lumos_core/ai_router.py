"""
AI Router for Lumos: route prompts to multiple AI providers.

Prepares the architecture for connecting to OpenAI, Gemini, Anthropic, etc.
Real providers are registered when configured (e.g. OPENAI_API_KEY); others use stubs.
"""
from __future__ import annotations

import os
from typing import Any, Protocol

# Supported provider names; extend this set when adding new providers.
SUPPORTED_PROVIDERS = frozenset({"openai", "gemini", "anthropic"})


class RouteResult:
    """Result of a routed request: response text and whether it came from a stub provider."""

    __slots__ = ("text", "is_stub")

    def __init__(self, text: str, is_stub: bool) -> None:
        self.text = text
        self.is_stub = is_stub


class AIProvider(Protocol):
    """Protocol for a single AI provider. Implement this to add a new provider."""

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Send prompt to the provider and return the response text."""
        ...


class AIRouter:
    """
    Routes prompts to the appropriate AI provider.

    Usage:
        router = AIRouter()
        result = router.route("Explain quantum computing", provider="openai")
    """

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._register_builtin_stubs()
        self._register_real_providers()

    def _register_builtin_stubs(self) -> None:
        """Register stub handlers for each supported provider. Replaced by real ones when configured."""
        for name in SUPPORTED_PROVIDERS:
            self._providers[name] = _StubProvider(name)

    def _register_real_providers(self) -> None:
        """Register real providers when their config (e.g. API key) is present."""
        if os.environ.get("OPENAI_API_KEY", "").strip():
            from lumos_core.ai_providers.openai import OpenAIProvider
            self._providers["openai"] = OpenAIProvider()

    def register_provider(self, name: str, provider: AIProvider) -> None:
        """Register a provider for routing. Use this to add or override providers."""
        self._providers[name] = provider

    def route(self, prompt: str, provider: str, **kwargs: Any) -> RouteResult:
        """
        Route the prompt to the given provider and return the response.

        :param prompt: User prompt to send to the AI.
        :param provider: Provider name (e.g. 'openai', 'gemini', 'anthropic').
        :param kwargs: Optional provider-specific options (for future use).
        :return: RouteResult with response text and is_stub flag.
        :raises ValueError: If provider is not supported or not registered, or key missing (e.g. openai).
        """
        provider = provider.lower().strip()
        if provider not in self._providers:
            supported = ", ".join(sorted(self._providers))
            raise ValueError(f"Unknown provider '{provider}'. Supported: {supported}")
        impl = self._providers[provider]
        if provider == "openai" and getattr(impl, "is_stub", True):
            raise ValueError(
                "OPENAI_API_KEY is not set. Set it in your environment to use the OpenAI provider."
            )
        text = impl.complete(prompt, **kwargs)
        is_stub = getattr(impl, "is_stub", True)
        return RouteResult(text=text, is_stub=is_stub)


class _StubProvider:
    """Placeholder provider that returns a stub response until real APIs are implemented."""

    is_stub = True

    def __init__(self, name: str) -> None:
        self._name = name

    def complete(self, prompt: str, **kwargs: Any) -> str:
        return "This is where the provider response will appear."
