"""
AI Router for Lumos: route prompts to multiple AI providers.

Prepares the architecture for connecting to OpenAI, Gemini, Anthropic, etc.
Full API implementations can be added later; this module defines the routing contract.
"""
from __future__ import annotations

from typing import Any, Protocol

# Supported provider names; extend this set when adding new providers.
SUPPORTED_PROVIDERS = frozenset({"openai", "gemini", "anthropic"})


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
        response = router.route("Explain quantum computing", provider="openai")
    """

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._register_builtin_stubs()

    def _register_builtin_stubs(self) -> None:
        """Register stub handlers for each supported provider. Replace with real implementations later."""
        for name in SUPPORTED_PROVIDERS:
            self._providers[name] = _StubProvider(name)

    def register_provider(self, name: str, provider: AIProvider) -> None:
        """Register a provider for routing. Use this to add or override providers."""
        self._providers[name] = provider

    def route(self, prompt: str, provider: str, **kwargs: Any) -> str:
        """
        Route the prompt to the given provider and return the response.

        :param prompt: User prompt to send to the AI.
        :param provider: Provider name (e.g. 'openai', 'gemini', 'anthropic').
        :param kwargs: Optional provider-specific options (for future use).
        :return: Response text from the provider.
        :raises ValueError: If provider is not supported or not registered.
        """
        provider = provider.lower().strip()
        if provider not in self._providers:
            supported = ", ".join(sorted(self._providers))
            raise ValueError(f"Unknown provider '{provider}'. Supported: {supported}")
        return self._providers[provider].complete(prompt, **kwargs)


class _StubProvider:
    """Placeholder provider that returns a stub response until real APIs are implemented."""

    def __init__(self, name: str) -> None:
        self._name = name

    def complete(self, prompt: str, **kwargs: Any) -> str:
        return "This is where the provider response will appear."
