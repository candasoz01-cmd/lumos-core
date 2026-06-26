"""Tests for Qiskit Aer approval-gated connect and usage recommendations."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from integrations.models import IntegrationRequest
from integrations.quantum_usage_tracker import (
    CONNECTS_PER_DAY_ACTIVE,
    EVENTS_PER_WEEK_ACTIVE,
    record_quantum_usage,
    recommend_usage_mode,
)
from integrations.resource_mode_advisor import ResourceLayer, resource_usage_path
from integrations.registry import register_default_integrations


@pytest.fixture
def tmp_lumos_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / ".lumos"
    base.mkdir()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(base))
    return base


def test_qiskit_aer_connect_blocks_without_approval():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="quantum",
            action="connect",
            payload={"provider_id": "qiskit_aer_sim"},
        ),
    )
    assert result.ok is False
    assert result.error == "approval_required"
    assert result.data["requires_approval"] is True


def test_qiskit_aer_connect_not_configured_when_deps_missing(tmp_lumos_base: Path):
    reg = register_default_integrations()
    with patch(
        "integrations.providers.quantum_provider.qiskit_aer_import_status",
        return_value={
            "qiskit_available": False,
            "qiskit_aer_available": False,
            "ready": False,
            "install_hint": "pip install qiskit qiskit-aer",
        },
    ):
        result = reg.run(
            IntegrationRequest(
                provider="quantum",
                action="connect",
                payload={"provider_id": "qiskit_aer", "approved": True},
            ),
        )
    assert result.ok is False
    assert result.error == "not_configured"
    assert "install_hint" in result.data
    assert result.data["recommended_mode"] in ("active", "passive", "insufficient_data")


def test_qiskit_aer_connect_success_with_mock_smoke(tmp_lumos_base: Path):
    reg = register_default_integrations()
    smoke = {"smoke_ok": True, "qubits": 1, "shots": 1, "counts": {"0": 1}}
    import_status = {
        "qiskit_available": True,
        "qiskit_aer_available": True,
        "ready": True,
        "install_hint": "pip install qiskit qiskit-aer",
    }
    with (
        patch(
            "integrations.providers.quantum_provider.qiskit_aer_import_status",
            return_value=import_status,
        ),
        patch(
            "integrations.providers.quantum_provider.run_aer_smoke",
            return_value=smoke,
        ),
    ):
        result = reg.run(
            IntegrationRequest(
                provider="quantum",
                action="connect",
                payload={"provider_id": "qiskit_aer_sim", "user_approved": True},
            ),
        )
    assert result.ok is True
    assert result.data["connection_status"] == "connected"
    assert result.data["smoke"] == smoke
    assert result.data["provider_id"] == "qiskit_aer"
    assert result.data["autonomous_connect"] is False


def test_quantum_list_catalog_unchanged_except_usage_hint(tmp_lumos_base: Path):
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(provider="quantum", action="list_catalog", payload={}),
    )
    assert result.ok is True
    assert result.data["count"] == 13
    assert result.data["autonomous_connect"] is False
    ids = {p["provider_id"] for p in result.data["providers"]}
    assert "qiskit_aer" in ids
    assert "recommended_mode" in result.data


def test_usage_recommendation_insufficient_data(tmp_lumos_base: Path):
    rec = recommend_usage_mode(base_dir=tmp_lumos_base)
    assert rec["recommended_mode"] == "insufficient_data"
    assert rec["default_mode"] == "passive"


def test_usage_recommendation_active_high_frequency(tmp_lumos_base: Path):
    for _ in range(EVENTS_PER_WEEK_ACTIVE):
        record_quantum_usage("list_catalog", base_dir=tmp_lumos_base)
    rec = recommend_usage_mode(base_dir=tmp_lumos_base)
    assert rec["recommended_mode"] == "active"
    assert rec["events_last_7d"] >= EVENTS_PER_WEEK_ACTIVE


def test_usage_recommendation_active_connects_per_day(tmp_lumos_base: Path):
    for _ in range(CONNECTS_PER_DAY_ACTIVE):
        record_quantum_usage("connect", provider_id="qiskit_aer", base_dir=tmp_lumos_base)
    rec = recommend_usage_mode(base_dir=tmp_lumos_base)
    assert rec["recommended_mode"] == "active"
    assert rec["connects_last_24h"] >= CONNECTS_PER_DAY_ACTIVE


def test_usage_recommendation_action():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(provider="quantum", action="usage_recommendation", payload={}),
    )
    assert result.ok is True
    assert result.data["recommended_mode"] in ("active", "passive", "insufficient_data")
    assert result.data["default_mode"] == "passive"


def test_quantum_usage_writes_shared_resource_jsonl(tmp_lumos_base: Path):
    record_quantum_usage("connect", provider_id="qiskit_aer", base_dir=tmp_lumos_base)
    path = resource_usage_path(tmp_lumos_base)
    assert path.is_file()
    assert '"layer": "quantum"' in path.read_text(encoding="utf-8")


def test_quantum_recommendation_uses_resource_layer(tmp_lumos_base: Path):
    from integrations.resource_mode_advisor import recommend_mode

    for _ in range(EVENTS_PER_WEEK_ACTIVE):
        record_quantum_usage("list_catalog", base_dir=tmp_lumos_base)
    direct = recommend_mode(ResourceLayer.QUANTUM, base_dir=tmp_lumos_base)
    wrapped = recommend_usage_mode(base_dir=tmp_lumos_base)
    assert direct["recommended_mode"] == wrapped["recommended_mode"] == "active"


def test_ibm_connect_still_not_configured_with_approval():
    reg = register_default_integrations()
    result = reg.run(
        IntegrationRequest(
            provider="quantum",
            action="connect",
            payload={"provider_id": "ibm_quantum", "approved": True},
            risk_level="high",
            requires_approval=True,
        ),
    )
    assert result.ok is False
    assert result.error == "quantum_provider_not_configured"
