"""AI provider implementations for Lumos. Extensible for OpenAI, Gemini, Anthropic, etc."""
from __future__ import annotations

from lumos_core.ai_providers.base import AIProvider, BaseAIProvider
from lumos_core.ai_providers.openai import OpenAIProvider
from lumos_core.ai_providers.registry import (
    ensure_builtins,
    get_provider,
    list_available,
    list_providers,
    register,
)
from lumos_core.ai_providers.stub import StubProvider

__all__ = [
    "AIProvider",
    "BaseAIProvider",
    "OpenAIProvider",
    "StubProvider",
    "ensure_builtins",
    "get_provider",
    "list_available",
    "list_providers",
    "register",
]
