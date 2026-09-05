"""Docs contract: Agent Wall observer sandbox v0 + ADR-033 (no runtime)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "agent-wall-observer-sandbox-v0.md"
ADR = ROOT / "docs" / "decisions" / "ADR-033-agent-wall-observer-sandbox.md"
OBS = ROOT / "docs" / "contracts" / "agent-wall-observation-v1.md"
HEAD = "d5248e26"


def test_sandbox_contract_exists_and_locks_mvp_boundary() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "A — sandbox" in text
    assert "Founder decision: A — sandbox" in text
    assert HEAD in text
    assert "MUST NOT" in text
    assert "allowed_roots" in text
    assert "filter.*.clean" in text
    assert "yeni Git yönlendirme" in text
    assert "operatör kimlik" in text
    assert "Fallback" in text
    assert "trusted" in text.lower()
    assert "index/stat" in text.lower() or "Index/stat" in text
    assert "merge adayı değildir" in text
    # No runtime claim
    assert "docs-only" in text.lower() or "docs-only" in text or "Uygulama ayrı dilim" in text


def test_adr_033_records_founder_choice_and_stop() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert "Accepted" in text
    assert HEAD in text
    assert "sandbox" in text.lower()
    assert "STOP" in text
    assert "B/C/D" in text
    assert "runtime sandbox **yok**" in text
    assert "KOD / CANLI yok" in text


def test_observation_v1_points_at_sandbox_gate() -> None:
    text = OBS.read_text(encoding="utf-8")
    assert "agent-wall-observer-sandbox-v0.md" in text
    assert "ADR-033" in text
    assert HEAD in text
    assert "merge adayı değildir" in text
