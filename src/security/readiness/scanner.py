"""Yerel salt okunur Quantum Readiness tarayıcısı (ADR-013 Faz-2)."""
from __future__ import annotations

import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.lumos_base_dir import lumos_base_dir
from core.workspace_contract import (
    identity_file_path,
    keystore_file_path,
    notes_file_path,
)
from security.readiness.schema import (
    CRYPTO_SOURCE_ALLOWLIST,
    DISCLAIMER,
    ENTROPY_SILENT_FALLBACK_NOTE,
)

_CODE_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "src/security/crypto.py": [
        (r"AESGCM", "AES-GCM-256"),
        (r"Scrypt", "Scrypt KDF"),
    ],
    "src/security/identity.py": [
        (r"Ed25519", "Ed25519"),
        (r"aesgcm", "AES-GCM (private key at rest)"),
    ],
    "src/security/request_signer.py": [
        (r"Ed25519", "Ed25519 request signature"),
        (r"get_random_bytes", "CSPRNG nonce (entropy-backed)"),
    ],
    "src/memory/secure_store.py": [
        (r"aesgcm", "AES-GCM-256 (notes at rest)"),
    ],
    "src/security/keystore.py": [
        (r"get_random_bytes\(32\)", "256-bit random root key"),
        (r"encrypt_with_passphrase", "Scrypt + AES-GCM wrapper"),
    ],
}


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _import_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _read_text_safe(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _load_json_safe(path: Path) -> dict[str, Any] | None:
    text = _read_text_safe(path)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _scan_crypto_sources(repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    encryption: set[str] = set()
    signatures: set[str] = set()
    keys: set[str] = set()
    evidence: list[str] = []
    findings: list[dict[str, Any]] = []

    for rel in CRYPTO_SOURCE_ALLOWLIST:
        full = repo_root / rel
        text = _read_text_safe(full)
        if text is None:
            findings.append(
                {
                    "finding_id": f"SCAN-{rel.replace('/', '-')}",
                    "severity": "orta",
                    "category": "crypto",
                    "summary": f"Allowlist dosyası okunamadı: {rel}",
                    "file_path": rel,
                    "line_or_section": "",
                    "evidence_type": "code",
                    "verified": False,
                }
            )
            continue

        evidence.append(f"file:{rel}")
        for pattern, label in _CODE_PATTERNS.get(rel, []):
            if not re.search(pattern, text):
                continue
            lower = label.lower()
            if "signature" in lower or "ed25519" in lower:
                signatures.add(label)
            elif any(x in lower for x in ("random", "kdf", "scrypt", "wrapper", "nonce")):
                keys.add(label)
            else:
                encryption.add(label)

    if "AES-GCM-256" not in encryption and any("AES-GCM" in x for x in encryption):
        encryption.add("AES-GCM-256")

    inventory = {
        "encryption_types": sorted(encryption),
        "signature_types": sorted(signatures),
        "key_types": sorted(keys),
        "quantum_exposure_note": "Klasik — PQC değil",
        "evidence": evidence,
    }
    return inventory, findings


def _probe_entropy_lab() -> dict[str, Any]:
    configured = (os.environ.get("LUMOS_ENTROPY_PROVIDER") or "os").strip().lower() or "os"
    qiskit_ok = _import_available("qiskit")
    qiskit_aer_ok = _import_available("qiskit_aer")
    ibm_runtime_ok = _import_available("qiskit_ibm_runtime")

    effective = configured
    silent_fallback = False
    fallback_reason: str | None = None

    if configured == "qiskit_aer":
        if not (qiskit_ok and qiskit_aer_ok):
            effective = "os"
            silent_fallback = True
            fallback_reason = "qiskit/qiskit_aer import yok — get_provider sessiz os fallback"
    elif configured == "ibm_runtime":
        if not ibm_runtime_ok:
            effective = "os"
            silent_fallback = True
            fallback_reason = "qiskit_ibm_runtime import yok — sessiz os fallback"
    elif configured not in ("os", "qiskit_aer", "ibm_runtime"):
        effective = "os"
        silent_fallback = True
        fallback_reason = f"bilinmeyen sağlayıcı '{configured}' — os fallback"

    return {
        "label": "deneysel",
        "configured_provider": configured,
        "effective_provider_heuristic": effective,
        "qiskit_import_available": qiskit_ok,
        "qiskit_aer_import_available": qiskit_aer_ok,
        "ibm_runtime_import_available": ibm_runtime_ok,
        "silent_fallback_warning": silent_fallback,
        "silent_fallback_note": ENTROPY_SILENT_FALLBACK_NOTE if silent_fallback else None,
        "fallback_reason": fallback_reason,
        "evidence": [
            "env:LUMOS_ENTROPY_PROVIDER",
            "importlib:qiskit",
            "importlib:qiskit_aer",
            "importlib:qiskit_ibm_runtime",
        ],
    }


def _scan_lumos_metadata(base_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    long_lived: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    ks_path = keystore_file_path(base_dir)
    ks = _load_json_safe(ks_path)
    if ks is not None:
        root = ks.get("root_key") if isinstance(ks.get("root_key"), dict) else {}
        kdf = root.get("kdf", "unknown")
        long_lived.append(
            {
                "data_class": "keystore",
                "retention": "indefinite",
                "crypto_at_rest": f"AES-GCM + {kdf} KDF (metadata)",
                "harvest_now_decrypt_later_risk": "orta",
                "evidence": str(ks_path.relative_to(base_dir) if ks_path.is_relative_to(base_dir) else ks_path.name),
                "metadata_only": True,
            }
        )
    else:
        long_lived.append(
            {
                "data_class": "keystore",
                "retention": "indefinite",
                "crypto_at_rest": "AES-GCM + Scrypt (expected — file absent)",
                "harvest_now_decrypt_later_risk": "orta",
                "evidence": ".lumos/keystore.json (missing)",
                "metadata_only": True,
            }
        )

    id_path = identity_file_path(base_dir)
    ident = _load_json_safe(id_path)
    if ident is not None:
        algo = ident.get("algo", "unknown")
        pk = ident.get("private_key") if isinstance(ident.get("private_key"), dict) else {}
        cipher = pk.get("cipher", "unknown")
        long_lived.append(
            {
                "data_class": "identity",
                "retention": "indefinite",
                "crypto_at_rest": f"{algo} + {cipher} (private key metadata)",
                "harvest_now_decrypt_later_risk": "orta",
                "evidence": str(id_path.relative_to(base_dir) if id_path.is_relative_to(base_dir) else id_path.name),
                "metadata_only": True,
            }
        )

    notes_path = notes_file_path(base_dir)
    notes = _load_json_safe(notes_path)
    if notes is not None:
        cipher = notes.get("cipher", "unknown")
        long_lived.append(
            {
                "data_class": "notes",
                "retention": "indefinite",
                "crypto_at_rest": cipher,
                "harvest_now_decrypt_later_risk": "orta",
                "evidence": str(notes_path.relative_to(base_dir) if notes_path.is_relative_to(base_dir) else notes_path.name),
                "metadata_only": True,
            }
        )

    if ks is None and ident is None and notes is None:
        findings.append(
            {
                "finding_id": "LL-001",
                "severity": "dusuk",
                "category": "config",
                "summary": ".lumos çekirdek şifreli dosyalar henüz yok — statik kod envanteri geçerli",
                "file_path": str(base_dir),
                "line_or_section": "",
                "evidence_type": "config",
                "verified": True,
            }
        )

    return long_lived, findings


def _hard_to_change_deps(repo_root: Path) -> list[dict[str, Any]]:
    deps: list[dict[str, Any]] = [
        {
            "component": "crypto.py encrypt/decrypt",
            "algorithm": "AES-GCM-256",
            "change_cost": "yuksek",
            "reason": "API yüzeyi + mevcut şifreli blob formatı",
            "evidence": "file:src/security/crypto.py",
        },
        {
            "component": "crypto.py KDF",
            "algorithm": "Scrypt",
            "change_cost": "yuksek",
            "reason": "Mevcut passphrase türetilmiş anahtarlar",
            "evidence": "file:src/security/crypto.py",
        },
        {
            "component": "keystore format",
            "algorithm": "256-bit + AES wrapper",
            "change_cost": "yuksek",
            "reason": "Dağıtılmış keystore dosyaları",
            "evidence": "file:src/security/keystore.py",
        },
        {
            "component": "entropy default",
            "algorithm": "os.urandom",
            "change_cost": "dusuk",
            "reason": "Env ile değiştirilebilir; efektif kaynak probe gerekir",
            "evidence": "file:src/security/entropy/__init__.py",
        },
    ]
    crypto_path = repo_root / "src/security/crypto.py"
    text = _read_text_safe(crypto_path)
    if text and '"v"' in text and "EncryptedBlob" in text:
        deps.append(
            {
                "component": "EncryptedBlob format",
                "algorithm": "version field v=1",
                "change_cost": "orta",
                "reason": "Kısmi versiyonlama var; PQC migration hook yok",
                "evidence": "file:src/security/crypto.py",
            }
        )
    return deps


def _assess_crypto_agility(repo_root: Path) -> str:
    crypto_path = repo_root / "src/security/crypto.py"
    text = _read_text_safe(crypto_path)
    if not text:
        return "dogrulanamadi"

    has_version = "EncryptedBlob" in text and re.search(r"\bv:\s*int", text) is not None
    has_module_boundaries = all(
        (repo_root / rel).is_file() for rel in CRYPTO_SOURCE_ALLOWLIST
    )
    has_algo_config = bool(re.search(r"ALGO|algorithm.*env|getenv.*cipher", text, re.I))

    if has_algo_config and has_version:
        return "yuksek"
    if has_module_boundaries and has_version:
        return "orta"
    if has_module_boundaries:
        return "orta"
    return "dusuk"


def _post_quantum_readiness() -> dict[str, Any]:
    return {
        "pqc_status": "uygulanmiyor",
        "nist_pqc_awareness": True,
        "hybrid_ready": False,
        "hybrid_ready_note": "Migration hook tanımsız — hibrit geçiş uygun değil",
        "blockers": [
            "Format sabitliği (AES-GCM + Scrypt blob)",
            "Keystore migrasyon planı yok",
            "PQC algoritma entegrasyonu yok",
        ],
        "evidence": [
            "docs:docs/decisions/ADR-013-lumos-quantum-security-readiness.md",
            "docs:docs/analysis/lumos-quantum-readiness-checklist.md",
        ],
    }


def _evidenced_findings(
    entropy_lab: dict[str, Any],
    scan_findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = [
        {
            "finding_id": "CR-001",
            "severity": "orta",
            "category": "crypto",
            "summary": "AES-GCM-256 klasik simetrik; PQC değil",
            "file_path": "src/security/crypto.py",
            "line_or_section": "AESGCM",
            "evidence_type": "code",
            "verified": True,
        },
        {
            "finding_id": "CR-002",
            "severity": "orta",
            "category": "crypto",
            "summary": "Scrypt KDF — kuantum sonrası değiştirme planı yok",
            "file_path": "src/security/crypto.py",
            "line_or_section": "Scrypt",
            "evidence_type": "code",
            "verified": True,
        },
        {
            "finding_id": "EN-001",
            "severity": "yuksek",
            "category": "entropy",
            "summary": "Sessiz fallback: qiskit_aer/ibm_runtime → os",
            "file_path": "src/security/entropy/__init__.py",
            "line_or_section": "get_provider",
            "evidence_type": "code",
            "verified": True,
        },
        {
            "finding_id": "EN-002",
            "severity": "orta",
            "category": "entropy",
            "summary": "Qiskit Aer simülatör — donanım değil",
            "file_path": "src/security/entropy/providers/qiskit_aer.py",
            "line_or_section": "AerSimulator",
            "evidence_type": "code",
            "verified": True,
        },
    ]

    if entropy_lab.get("silent_fallback_warning"):
        findings.append(
            {
                "finding_id": "EN-003",
                "severity": "yuksek",
                "category": "entropy",
                "summary": entropy_lab.get("fallback_reason") or "Yapılandırılmış sağlayıcı kullanılamıyor — os fallback",
                "file_path": "env:LUMOS_ENTROPY_PROVIDER",
                "line_or_section": entropy_lab.get("configured_provider", ""),
                "evidence_type": "env",
                "verified": True,
            }
        )

    findings.extend(scan_findings)
    return findings


def _prioritized_migration_plan() -> list[dict[str, Any]]:
    return [
        {
            "priority": "P0",
            "action": "Sessiz entropy fallback uyarısını readiness raporunda zorunlu göster",
            "target": "Entropy Lab bölümü",
            "dependency": "Faz-2 probe",
            "effort": "S",
            "owner_hint": "security",
            "status": "oneri",
        },
        {
            "priority": "P1",
            "action": "Kripto envanter yerel tarama (CLI/panel GET)",
            "target": "crypto_inventory",
            "dependency": "Bu PR (CLI)",
            "effort": "M",
            "owner_hint": "security",
            "status": "oneri",
        },
        {
            "priority": "P1",
            "action": "Keystore / encrypted blob format versiyonlama taslağı",
            "target": "hard_to_change_deps",
            "dependency": "Ayrı ADR",
            "effort": "L",
            "owner_hint": "security",
            "status": "ertelendi",
        },
        {
            "priority": "P2",
            "action": "NIST PQC aday izleme notu güncelleme",
            "target": "post_quantum_transition_readiness",
            "dependency": None,
            "effort": "S",
            "owner_hint": "security",
            "status": "oneri",
        },
        {
            "priority": "P3",
            "action": "Hibrit PQC POC (private/onaylı)",
            "target": "PQC uygulama",
            "dependency": "P1 + audit",
            "effort": "L",
            "owner_hint": "security",
            "status": "ertelendi",
        },
    ]


def scan_quantum_readiness(
    *,
    repo_root: Path | None = None,
    lumos_dir: Path | None = None,
) -> dict[str, Any]:
    """
    ADR-013 yerel salt okunur readiness taraması.
    get_entropy() çağırmaz; .lumos dosyalarını decrypt etmez.
    """
    root = (repo_root or _default_repo_root()).resolve()
    base = (lumos_dir or lumos_base_dir()).resolve()

    crypto_inventory, source_findings = _scan_crypto_sources(root)
    long_lived_data, lumos_findings = _scan_lumos_metadata(base)
    entropy_lab = _probe_entropy_lab()
    agility = _assess_crypto_agility(root)

    return {
        "meta": {
            "report_type": "quantum_readiness",
            "scan_mode": "local",
            "read_only": True,
            "generated_at": _iso_now(),
            "evidence_basis": "local_scan",
            "disclaimer": DISCLAIMER,
            "lumos_base_dir": str(base),
        },
        "crypto_inventory": crypto_inventory,
        "long_lived_data": long_lived_data,
        "hard_to_change_deps": _hard_to_change_deps(root),
        "crypto_agility_level": agility,
        "post_quantum_transition_readiness": _post_quantum_readiness(),
        "evidenced_findings": _evidenced_findings(entropy_lab, source_findings + lumos_findings),
        "prioritized_migration_plan": _prioritized_migration_plan(),
        "entropy_lab": entropy_lab,
    }
