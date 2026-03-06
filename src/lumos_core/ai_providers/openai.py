"""OpenAI provider for Lumos AI router. Uses OPENAI_API_KEY from environment."""
from __future__ import annotations

import os
from typing import Any

from lumos_core.ai_providers.base import BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    """Real OpenAI API provider. Requires OPENAI_API_KEY in the environment."""

    name = "OpenAI"
    is_stub = False

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini") -> None:
        self._api_key = (api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
        self._model = model

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Send prompt to OpenAI chat completions and return the response text."""
        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Set it in your environment to use the OpenAI provider."
            )
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=kwargs.get("model", self._model),
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        return content if content is not None else ""
