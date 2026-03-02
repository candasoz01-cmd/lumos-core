set -e

# Context güncelle
cat <<'PY' > src/context/context.py
from dataclasses import dataclass

@dataclass
class Context:
    message: str = ""
    online: bool = False
    confidence: float = 1.0
    user_is_child: bool = False
    memory_note_count: int = 0
PY

# Memory güncelle
cat <<'PY' > src/memory/memory.py
from dataclasses import dataclass, field
from typing import List
from context.context import Context
from memory.schema import MemoryNote

@dataclass
class Memory:
    enabled: bool = True
    notes: List[MemoryNote] = field(default_factory=list)

    def enrich(self, ctx: Context) -> Context:
        ctx.memory_note_count = len(self.notes)
        return ctx

    def add(self, note: MemoryNote) -> None:
        if not self.enabled:
            return
        self.notes.append(note)
PY

# Main debug güncelle
cat <<'PY' > src/main.py
import os
from core.lumos import Lumos
from context.context import Context

def main():
    lumos = Lumos(mode="offline")
    lumos.boot()

    msg = input("Sen: ").strip()

    ctx = Context(
        message=msg,
        online=False,
        confidence=0.9,
        user_is_child=False
    )

    if os.getenv("DEBUG") == "1":
        ctx = lumos.memory.enrich(ctx)
        print(f"(debug) ctx.memory_note_count(before): {ctx.memory_note_count}")

    response = lumos.respond(ctx)
    if response:
        print("Lumos:", response)

    if os.getenv("DEBUG") == "1":
        print(f"(debug) memory notes(after): {len(lumos.memory.notes)}")

if __name__ == "__main__":
    main()
PY

echo "OK: Memory patch uygulandı."
echo "Test için:"
echo "  cd src && DEBUG=1 python3 main.py"
