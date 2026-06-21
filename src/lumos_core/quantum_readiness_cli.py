"""Lumos CLI quantum-readiness subcommand (ADR-013). Wraps scan_quantum_readiness."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from security.readiness.scanner import scan_quantum_readiness


def run_quantum_readiness_scan(
    *,
    repo_root: Path | None = None,
    lumos_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the local read-only readiness scan (no duplicate scanner logic)."""
    return scan_quantum_readiness(repo_root=repo_root, lumos_dir=lumos_dir)


def format_quantum_readiness_summary(report: dict[str, Any]) -> str:
    """Human-readable one-screen summary matching scanner report fields."""
    meta = report.get("meta") or {}
    inv = report.get("crypto_inventory") or {}
    pqc = report.get("post_quantum_transition_readiness") or {}
    entropy = report.get("entropy_lab") or {}
    findings = report.get("evidenced_findings") or []
    plan = report.get("prioritized_migration_plan") or []

    enc = ", ".join(inv.get("encryption_types") or []) or "—"
    lines = [
        "Lumos Quantum Readiness (local_scan, read-only)",
        f"Generated: {meta.get('generated_at', '?')}",
        f"Evidence basis: {meta.get('evidence_basis', '?')}",
        f"Crypto agility: {report.get('crypto_agility_level', '?')}",
        f"PQC status: {pqc.get('pqc_status', '?')}",
        f"Quantum exposure: {inv.get('quantum_exposure_note', '?')}",
        f"Encryption: {enc}",
        f"Findings: {len(findings)} | Migration items: {len(plan)}",
    ]
    if entropy.get("silent_fallback_warning"):
        eff = entropy.get("effective_provider_heuristic", "?")
        lines.append(f"Entropy lab: silent fallback (effective={eff})")
    disclaimer = meta.get("disclaimer")
    if disclaimer:
        lines.append(f"Disclaimer: {disclaimer}")
    return "\n".join(lines)


def emit_quantum_readiness_report(
    report: dict[str, Any],
    *,
    summary: bool = False,
    out: TextIO | None = None,
) -> None:
    """Write JSON (default) or human summary to stdout or a given stream."""
    stream = out or sys.stdout
    if summary:
        stream.write(format_quantum_readiness_summary(report))
        stream.write("\n")
    else:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
