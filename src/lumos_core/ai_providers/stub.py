"""Stub provider for unconfigured or missing AI backends."""
from __future__ import annotations

from typing import Any

from lumos_core.ai_providers.base import BaseAIProvider


class StubProvider(BaseAIProvider):
    """Placeholder provider until a real API is configured (e.g. API key set)."""

    is_stub = True

    def __init__(self, name: str) -> None:
        self.name = name

    def complete(self, prompt: str, **kwargs: Any) -> str:
        return "This is where the provider response will appear."
