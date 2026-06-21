"""ADR-013 Quantum Readiness rapor sabitleri ve allowlist."""
from __future__ import annotations

DISCLAIMER = (
    "Hazırlık raporu — kuantum güvenli veya kuantum bilgisayar iddiası taşımaz"
)

CRYPTO_SOURCE_ALLOWLIST: tuple[str, ...] = (
    "src/security/crypto.py",
    "src/security/identity.py",
    "src/security/request_signer.py",
    "src/memory/secure_store.py",
    "src/security/keystore.py",
)

ENTROPY_SILENT_FALLBACK_NOTE = (
    "LUMOS_ENTROPY_PROVIDER qiskit_aer veya ibm_runtime olsa bile, sağlayıcı "
    "kullanılamazsa sistem uyarı vermeden os.urandom kullanabilir. Entropy Lab "
    "deneyseldir; kuantum entropy veya kuantum güvenli kullanım anlamına gelmez."
)
