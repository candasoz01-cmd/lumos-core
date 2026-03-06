"""
Provider protocol and optional base class for Lumos AI providers.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AIProvider(Protocol):
    """Protocol for an AI provider. Implement complete(); is_available and get_display_name are optional."""

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Send prompt to the provider and return the response text."""
        ...

    @property
    def is_available(self) -> bool:
        """True if the provider can be used (e.g. API key set). Default True."""
        return True

    def get_display_name(self) -> str:
        """Human-readable name for CLI/UI. Default: class name."""
        return getattr(self, "name", self.__class__.__name__)


class BaseAIProvider:
    """Optional base: default is_available and get_display_name for stub vs real providers."""

    name: str = ""
    is_stub: bool = False

    @property
    def is_available(self) -> bool:
        return not self.is_stub

    def get_display_name(self) -> str:
        return self.name or self.__class__.__name__
