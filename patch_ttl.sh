set -e

# Schema: created_at ekle
cat <<'PY' > src/memory/schema.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class MemoryNote:
    kind: str
    content: str
    source: str = "local"
    ttl_seconds: Optional[int] = None
    created_at: Optional[float] = None  # epoch time (time.time())
PY

# Memory: cleanup + add created_at
cat <<'PY' > src/memory/memory.py
from dataclasses import dataclass, field
from typing import List
import time

from context.context import Context
from memory.schema import MemoryNote

@dataclass
class Memory:
    enabled: bool = True
    notes: List[MemoryNote] = field(default_factory=list)

    def cleanup(self) -> None:
        # TTL dolanları RAM'den çıkar
        now = time.time()
        kept: List[MemoryNote] = []
        for n in self.notes:
            if n.ttl_seconds is None:
                kept.append(n)
                continue
            if n.created_at is None:
                # Eski notlara güvenli varsayım: şimdi başlat
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
PY

echo "OK: TTL patch uygulandı."
echo "Test için:"
echo "  cd src && DEBUG=1 python3 main.py"
echo "İstersen TTL testini ben söyleyeceğim bir komutla yaparız."
