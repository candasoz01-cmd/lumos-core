from dataclasses import dataclass, field
from typing import List
from lumos_core.context.context import Context

@dataclass
class SessionMemory:
    max_items: int = 3
    history: List[str] = field(default_factory=list)

    def enrich(self, ctx: Context) -> Context:
        msg = (getattr(ctx, "message", "") or "").strip()
        if msg:
            self.history.append(msg)
            self.history = self.history[-self.max_items:]
        ctx.short_context = " | ".join(self.history)
        return ctx

    def clear(self) -> None:
        self.history.clear()
