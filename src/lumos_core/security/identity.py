from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from lumos_core.security.crypto import aesgcm_encrypt, aesgcm_decrypt, b64e, b64d


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@dataclass
class IdentityPaths:
    base_dir: Path

    @property
    def identity_file(self) -> Path:
        return self.base_dir / "identity.json"


class DeviceIdentity:
    """
    Local-first device identity:
    - Ed25519 keypair
    - private key: root_key ile AES-GCM şifreli
    - public key: plaintext (kimlik)
    - lumos_id: sha256(public_key_bytes)
    """
    def __init__(self, base_dir: str = "src/.lumos"):
        self.paths = IdentityPaths(Path(base_dir))
        self.paths.base_dir.mkdir(parents=True, exist_ok=True)

    def is_initialized(self) -> bool:
        return self.paths.identity_file.exists()

    def init(self, root_key: bytes) -> None:
        if self.is_initialized():
            return

        priv = Ed25519PrivateKey.generate()
        pub = priv.public_key()

        pub_bytes = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        priv_bytes = priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )

        aad = b"lumos-identity-v1"
        nonce, ct = aesgcm_encrypt(root_key, priv_bytes, aad=aad)

        data = {
            "v": 1,
            "algo": "ed25519",
            "lumos_id": sha256_hex(pub_bytes),
            "public_key_b64": b64e(pub_bytes),
            "private_key": {
                "v": 1,
                "cipher": "aesgcm",
                "aad": "lumos-identity-v1",
                "nonce_b64": b64e(nonce),
                "ct_b64": b64e(ct),
            }
        }
        self.paths.identity_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, root_key: bytes) -> dict:
        if not self.is_initialized():
            raise RuntimeError("Identity init edilmemiş. scripts/init_identity.py çalıştır.")
        data = json.loads(self.paths.identity_file.read_text(encoding="utf-8"))

        pub = b64d(data["public_key_b64"])
        pk = data["private_key"]
        nonce = b64d(pk["nonce_b64"])
        ct = b64d(pk["ct_b64"])

        aad = b"lumos-identity-v1"
        priv_bytes = aesgcm_decrypt(root_key, nonce, ct, aad=aad)

        # doğrulama: lumos_id tutarlı mı?
        expected = sha256_hex(pub)
        if data.get("lumos_id") != expected:
            raise RuntimeError("Identity bozuk: lumos_id mismatch")

        return {
            "v": data.get("v", 1),
            "algo": data.get("algo", "ed25519"),
            "lumos_id": data["lumos_id"],
            "public_key_bytes": pub,
            "private_key_bytes": priv_bytes,
        }
