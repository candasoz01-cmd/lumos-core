#!/bin/zsh
set -e

cd "$(dirname "$0")"

echo "== Lumos bootstrap starting =="
echo "PWD: $(pwd)"

# 1) Ensure package folders exist
mkdir -p src/engine src/policy src/core

# 2) Ensure __init__.py for packages
touch src/engine/__init__.py
touch src/policy/__init__.py
touch src/core/__init__.py

# 3) engine/base.py
cat <<'PY' > src/engine/base.py
class BaseEngine:
    def process(self, message: str) -> dict:
        raise NotImplementedError
PY

# 4) core/version.py
cat <<'PY' > src/core/version.py
VERSION = "0.1.0"
PY

# 5) engine/model_client.py
cat <<'PY' > src/engine/model_client.py
import os

class ModelClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("LUMOS_API_KEY")

    def generate(self, prompt: str) -> str:
        # Şimdilik gerçek model yok. Online stub metni.
        return "Yanındayım."
PY

# 6) engine/online_engine.py
cat <<'PY' > src/engine/online_engine.py
from engine.base import BaseEngine
from engine.model_client import ModelClient

class OnlineEngineV1(BaseEngine):

    def __init__(self):
        self.client = ModelClient()

    def process(self, message: str) -> dict:
        prompt = self._build_prompt(message)
        raw = self.client.generate(prompt)
        safe = self._apply_character_filters(raw)

        return {
            "response": safe,
            "reason": "İstersen birlikte sadeleştirebiliriz.",
            "follow_up": "Buradaki asıl mesele sence ne?"
        }

    def _build_prompt(self, message: str) -> str:
        # Bu metin modele gider, kullanıcıya gösterilmez.
        return f"Kullanıcı mesajı: {message}"

    def _apply_character_filters(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            t = "Yanındayım."
        max_len = 200
        if len(t) > max_len:
            t = t[:max_len].rstrip() + "…"
        return t
PY

# 7) policy/offline_engine.py
cat <<'PY' > src/policy/offline_engine.py
from engine.base import BaseEngine

class OfflineEngineV1(BaseEngine):

    def process(self, message: str) -> dict:
        msg = (message or "").strip()

        # Boş / çok kısa mesaj
        if not msg or len(msg) <= 2:
            return {
                "response": "Yanındayım.",
                "reason": "İstersen birlikte sadeleştirebiliriz.",
                "follow_up": "Buradaki asıl mesele sence ne?"
            }

        reflected = msg if len(msg) <= 120 else msg[:120].rstrip() + "…"

        return {
            "response": f"Şunu duyuyorum: '{reflected}'",
            "reason": "İstersen birlikte sadeleştirebiliriz.",
            "follow_up": "Buradaki asıl mesele sence ne?"
        }
PY

# 8) core/lumos.py
cat <<'PY' > src/core/lumos.py
import os
from dataclasses import dataclass, field
from typing import Optional
from context.context import Context
from policy.rules import PolicyRules
from memory.memory import Memory
from engine.base import BaseEngine
from policy.offline_engine import OfflineEngineV1
from core.version import VERSION

@dataclass
class Lumos:
    mode: str = "offline"
    confidence_threshold: float = 0.70
    memory: Memory = field(default_factory=Memory)
    engine: BaseEngine = field(default_factory=OfflineEngineV1)

    def boot(self) -> None:
        print("Lumos core başlatılıyor...")
        print(f"Versiyon: {VERSION}")
        print(f"Mod: {self.mode} (varsayılan)")
        print("Durum: güvenli")
        print("Hazır.")

    def respond(self, ctx: Context) -> Optional[str]:
        ctx = self.memory.enrich(ctx)

        decision = PolicyRules.evaluate(
            ctx=ctx,
            mode=self.mode,
            confidence_threshold=self.confidence_threshold,
            engine=self.engine
        )

        if not decision.allow:
            return None

        debug = os.getenv("LUMOS_DEBUG", "0") == "1"

        if decision.payload:
            r = decision.payload.get("response", "")
            reason = decision.payload.get("reason", "")
            follow = decision.payload.get("follow_up", "")
            tech = decision.payload.get("debug", "")

            parts = [p for p in [r, reason, follow] if p]
            if debug and tech:
                parts.append(tech)

            return " | ".join(parts)

        if ctx.user_is_child:
            return "Lumos burada. (Çocuk modu)"

        return "Lumos burada."
PY

echo "== Bootstrap write complete =="

# 9) Quick import checks (kökten PYTHONPATH ile)
echo "== Import checks =="
PYTHONPATH=src python3 -c "from engine.model_client import ModelClient; print(ModelClient().generate('x'))"
PYTHONPATH=src python3 -c "from engine.online_engine import OnlineEngineV1; print(OnlineEngineV1().process('selam'))"
PYTHONPATH=src python3 -c "from policy.offline_engine import OfflineEngineV1; print(OfflineEngineV1().process('selam'))"

echo "== Running tests (if present) =="
if [ -f scripts/test.sh ]; then
  ./scripts/test.sh
else
  echo "scripts/test.sh not found, skipping."
fi

echo "== ALL OK =="
