from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Tuple, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from security.entropy import get_random_bytes


def b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8")


def b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def derive_key_scrypt(passphrase: str, salt: bytes, length: int = 32) -> bytes:
    if not isinstance(passphrase, str) or not passphrase:
        raise ValueError("passphrase boş olamaz")
    kdf = Scrypt(
        salt=salt,
        length=length,
        n=2**14,
        r=8,
        p=1,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def aesgcm_encrypt(key: bytes, plaintext: bytes, aad: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    if len(key) != 32:
        raise ValueError("AESGCM key 32 byte olmalı")
    nonce = get_random_bytes(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, aad)
    return nonce, ct


def aesgcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: Optional[bytes] = None) -> bytes:
    if len(key) != 32:
        raise ValueError("AESGCM key 32 byte olmalı")
    return AESGCM(key).decrypt(nonce, ciphertext, aad)


@dataclass
class EncryptedBlob:
    kdf: str
    salt_b64: str
    nonce_b64: str
    ct_b64: str
    v: int = 1

    def to_dict(self) -> dict:
        return {
            "v": self.v,
            "kdf": self.kdf,
            "salt_b64": self.salt_b64,
            "nonce_b64": self.nonce_b64,
            "ct_b64": self.ct_b64,
        }

    @staticmethod
    def from_dict(d: dict) -> "EncryptedBlob":
        return EncryptedBlob(
            v=int(d.get("v", 1)),
            kdf=str(d.get("kdf", "scrypt")),
            salt_b64=str(d["salt_b64"]),
            nonce_b64=str(d["nonce_b64"]),
            ct_b64=str(d["ct_b64"]),
        )


def encrypt_with_passphrase(passphrase: str, plaintext: bytes, aad: Optional[bytes] = None) -> EncryptedBlob:
    salt = get_random_bytes(16)
    key = derive_key_scrypt(passphrase, salt)
    nonce, ct = aesgcm_encrypt(key, plaintext, aad=aad)
    return EncryptedBlob(
        kdf="scrypt",
        salt_b64=b64e(salt),
        nonce_b64=b64e(nonce),
        ct_b64=b64e(ct),
    )


def decrypt_with_passphrase(passphrase: str, blob: EncryptedBlob, aad: Optional[bytes] = None) -> bytes:
    if blob.kdf != "scrypt":
        raise ValueError(f"Desteklenmeyen KDF: {blob.kdf}")
    salt = b64d(blob.salt_b64)
    nonce = b64d(blob.nonce_b64)
    ct = b64d(blob.ct_b64)
    key = derive_key_scrypt(passphrase, salt)
    return aesgcm_decrypt(key, nonce, ct, aad=aad)
