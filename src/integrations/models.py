from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class IntegrationRequest:
    provider: str
    action: str
    payload: dict[str, Any]
    region: str = ""
    language: str = ""
    risk_level: str = "normal"
    requires_approval: bool = False
@dataclass(frozen=True)
class IntegrationResult:
    ok: bool
    provider: str
    action: str
    data: dict[str, Any]
    error: str = ""
