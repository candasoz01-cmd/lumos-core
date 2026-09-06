"""Docs contract: Agent Wall observer sandbox v0 + ADR-033 (no runtime)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "agent-wall-observer-sandbox-v0.md"
ADR = ROOT / "docs" / "decisions" / "ADR-033-agent-wall-observer-sandbox.md"
OBS = ROOT / "docs" / "contracts" / "agent-wall-observation-v1.md"
HEAD = "d5248e26"


def _load_probe():
    path = ROOT / "scripts" / "wall_sandbox_capability_probe.py"
    spec = importlib.util.spec_from_file_location("wall_sandbox_capability_probe", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def test_s0_gate_marks_later_rows_unmeasured_but_preserves_raw_observation() -> None:
    probe = _load_probe()
    results = {
        "broken": {
            "S0 git gerçekten koşuyor mu": {"saglandi": False},
            "S1 filter.*.clean çalıştırma": {"saglandi": True},
        }
    }

    probe.apply_s0_gate(results)

    row = results["broken"]["S1 filter.*.clean çalıştırma"]
    assert row["saglandi"] is None
    assert row["olculen_saglandi"] is True
    assert row["s0_gecerli"] is False


def test_s0_gate_keeps_valid_engine_results() -> None:
    probe = _load_probe()
    results = {
        "working": {
            "S0 git gerçekten koşuyor mu": {"saglandi": True},
            "S1 filter.*.clean çalıştırma": {"saglandi": False},
        }
    }

    probe.apply_s0_gate(results)

    row = results["working"]["S1 filter.*.clean çalıştırma"]
    assert row["saglandi"] is False
    assert row["olculen_saglandi"] is False
    assert row["s0_gecerli"] is True


def test_s3_uses_existing_outside_ssh_fixture(tmp_path: Path) -> None:
    probe = _load_probe()
    fx = probe.Fixture.build(tmp_path)

    result = probe.s3_credentials(
        lambda command, cwd, env, fixture: probe.run_direct(command, cwd, env),
        fx,
    )

    assert fx.operator_ssh.is_dir()
    assert result["ssh_olculdu"] is True
    assert result["ssh_okunabilir"] is True
    assert result["saglandi"] is False


def test_s3_records_unmeasured_when_probe_command_never_reports_status(tmp_path: Path) -> None:
    probe = _load_probe()
    fx = probe.Fixture.build(tmp_path)

    def silent_runner(command, cwd, env, fixture):
        return probe.subprocess.CompletedProcess(command, 1, stdout="", stderr="blocked")

    result = probe.s3_credentials(silent_runner, fx)

    assert result["ssh_olculdu"] is False
    assert result["ssh_okunabilir"] is None
    assert result["saglandi"] is None
    assert "ssh=ölçülmedi" in result["olan"]
