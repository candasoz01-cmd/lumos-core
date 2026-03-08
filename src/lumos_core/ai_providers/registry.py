"""
Provider registry: register providers by name; router uses only this module.
Optional providers (Gemini, Anthropic) can register when installed/configured.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from lumos_core.ai_providers.base import AIProvider

ProviderFactory = Callable[[], "AIProvider"]

_registry: dict[str, ProviderFactory] = {}
_BUILTINS_LOADED = False

SUPPORTED_PROVIDER_NAMES = frozenset({"openai", "gemini", "anthropic"})


def register(name: str, factory: ProviderFactory) -> None:
    """Register a provider by name. Overwrites existing."""
    _registry[name.lower().strip()] = factory


def unregister(name: str) -> None:
    """Remove a provider by name."""
    _registry.pop(name.lower().strip(), None)


def get_provider(name: str) -> "AIProvider" | None:
    """Return an instance for the given provider name, or None if unknown."""
    factory = _registry.get(name.lower().strip())
    if factory is None:
        return None
    return factory()


def list_providers() -> list[str]:
    """Return sorted list of registered provider names."""
    return sorted(_registry)


def list_available() -> list[str]:
    """Return provider names that are registered and currently available (e.g. API key set)."""
    return [n for n in list_providers() if get_provider(n) and get_provider(n).is_available]


def _register_builtins() -> None:
    """Register stubs for all supported names; replace with real providers when configured."""
    from lumos_core.ai_providers.stub import StubProvider

    for n in SUPPORTED_PROVIDER_NAMES:
        register(n, lambda _n=n: StubProvider(_n))

    if os.environ.get("OPENAI_API_KEY", "").strip():
        try:
            import openai  # noqa: F401 - ensure package installed before using real provider
            from lumos_core.ai_providers.openai import OpenAIProvider
            register("openai", lambda: OpenAIProvider())
        except ImportError:
            pass  # Keep stub when openai package is not installed

    # Optional: register Gemini/Anthropic when present (try/import or optional package)
    # try:
    #     from lumos_core.ai_providers.anthropic import AnthropicProvider
    #     register("anthropic", AnthropicProvider)
    # except ImportError:
    #     pass
    # try:
    #     from lumos_core.ai_providers.gemini import GeminiProvider
    #     register("gemini", GeminiProvider)
    # except ImportError:
    #     pass


def ensure_builtins() -> None:
    """Ensure default providers (stubs + any configured real ones) are registered. Idempotent."""
    global _BUILTINS_LOADED
    if not _BUILTINS_LOADED:
        _register_builtins()
        _BUILTINS_LOADED = True
