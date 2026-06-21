"""Quantum Readiness Faz-2 scanner tests (ADR-013)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from security.readiness.scanner import scan_quantum_readiness

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHONPATH = f"{REPO_ROOT / 'src'}:{REPO_ROOT / 'packages' / 'kando_runtime' / 'src'}:{REPO_ROOT / 'packages' / 'kando_bridge' / 'src'}"


def _run_cli(env: dict | None = None) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.quantum_readiness_scan"],
        cwd=str(REPO_ROOT),
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), **(env or {})},
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_scan_has_adr013_seven_fields_and_meta():
    report = scan_quantum_readiness(repo_root=REPO_ROOT)

    assert report["meta"]["report_type"] == "quantum_readiness"
    assert report["meta"]["read_only"] is True
    assert report["meta"]["evidence_basis"] == "local_scan"
    assert "disclaimer" in report["meta"]

    for key in (
        "crypto_inventory",
        "long_lived_data",
        "hard_to_change_deps",
        "crypto_agility_level",
        "post_quantum_transition_readiness",
        "evidenced_findings",
        "prioritized_migration_plan",
    ):
        assert key in report

    assert "entropy_lab" in report


def test_crypto_inventory_from_allowlist():
    report = scan_quantum_readiness(repo_root=REPO_ROOT)
    inv = report["crypto_inventory"]

    assert "AES-GCM-256" in inv["encryption_types"] or any("AES-GCM" in x for x in inv["encryption_types"])
    assert inv["quantum_exposure_note"] == "Klasik — PQC değil"
    assert any("crypto.py" in e for e in inv["evidence"])


def test_crypto_agility_level_is_orta_for_lumos():
    report = scan_quantum_readiness(repo_root=REPO_ROOT)
    assert report["crypto_agility_level"] == "orta"


def test_entropy_silent_fallback_when_qiskit_missing(monkeypatch):
    monkeypatch.setenv("LUMOS_ENTROPY_PROVIDER", "qiskit_aer")
    report = scan_quantum_readiness(repo_root=REPO_ROOT)

    lab = report["entropy_lab"]
    assert lab["configured_provider"] == "qiskit_aer"
    if not lab["qiskit_import_available"] or not lab["qiskit_aer_import_available"]:
        assert lab["effective_provider_heuristic"] == "os"
        assert lab["silent_fallback_warning"] is True
        assert lab["silent_fallback_note"]


def test_lumos_metadata_only_no_decrypt(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))

    keystore = {
        "v": 1,
        "root_key": {
            "v": 1,
            "kdf": "scrypt",
            "salt_b64": "c2FsdA==",
            "nonce_b64": "bm9uY2U=",
            "ct_b64": "Y3Q=",
        },
    }
    identity = {
        "v": 1,
        "algo": "ed25519",
        "lumos_id": "abc",
        "public_key_b64": "cHVi",
        "private_key": {"v": 1, "cipher": "aesgcm", "nonce_b64": "bg==", "ct_b64": "Y3Q="},
    }
    notes = {"v": 1, "cipher": "aesgcm", "nonce_b64": "bg==", "ct_b64": "Y3Q="}

    (tmp_path / "keystore.json").write_text(json.dumps(keystore), encoding="utf-8")
    (tmp_path / "identity.json").write_text(json.dumps(identity), encoding="utf-8")
    (tmp_path / "notes.enc.json").write_text(json.dumps(notes), encoding="utf-8")

    report = scan_quantum_readiness(repo_root=REPO_ROOT, lumos_dir=tmp_path)
    classes = {row["data_class"] for row in report["long_lived_data"]}

    assert "keystore" in classes
    assert "identity" in classes
    assert "notes" in classes
    assert all(row.get("metadata_only") for row in report["long_lived_data"])


def test_pqc_status_not_implemented():
    report = scan_quantum_readiness(repo_root=REPO_ROOT)
    pqc = report["post_quantum_transition_readiness"]
    assert pqc["pqc_status"] == "uygulanmiyor"
    assert pqc["nist_pqc_awareness"] is True


def test_migration_plan_is_read_only_suggestions():
    report = scan_quantum_readiness(repo_root=REPO_ROOT)
    plan = report["prioritized_migration_plan"]
    assert len(plan) >= 3
    assert all(item["status"] in ("oneri", "onay_bekliyor", "ertelendi") for item in plan)


def test_cli_stdout_json(monkeypatch):
    monkeypatch.delenv("LUMOS_ENTROPY_PROVIDER", raising=False)
    report = _run_cli(env={"PYTHONPATH": PYTHONPATH})
    assert report["meta"]["evidence_basis"] == "local_scan"


def test_does_not_call_get_entropy():
    """Scanner modülü get_entropy/get_random_bytes import veya çağrı yapmaz."""
    import ast

    import security.readiness.scanner as scanner_mod

    tree = ast.parse(Path(scanner_mod.__file__).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node, ast.Attribute) and node.attr in ("get_entropy", "get_random_bytes"):
            names.add(node.attr)

    assert "get_entropy" not in names
    assert "get_random_bytes" not in names
