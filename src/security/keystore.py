from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from security.crypto import encrypt_with_passphrase, decrypt_with_passphrase, EncryptedBlob
from security.entropy import get_random_bytes


@dataclass
class KeyStorePaths:
    base_dir: Path

    @property
    def keystore_file(self) -> Path:
        return self.base_dir / "keystore.json"


class FileKeyStore:
    """
    Platform bağımsız kök anahtar (root key) saklama:
    - Diskte plaintext yok
    - passphrase ile türetilmiş anahtarla AES-GCM şifreli
    """
    def __init__(self, base_dir: str = ".lumos"):
        self.paths = KeyStorePaths(Path(base_dir))
        self.paths.base_dir.mkdir(parents=True, exist_ok=True)

    def is_initialized(self) -> bool:
        return self.paths.keystore_file.exists()

    def init(self, passphrase: str) -> None:
        if self.is_initialized():
            return
        root_key = get_random_bytes(32)  # 256-bit
        aad = b"lumos-keystore-v1"
        blob = encrypt_with_passphrase(passphrase, root_key, aad=aad)
        data = {"v": 1, "root_key": blob.to_dict()}
        self.paths.keystore_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_root_key(self, passphrase: str) -> bytes:
        if not self.is_initialized():
            raise RuntimeError("Keystore init edilmemiş. python -m src.scripts.init_keystore çalıştır.")
        data = json.loads(self.paths.keystore_file.read_text(encoding="utf-8"))
        blob = EncryptedBlob.from_dict(data["root_key"])
        aad = b"lumos-keystore-v1"
        return decrypt_with_passphrase(passphrase, blob, aad=aad)
