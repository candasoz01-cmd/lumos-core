"""ADR-012: panel bridge task_actions_gate — check_policy + profil guard enforcement."""
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


class _RuntimeLock:
    def __init__(self, unlocked: bool) -> None:
        self.unlocked = unlocked


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


def test_task_action_gate_online_rapor_blocks_create(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.delenv("LUMOS_SESSION_UNLOCKED", raising=False)
    monkeypatch.delenv("LUMOS_PROFILE", raising=False)
    gate = task_action_gate(CREATE_TASK)
    assert gate["enabled"] is False
    assert "[PROFILE_BLOCKED]" in gate["reason"]
    assert "rapor" in gate["reason"]
    assert "safe_local" in gate["reason"]


def test_task_action_gate_online_guvenli_yurut_allows_create(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    monkeypatch.delenv("LUMOS_SESSION_UNLOCKED", raising=False)
    gate = task_action_gate(CREATE_TASK)
    assert gate["enabled"] is True
    assert "Mutasyon izinli" in gate["reason"]
    assert "profil" in gate["reason"]


def test_task_action_gate_online_invalid_profile_blocks(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "admin")
    gate = task_action_gate(CREATE_TASK)
    assert gate["enabled"] is False
    assert "[PROFILE_BLOCKED]" in gate["reason"]
    assert "Geçersiz profil" in gate["reason"]


def test_task_action_gate_kisitli_otonom_without_approval_blocks(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "kisitli_otonom")
    monkeypatch.delenv("LUMOS_GENERAL_APPROVAL", raising=False)
    gate = task_action_gate(CREATE_TASK)
    assert gate["enabled"] is False
    assert "[PROFILE_BLOCKED]" in gate["reason"]
    assert "LUMOS_GENERAL_APPROVAL" in gate["reason"]


def test_task_action_gate_kisitli_otonom_with_approval_allows(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "kisitli_otonom")
    monkeypatch.setenv("LUMOS_GENERAL_APPROVAL", "true")
    gate = task_action_gate(CREATE_TASK)
    assert gate["enabled"] is True


def test_task_action_gate_guvenli_yurut_put_write_local_blocked(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    gate = task_action_gate(CREATE_TASK, full_doc_replace=True)
    assert gate["enabled"] is False
    assert "[PROFILE_BLOCKED]" in gate["reason"]
    assert "write_local" in gate["reason"]


def test_task_action_gate_kisitli_otonom_put_allowed_with_approval(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "kisitli_otonom")
    monkeypatch.setenv("LUMOS_GENERAL_APPROVAL", "true")
    gate = task_action_gate(CREATE_TASK, full_doc_replace=True)
    assert gate["enabled"] is True


def test_task_action_gate_profile_guard_skippable(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.delenv("LUMOS_PROFILE", raising=False)
    gate = task_action_gate(DELETE_TASK, profile_guard=False)
    assert gate["enabled"] is False
    assert "[PROFILE_BLOCKED]" not in gate["reason"]
    assert "koruma aktif" in gate["reason"]


def test_task_action_gate_online_koruma_blocks_delete(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    monkeypatch.delenv("LUMOS_SESSION_UNLOCKED", raising=False)
    gate = task_action_gate(DELETE_TASK)
    assert gate["enabled"] is False
    assert "koruma aktif" in gate["reason"]


def test_task_action_gate_online_unlocked_allows_delete(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    monkeypatch.setenv("LUMOS_SESSION_UNLOCKED", "true")
    gate = task_action_gate(DELETE_TASK, runtime_lock_state=_RuntimeLock(True))
    assert gate["enabled"] is True


def test_task_action_gate_ignores_session_unlocked_env_without_runtime_lock(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    monkeypatch.setenv("LUMOS_SESSION_UNLOCKED", "true")
    gate = task_action_gate(DELETE_TASK)
    assert gate["enabled"] is False
    assert "koruma aktif" in gate["reason"]


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


def test_task_action_gate_confirmation_disabled_no_change(monkeypatch) -> None:
    """Varsayılan: confirmation kapalı — mevcut profil gate davranışı korunur."""
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    gate = task_action_gate(CREATE_TASK)
    assert gate["enabled"] is True
    assert "[CONFIRMATION_BLOCKED]" not in gate["reason"]


def test_task_action_gate_confirmation_enabled_blocks_without_id(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    gate = task_action_gate(CREATE_TASK)
    assert gate["enabled"] is False
    assert "[CONFIRMATION_BLOCKED]" in gate["reason"]
    assert "create_task" in gate["reason"]
    assert "confirmation_required" in gate["reason"]


def test_task_action_gate_confirmation_enabled_allows_with_grant(
    tmp_path, monkeypatch
) -> None:
    from policy.confirmation_policy import request_confirmation  # noqa: E402

    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    scope = {"title": "Demo görev"}
    pending = request_confirmation("create_task", scope, base_dir=tmp_path)
    gate = task_action_gate(
        CREATE_TASK,
        confirmation_id=pending.confirmation_id,
        scope=scope,
    )
    assert gate["enabled"] is True
    assert "Confirmation geçerli" in gate["reason"]


def test_task_action_gate_confirmation_put_write_local_blocked(monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "kisitli_otonom")
    monkeypatch.setenv("LUMOS_GENERAL_APPROVAL", "true")
    scope = {"route": "PUT /tasks.json"}
    gate = task_action_gate(CREATE_TASK, full_doc_replace=True, scope=scope)
    assert gate["enabled"] is False
    assert "[CONFIRMATION_BLOCKED]" in gate["reason"]
    assert "write_local" in gate["reason"]




def test_bootstrap_panel_runtime_lock_from_bridge_env(monkeypatch) -> None:
    from core.panel_runtime_lock import (  # noqa: E402
        bootstrap_panel_runtime_lock_from_bridge_env,
        clear_panel_runtime_lock_hooks,
        resolve_panel_runtime_lock,
    )

    clear_panel_runtime_lock_hooks()
    try:
        monkeypatch.setenv("LUMOS_MODE", "online")
        monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
        monkeypatch.setenv("LUMOS_SESSION_UNLOCKED", "true")
        bootstrap_panel_runtime_lock_from_bridge_env()
        snap = resolve_panel_runtime_lock()
        assert snap is not None
        assert bool(getattr(snap, "unlocked", False)) is True
        gate = task_action_gate(DELETE_TASK)
        assert gate["enabled"] is True
    finally:
        clear_panel_runtime_lock_hooks()

def test_resolve_panel_runtime_lock_injection() -> None:
    from core.panel_runtime_lock import (  # noqa: E402
        clear_panel_runtime_lock_hooks,
        inject_panel_runtime_lock,
        resolve_panel_runtime_lock,
    )

    clear_panel_runtime_lock_hooks()
    try:
        assert resolve_panel_runtime_lock() is None
        inject_panel_runtime_lock(_RuntimeLock(True))
        snap = resolve_panel_runtime_lock()
        assert snap is not None
        assert bool(getattr(snap, "unlocked", False)) is True
    finally:
        clear_panel_runtime_lock_hooks()


def test_panel_tasks_server_gate_resolves_injected_lock(monkeypatch) -> None:
    from core.panel_runtime_lock import (  # noqa: E402
        clear_panel_runtime_lock_hooks,
        inject_panel_runtime_lock,
    )

    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    monkeypatch.setenv("LUMOS_MODE", "online")
    monkeypatch.setenv("LUMOS_PROFILE", "guvenli_yurut")
    monkeypatch.delenv("LUMOS_SESSION_UNLOCKED", raising=False)
    clear_panel_runtime_lock_hooks()
    try:
        gate_locked = pts._task_action_gate(DELETE_TASK)
        assert gate_locked["enabled"] is False
        inject_panel_runtime_lock(_RuntimeLock(True))
        gate_unlocked = pts._task_action_gate(DELETE_TASK)
        assert gate_unlocked["enabled"] is True
    finally:
        clear_panel_runtime_lock_hooks()
