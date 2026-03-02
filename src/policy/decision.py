from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Decision:
    allow: bool
    reason: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
