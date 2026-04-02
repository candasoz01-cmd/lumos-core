from dataclasses import dataclass, field
import time
from typing import List

from context.context import Context
from memory.schema import MemoryNote
# manages memory state


@dataclass
class Memory:
    enabled: bool = True
    notes: List[MemoryNote] = field(default_factory=list)

    def cleanup(self) -> None:
        now = time.time()
        kept: List[MemoryNote] = []
        for n in self.notes:
            if n.ttl_seconds is None:
                kept.append(n)
                continue
            if n.created_at is None:
                n.created_at = now
                kept.append(n)
                continue
            if (now - n.created_at) <= n.ttl_seconds:
                kept.append(n)
        self.notes = kept

    def enrich(self, ctx: Context) -> Context:
        self.cleanup()
        ctx.memory_note_count = len(self.notes)
        return ctx

    def add(self, note: MemoryNote) -> None:
        if not self.enabled:
            return
        if note.created_at is None:
            note.created_at = time.time()
        self.notes.append(note)


# agent auto comment