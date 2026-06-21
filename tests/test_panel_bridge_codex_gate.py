"""ADR-012: panel bridge task_actions_gate — check_policy enforcement."""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from policy.action_policy import CREATE_TASK, DELETE_TASK  # noqa: E402
from core.panel_bridge_state import (  # noqa: E402
    build_panel_read_state,
    task_action_gate,
    task_actions_gate,
)


def test_task_action_gate_offline_blocks_create(monkeypatch) -> None:
    monkeypatch.delenv("LUMOS_MODE", raising=False)
    monkeypatch.delenv("LUMOS_PROFILE", raising=False)
    monkeypatch.delenv("LUMOS_SANDBOX_MODE", raising=False)
    gate = task_action_gate(CREATE_TASK)
    assert gate["enabled"] is False
    assert gate["reason"]
    assert "Demo panel" in gate["reason"]
    assert "ADR-012" in gate["reason"]
    assert "POLICY_BLOCKED" in gate["reason"]
    assert "çevrimdışı" in gate["reason"]


def test_task_action_gate_online_allows_create(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.delenv("LUMOS_SESSION_UNLOCKED", raising=False)
    gate = task_action_gate(CREATE_TASK)
    assert gate["enabled"] is True
    assert "Mutasyon izinli" in gate["reason"]


def test_task_action_gate_online_koruma_blocks_delete(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.delenv("LUMOS_SESSION_UNLOCKED", raising=False)
    gate = task_action_gate(DELETE_TASK)
    assert gate["enabled"] is False
    assert "koruma aktif" in gate["reason"]


def test_task_action_gate_online_unlocked_allows_delete(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_SESSION_UNLOCKED", "true")
    gate = task_action_gate(DELETE_TASK)
    assert gate["enabled"] is True


def test_task_actions_gate_reason_reflects_env(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    monkeypatch.setenv("LUMOS_SANDBOX_MODE", "true")
    gate = task_actions_gate()
    assert gate["enabled"] is True
    reason = gate["reason"]
    assert "çevrimiçi" in reason
    assert "guvenli_yurut" in reason
    assert "sandbox" in reason


def test_build_panel_read_state_exposes_codex_gate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("LUMOS_MODE", "offline")
    monkeypatch.setenv("LUMOS_PROFILE", "rapor")
    state = build_panel_read_state(repo_root=_REPO_ROOT)
    g = state["guidance"]
    assert g["codex_warning"]
    assert g["task_actions_gate"]["enabled"] is False
    assert g["task_actions_gate"]["reason"]
    assert state["dashboard"]["warnings"]
    assert "ADR-012" in state["dashboard"]["warnings"][0]
