"""Tests for shared resource mode advisor."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from integrations.resource_mode_advisor import (
    CONNECTS_PER_DAY_ACTIVE,
    EVENTS_PER_WEEK_ACTIVE,
    IDLE_DAYS_PASSIVE,
    ResourceLayer,
    ResourceModeApprovalRequired,
    apply_mode_change,
    propose_mode_change,
    recommend_mode,
    record_event,
    resource_modes_path,
    resource_usage_path,
)


@pytest.fixture
def tmp_lumos_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / ".lumos"
    base.mkdir()
    monkeypatch.setenv("LUMOS_BASE_DIR", str(base))
    return base


def test_record_event_appends_jsonl(tmp_lumos_base: Path) -> None:
    record_event(ResourceLayer.QUANTUM, "connect", {"provider_id": "qiskit_aer"})
    path = resource_usage_path(tmp_lumos_base)
    assert path.is_file()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert '"layer": "quantum"' in lines[0]
    assert '"action": "connect"' in lines[0]


def test_recommend_insufficient_data(tmp_lumos_base: Path) -> None:
    rec = recommend_mode(ResourceLayer.VISION, base_dir=tmp_lumos_base)
    assert rec["recommended_mode"] == "insufficient_data"
    assert rec["default_mode"] == "passive"
    assert rec["reason"]


def test_recommend_active_high_event_count(tmp_lumos_base: Path) -> None:
    for _ in range(EVENTS_PER_WEEK_ACTIVE):
        record_event(ResourceLayer.GPU, "inference", base_dir=tmp_lumos_base)
    rec = recommend_mode(ResourceLayer.GPU, base_dir=tmp_lumos_base)
    assert rec["recommended_mode"] == "active"
    assert rec["stats"]["events_last_7d"] >= EVENTS_PER_WEEK_ACTIVE


def test_recommend_active_connects_per_day(tmp_lumos_base: Path) -> None:
    for _ in range(CONNECTS_PER_DAY_ACTIVE):
        record_event(ResourceLayer.INTEGRATIONS, "connect", base_dir=tmp_lumos_base)
    rec = recommend_mode(ResourceLayer.INTEGRATIONS, base_dir=tmp_lumos_base)
    assert rec["recommended_mode"] == "active"
    assert rec["stats"]["connects_last_24h"] >= CONNECTS_PER_DAY_ACTIVE


def test_recommend_passive_after_idle(tmp_lumos_base: Path) -> None:
    path = resource_usage_path(tmp_lumos_base)
    path.parent.mkdir(parents=True, exist_ok=True)
    old_ts = (datetime.now(timezone.utc) - timedelta(days=IDLE_DAYS_PASSIVE + 1)).isoformat()
    path.write_text(
        f'{{"timestamp": "{old_ts}", "layer": "voice", "action": "connect"}}\n',
        encoding="utf-8",
    )
    rec = recommend_mode(ResourceLayer.VOICE, base_dir=tmp_lumos_base)
    assert rec["recommended_mode"] == "passive"
    assert "gün" in rec["reason"]


def test_propose_mode_change_never_auto(tmp_lumos_base: Path) -> None:
    payload = propose_mode_change(ResourceLayer.CYBER, base_dir=tmp_lumos_base)
    assert payload["never_auto"] is True
    assert payload["requires_approval"] is True
    assert payload["layer"] == "cyber"
    assert "proposed_mode" in payload


def test_apply_without_approval_blocked(tmp_lumos_base: Path) -> None:
    result = apply_mode_change(
        ResourceLayer.LOCAL_MODELS,
        "active",
        user_approved=False,
        base_dir=tmp_lumos_base,
    )
    assert result.ok is False
    assert result.error == "approval_required"
    assert not resource_modes_path(tmp_lumos_base).is_file()


def test_apply_without_approval_raises(tmp_lumos_base: Path) -> None:
    with pytest.raises(ResourceModeApprovalRequired):
        apply_mode_change(
            ResourceLayer.LOCAL_MODELS,
            "active",
            user_approved=False,
            base_dir=tmp_lumos_base,
            raise_on_denied=True,
        )


def test_apply_with_approval_persists_mode(tmp_lumos_base: Path) -> None:
    result = apply_mode_change(
        ResourceLayer.QUANTUM,
        "active",
        user_approved=True,
        base_dir=tmp_lumos_base,
    )
    assert result.ok is True
    assert result.mode == "active"
    modes_path = resource_modes_path(tmp_lumos_base)
    assert modes_path.is_file()
    assert '"quantum"' in modes_path.read_text(encoding="utf-8")


def test_layers_isolated_in_jsonl(tmp_lumos_base: Path) -> None:
    record_event(ResourceLayer.QUANTUM, "connect", base_dir=tmp_lumos_base)
    record_event(ResourceLayer.CYBER, "scan", base_dir=tmp_lumos_base)
    q_rec = recommend_mode(ResourceLayer.QUANTUM, base_dir=tmp_lumos_base)
    c_rec = recommend_mode(ResourceLayer.CYBER, base_dir=tmp_lumos_base)
    assert q_rec["stats"]["events_last_7d"] == 1
    assert c_rec["stats"]["events_last_7d"] == 1
