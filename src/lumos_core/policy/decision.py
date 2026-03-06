from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal

@dataclass
class Decision:
    allow: bool
    reason: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


# Result of pre_route(ctx): whether to send to AI provider or return a Lumos message.
PreRouteDestination = Literal["provider", "tool_not_implemented", "unsupported"]


@dataclass
class PreRouteResult:
    """Result of pre_route(ctx). destination='provider' -> call AIRouter; else show message."""
    destination: PreRouteDestination
    message: str = ""
