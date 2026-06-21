"""Lumos CLI quantum-readiness subcommand wiring (ADR-013)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHONPATH = f"{REPO_ROOT / 'src'}:{REPO_ROOT / 'packages' / 'kando_runtime' / 'src'}:{REPO_ROOT / 'packages' / 'kando_bridge' / 'src'}"


def _run_lumos_qr(*extra: str) -> subprocess.CompletedProcess[str]:
    env = {**dict(__import__("os").environ), "PYTHONPATH": PYTHONPATH}
    return subprocess.run(
        [sys.executable, "-m", "lumos_core", "quantum-readiness", *extra],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def test_lumos_quantum_readiness_json_stdout():
    proc = _run_lumos_qr()
    report = json.loads(proc.stdout)
    assert report["meta"]["report_type"] == "quantum_readiness"
    assert report["meta"]["evidence_basis"] == "local_scan"
    assert report["meta"]["read_only"] is True
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


def test_lumos_quantum_readiness_summary_flag():
    proc = _run_lumos_qr("--summary")
    out = proc.stdout
    assert "Lumos Quantum Readiness" in out
    assert "local_scan" in out
    assert "Crypto agility:" in out
    assert "PQC status:" in out
    # summary mode must not be raw JSON object
    assert not out.lstrip().startswith("{")


def test_lumos_quantum_readiness_help_lists_subcommand():
    env = {**dict(__import__("os").environ), "PYTHONPATH": PYTHONPATH}
    proc = subprocess.run(
        [sys.executable, "-m", "lumos_core", "quantum-readiness", "--help"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "quantum-readiness" in proc.stdout
    assert "--summary" in proc.stdout
