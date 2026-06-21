"""PR-C4: CLI confirmation flow — request → onayla → consume."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from cli.cli_parse import normalize_command  # noqa: E402
from cli.cli_tasks_mutation import (  # noqa: E402
    TaskMutationContext,
    handle_confirmation_approve,
    handle_confirmation_cancel,
    handle_task_mutation,
)
from policy.confirmation_policy import (  # noqa: E402
    ensure_cli_mutation_confirmation,
    request_confirmation,
)
from task_engine import TaskStore, PROFILE_GUVENLI_YURUT  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_confirmation_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)


def _make_mut_ctx(base_dir: str, store: TaskStore) -> TaskMutationContext:
    ctx = TaskMutationContext()
    ctx.base_dir = base_dir
    ctx.task_store = store
    ctx.current_permission_profile = ["guvenli_yurut"]
    ctx.general_approval = [True]
    ctx.session_consent = [False]
    ctx.current_task = [None]
    ctx.last_action = [None]
    ctx.today_date = [""]
    ctx.today_actions = [[]]
    ctx.last_task_create_fingerprint = [None]
    ctx.record_today_action = lambda _a: None
    ctx.pending_intent = [None]
    ctx.pending_action = [None]
    ctx.pending_confirmation = []
    ctx.policy_runtime_mode = "online"
    ctx.policy_is_locked = lambda: False
    return ctx


def test_onayla_and_onay_iptal_parse(tmp_path: Path) -> None:
    base = tmp_path
    r, a = normalize_command("onayla abc123", base, {})
    assert r == "onayla"
    assert a == ["abc123"]
    r, a = normalize_command("onay iptal abc123", base, {})
    assert r == "onay_iptal"
    assert a == ["abc123"]
    r, a = normalize_command("onay iptal", base, {})
    assert r == "onay_iptal"
    assert a == []


def test_ensure_cli_mutation_requires_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"title": "Demo"}
    result = ensure_cli_mutation_confirmation("create_task", scope, None, base_dir=tmp_path)
    assert not result.allowed


def test_ensure_cli_mutation_confirmation_id_consumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    scope = {"id": "7"}
    pending = request_confirmation("delete_task", scope, base_dir=tmp_path)
    result = ensure_cli_mutation_confirmation(
        "delete_task",
        scope,
        pending.confirmation_id,
        base_dir=tmp_path,
    )
    assert result.allowed


def test_gorev_sil_moves_to_trash_not_permanent(tmp_path: Path) -> None:
    """gorev_sil soft delete: trash dosyası yazılır, kalıcı delete çağrılmaz."""
    store = TaskStore(tmp_path)
    task = store.create("Silinecek", "desc", PROFILE_GUVENLI_YURUT)
    ctx = _make_mut_ctx(str(tmp_path), store)
    handle_task_mutation("gorev_sil", [str(task.task_id)], ctx)
    assert store.get(task.task_id) is None
    trash_dir = tmp_path / "trash"
    assert trash_dir.is_dir()
    trash_files = list(trash_dir.glob("*.json"))
    assert len(trash_files) == 1
    record = json.loads(trash_files[0].read_text(encoding="utf-8"))
    assert str(record.get("id")) == str(task.task_id)
    assert record.get("payload", {}).get("task_id") == task.task_id


def test_create_confirmation_request_then_onayla(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    store = TaskStore(tmp_path)
    ctx = _make_mut_ctx(str(tmp_path), store)
    brain_result = SimpleNamespace(
        task_id=1,
        goal="Test görev",
        human_readable_summary="Görev oluşturuldu.",
        pipeline=None,
    )
    with patch("cli.cli_tasks_mutation.brain_run", return_value=brain_result):
        handle_task_mutation("gorev_olustur", ["Test görev"], ctx)
    out1 = capsys.readouterr().out
    assert "Onay gerekli" in out1
    assert "onayla" in out1
    assert len(store.list_all()) == 0
    assert len(ctx.pending_confirmation) == 1
    cid = ctx.pending_confirmation[0]["confirmation_id"]
    with patch("cli.cli_tasks_mutation.brain_run", return_value=brain_result):
        handle_confirmation_approve(cid, ctx)
    out2 = capsys.readouterr().out
    assert "Görev oluşturuldu" in out2
    assert len(store.list_all()) >= 0
    assert len(ctx.pending_confirmation) == 0


def test_delete_confirmation_request_then_onayla(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    store = TaskStore(tmp_path)
    task = store.create("Sil", "desc", PROFILE_GUVENLI_YURUT)
    ctx = _make_mut_ctx(str(tmp_path), store)
    handle_task_mutation("gorev_sil", [str(task.task_id)], ctx)
    out1 = capsys.readouterr().out
    assert "Onay gerekli" in out1
    assert store.get(task.task_id) is not None
    cid = ctx.pending_confirmation[0]["confirmation_id"]
    handle_confirmation_approve(cid, ctx)
    out2 = capsys.readouterr().out
    assert "çöpe taşındı" in out2
    assert store.get(task.task_id) is None
    assert (tmp_path / "trash").is_dir()


def test_onay_iptal_clears_pending(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "true")
    store = TaskStore(tmp_path)
    ctx = _make_mut_ctx(str(tmp_path), store)
    handle_task_mutation("gorev_sil", ["1"], ctx)
    assert len(ctx.pending_confirmation) == 1
    cid = ctx.pending_confirmation[0]["confirmation_id"]
    handle_confirmation_cancel([cid], ctx)
    assert len(ctx.pending_confirmation) == 0


def test_disabled_confirmation_create_immediate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = TaskStore(tmp_path)
    ctx = _make_mut_ctx(str(tmp_path), store)
    brain_result = SimpleNamespace(
        task_id=1,
        goal="Hemen",
        human_readable_summary="OK",
        pipeline=None,
    )
    with patch("cli.cli_tasks_mutation.brain_run", return_value=brain_result):
        handle_task_mutation("gorev_olustur", ["Hemen"], ctx)
    out = capsys.readouterr().out
    assert "Onay gerekli" not in out
    assert len(ctx.pending_confirmation) == 0
