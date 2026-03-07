from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal

@dataclass
class Decision:
    allow: bool
    reason: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


# Result of pre_route(ctx): whether to send to AI provider or return a Lumos message.
# "tool" = read-only system tool handled; message contains the tool output.
PreRouteDestination = Literal["provider", "tool", "tool_not_implemented", "unsupported"]


@dataclass
class PreRouteResult:
    """Result of pre_route(ctx). destination='provider' -> call AIRouter; else show message."""
    destination: PreRouteDestination
    message: str = ""
