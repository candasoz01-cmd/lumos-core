from dataclasses import dataclass
from typing import Optional


@dataclass
class MemoryNote:
    kind: str
    content: str
    source: str = "local"
    ttl_seconds: Optional[int] = None
    created_at: Optional[float] = None
