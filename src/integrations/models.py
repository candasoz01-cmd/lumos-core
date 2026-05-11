from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class IntegrationRequest:
    provider: str
    action: str
    payload: dict[str, Any]
@dataclass(frozen=True)
class IntegrationResult:
    ok: bool
    provider: str
    action: str
    data: dict[str, Any]
    error: str = ""
