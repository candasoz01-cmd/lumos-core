"""Secret manager: encrypt/decrypt roundtrip."""

import tempfile

from lumos_social.security.secrets import (
    decrypt,
    encrypt,
    ensure_secret_manager,
)


def test_encrypt_decrypt_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as d:
        ensure_secret_manager(d)
        data = b"secret payload"
        blob = encrypt(data)
        assert blob.version == 1
        assert len(blob.nonce) == 12
        assert len(blob.ciphertext) > len(data)
        out = decrypt(blob)
        assert out == data


def test_secret_blob_fields() -> None:
    with tempfile.TemporaryDirectory() as d:
        ensure_secret_manager(d)
        blob = encrypt(b"x")
        assert blob.version == 1 and len(blob.nonce) == 12 and len(blob.ciphertext) >= 1
