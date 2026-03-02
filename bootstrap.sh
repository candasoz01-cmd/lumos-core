set -e

mkdir -p src/context src/core src/policy src/memory

cat <<'PY' > src/context/__init__.py
PY

cat <<'PY' > src/context/context.py
from dataclasses import dataclass

@dataclass
class Context:
    message: str = ""
    online: bool = False
    confidence: float = 1.0
    user_is_child: bool = False
PY

cat <<'PY' > src/memory/__init__.py
PY

cat <<'PY' > src/memory/schema.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class MemoryNote:
    kind: str                 # "preference", "constraint", "summary", "safety_flag"
    content: str              # saklanacak metin (şimdilik RAM)
    source: str = "local"     # local / cloud / user
    ttl_seconds: Optional[int] = None
PY

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
        return ctx

    def add(self, note: MemoryNote) -> None:
        if not self.enabled:
            return
        self.notes.append(note)
PY

cat <<'PY' > src/policy/__init__.py
PY

cat <<'PY' > src/policy/offline_engine.py
class OfflineEngineV1:
    def process(self, message: str) -> dict:
        msg = (message or "").strip()

        if not msg:
            return {
                "response": "Yanındayım.",
                "reason": "İstersen birlikte sadeleştirebiliriz.",
                "follow_up": ""
            }

        reflected = msg if len(msg) <= 120 else msg[:120] + "..."

        return {
            "response": f"Şunu duyuyorum: '{reflected}'",
            "reason": "İstersen bunu birlikte sadeleştirebiliriz.",
            "follow_up": "Buradaki asıl mesele sence ne?"
        }
PY

cat <<'PY' > src/policy/rules.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
from context.context import Context
from policy.offline_engine import OfflineEngineV1

@dataclass
class Decision:
    allow: bool
    reason: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

class PolicyRules:
    """
    Lumos davranış politikaları.
    - Offline ise offline engine çalışır
    - Emin değilse sus
    - Çocuk kullanıcıya güvenli mod
    """

    @staticmethod
    def evaluate(ctx: Context, mode: str, confidence_threshold: float) -> Decision:
        # Emin değilse konuşma
        if ctx.confidence < confidence_threshold:
            return Decision(False, "Emin değil")

        # Çocuk kullanıcı koruması
        if ctx.user_is_child:
            return Decision(True, "Çocuk modu", payload=None)

        # Offline mod: offline engine ile cevap üret
        if mode == "offline" or not ctx.online:
            engine = OfflineEngineV1()
            payload = engine.process(getattr(ctx, "message", ""))
            return Decision(True, "Offline mod: offline engine", payload=payload)

        # Online mod (şimdilik yok)
        return Decision(False, "Online mod henüz yok")
PY

cat <<'PY' > src/core/__init__.py
PY

cat <<'PY' > src/core/lumos.py
from dataclasses import dataclass, field
from typing import Optional
from context.context import Context
from policy.rules import PolicyRules
from memory.memory import Memory
from memory.schema import MemoryNote

@dataclass
class Lumos:
    mode: str = "offline"
    confidence_threshold: float = 0.70
    memory: Memory = field(default_factory=Memory)

    def boot(self) -> None:
        print("Lumos core başlatılıyor...")
        print(f"Mod: {self.mode} (varsayılan)")
        print("Durum: güvenli")
        print("Hazır.")

    def respond(self, ctx: Context) -> Optional[str]:
        ctx = self.memory.enrich(ctx)

        decision = PolicyRules.evaluate(
            ctx=ctx,
            mode=self.mode,
            confidence_threshold=self.confidence_threshold
        )

        if not decision.allow:
            return None

        if decision.payload:
            r = decision.payload.get("response", "")
            reason = decision.payload.get("reason", "")
            follow = decision.payload.get("follow_up", "")

            if getattr(ctx, "message", ""):
                note = MemoryNote(kind="summary", content=f"User said: {ctx.message[:80]}")
                self.memory.add(note)

            parts = [p for p in [r, reason, follow] if p]
            return " | ".join(parts)

        if ctx.user_is_child:
            return "Lumos burada. (Çocuk modu)"

        return "Lumos burada."
PY

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

    response = lumos.respond(ctx)
    if response:
        print("Lumos:", response)

    if os.getenv("DEBUG") == "1":
        print(f"(debug) memory notes: {len(lumos.memory.notes)}")

if __name__ == "__main__":
    main()
PY

echo "OK: Dosyalar yazıldı."
echo "Test:"
echo "  cd src && DEBUG=1 python3 main.py"
