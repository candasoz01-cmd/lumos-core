import os
import json
from pathlib import Path

from engine.model_client import ModelClient
from security.keystore import FileKeyStore
from security.identity import DeviceIdentity
from security.request_signer import RequestSigner
from memory.secure_store import SecureNotesStore


def _base_dir() -> str:
    if Path("src/.lumos").exists():
        return "src/.lumos"
    if Path(".lumos").exists():
        return ".lumos"
    return "src/.lumos"


class OnlineEngineV1:
    def __init__(self):
        self.client = ModelClient()
        self.base_dir = _base_dir()
        self.identity = DeviceIdentity(base_dir=self.base_dir)
        self.signer = None
        self.lumos_id = ""

        passphrase = (os.getenv("LUMOS_PASSPHRASE", "") or "").strip()
        if not passphrase:
            return

        try:
            ks = FileKeyStore(base_dir=self.base_dir)
            root_key = ks.load_root_key(passphrase)

            store = SecureNotesStore(base_dir=self.base_dir)
            store.load(root_key)

            ident = self.identity.load(root_key)
            self.lumos_id = ident["lumos_id"]
            self.signer = RequestSigner(
                lumos_id=self.lumos_id,
                private_key_bytes=ident["private_key_bytes"],
                public_key_bytes=ident["public_key_bytes"]
            )
        except Exception:
            self.signer = None
            self.lumos_id = ""

    def process(self, message: str, short_context: str = "") -> dict:
        if not self.signer:
            return {
                "response": "Online hazır değil.",
                "reason": "Kimlik/şifre yok (dev için LUMOS_PASSPHRASE gerekli).",
                "follow_up": ""
            }

        payload = {
            "short_context": short_context,
            "message": message
        }

        signed = self.signer.sign(payload)
        wire = json.dumps(signed.__dict__, ensure_ascii=False)

        raw = self.client.generate(wire)

        safe_raw = (raw or "").strip() or "Yanıt yok."
        try:
            parsed = json.loads(safe_raw)
            safe = parsed.get("response") or safe_raw
        except Exception:
            safe = safe_raw
        if len(safe) > 200:
            safe = safe[:200].rstrip() + "…"

        return {
            "response": safe,
            "reason": "",
            "follow_up": "",
            "debug": f"ONLINE_SIGNED id={self.lumos_id[:8]}"
        }
