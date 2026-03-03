"""Secret manager: master key, AES-GCM, encrypt/decrypt. DB'ye plaintext yazılmaz."""

import os
import secrets as std_secrets
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_VERSION = 1
_KEY_SIZE = 32
_NONCE_SIZE = 12
_MASTER_KEY_FILENAME = ".master_key"


@dataclass
class SecretBlob:
    """Encrypted payload: version, nonce, ciphertext, tag (tag is last 16 bytes of ciphertext in GCM)."""

    version: int
    nonce: bytes
    ciphertext: bytes  # includes 16-byte GCM tag at end


def _keychain_path(base_dir: str | Path) -> Path:
    p = Path(base_dir)
    if str(p.name) == ".lumos":
        return p / _MASTER_KEY_FILENAME
    return p / ".lumos" / _MASTER_KEY_FILENAME


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass


def _load_or_create_master_key(base_dir: str | Path) -> bytes:
    path = _keychain_path(base_dir)
    _ensure_dir(path)
    if path.exists():
        raw = path.read_bytes()
        if len(raw) == _KEY_SIZE:
            return raw
    key = std_secrets.token_bytes(_KEY_SIZE)
    try:
        path.write_bytes(key)
        os.chmod(path, 0o600)
    except OSError:
        raise RuntimeError("Master key could not be written to keychain path")
    return key


_master_key: bytes | None = None
_base_dir: Path | None = None


def ensure_secret_manager(base_dir: str | Path) -> None:
    """İlk çalışmada master key üretir veya lokal keychain'den okur."""
    global _master_key, _base_dir
    _base_dir = Path(base_dir)
    _master_key = _load_or_create_master_key(_base_dir)


def _get_master_key() -> bytes:
    if _master_key is None:
        ensure_secret_manager(Path.cwd() / ".lumos")
    if _master_key is None:
        raise RuntimeError("Secret manager not initialized")
    return _master_key


def encrypt(data: bytes) -> SecretBlob:
    """AES-GCM ile şifrele. nonce saklanır."""
    key = _get_master_key()
    nonce = std_secrets.token_bytes(_NONCE_SIZE)
    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, data, None)
    return SecretBlob(version=_VERSION, nonce=nonce, ciphertext=ciphertext)


def decrypt(blob: SecretBlob) -> bytes:
    """SecretBlob'dan düz metni çıkar."""
    if blob.version != _VERSION:
        raise ValueError(f"Unsupported secret version {blob.version}")
    key = _get_master_key()
    aes = AESGCM(key)
    return aes.decrypt(blob.nonce, blob.ciphertext, None)
