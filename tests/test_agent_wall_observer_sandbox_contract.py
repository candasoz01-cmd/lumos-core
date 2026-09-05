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


# --- v0.1: motor kararı + yürütme modeli + host zorunlulukları -------------


def test_engines_are_not_equal_security_boundaries() -> None:
    """Linux bwrap birincil sınır; macOS seatbelt yalnız savunma derinliği."""
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Birincil güvenlik sınırı" in text
    assert "Yalnız savunma derinliği" in text
    assert "bwrap" in text
    assert "mikro-VM veya izole Linux" in text
    # Eşdeğerlik iddiası yasak
    assert "İki motor\neşdeğer güvenlik sınırı sayılmaz" in text or "eşdeğer güvenlik sınırı sayılmaz" in text


def test_execution_model_is_capability_denial_not_execution_prevention() -> None:
    """§4.1 ölçümle yeniden yazıldı: kod koşabilir, yetenek reddedilir."""
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Repository-controlled code may execute as a side effect of Git inspection." in text
    assert "Security does not rely on preventing execution" in text
    assert "denying" in text and "capabilities outside the observer" in text
    for capability in ("operator credentials", "unauthorized host files", "the network"):
        assert capability in text


def test_host_side_requirements_are_normative() -> None:
    """Env temizliği ve süreç sınırları motora bırakılamaz."""
    text = CONTRACT.read_text(encoding="utf-8")
    assert "clearenv" in text
    assert "env allowlist" in text
    assert "fork tavanı" in text
    assert "FD temizliği" in text or "file descriptor" in text


def test_weak_evidence_is_marked_not_claimed_as_proven() -> None:
    """Ubuntu CI'da koşmadan ağ izolasyonu kanıtlanmış sayılamaz."""
    text = CONTRACT.read_text(encoding="utf-8")
    assert "Linux network isolation proven" in text
    assert "yazılamaz" in text
    assert "zayıf kanıt" in text.lower()


def test_measurement_record_and_probe_script_exist() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "scripts/wall_sandbox_capability_probe.py" in text
    assert (ROOT / "scripts" / "wall_sandbox_capability_probe.py").is_file()
    # Ölçüm ham gerçeği taşımalı: filter her iki motorda da koştu
    assert "koştu" in text
