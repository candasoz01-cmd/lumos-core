"""Tek açık onay. Silme ve görev motoru bu dosyada birleştirilmez."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.explicit_approval import (
    grant_explicit_approval,
    is_explicit_approval_open,
    reset_explicit_approval_session,
    revoke_explicit_approval,
)
from task_engine import PROFILE_KISITLI_OTONOM, TaskEngine, TaskStep, TaskStore
from task_engine.profiles import STEP_TYPE_WRITE_LOCAL

_UNATTENDED = (
    Path("src/kando/llm.py"),
    Path("src/kando/agent_runner.py"),
    Path("src/kando/cursor_bridge.py"),
)


@pytest.fixture(autouse=True)
def _isolated_approval(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("LUMOS_GENERAL_APPROVAL", raising=False)
    reset_explicit_approval_session()
    yield
    reset_explicit_approval_session()


def test_approval_closed_until_granted() -> None:
    assert is_explicit_approval_open() is False
    assert grant_explicit_approval() is True
    assert is_explicit_approval_open() is True
    revoke_explicit_approval()
    assert is_explicit_approval_open() is False


def test_panel_env_opens_the_same_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_GENERAL_APPROVAL", "1")
    assert is_explicit_approval_open() is True


def test_broken_constants_refuse_approval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("core.inviolable.verify_core_constants", lambda: False)
    monkeypatch.setenv("LUMOS_GENERAL_APPROVAL", "yes")
    assert grant_explicit_approval() is False
    assert is_explicit_approval_open() is False


def test_unapproved_write_does_not_run() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        task = store.create("Yaz", "özet ver", PROFILE_KISITLI_OTONOM)
        task.steps = [TaskStep("Dosyaya yaz", kind=STEP_TYPE_WRITE_LOCAL)]
        store.update(task)
        engine = TaskEngine(
            store,
            PROFILE_KISITLI_OTONOM,
            general_approval=is_explicit_approval_open(),
        )
        ok, _msg = engine.run_task(task.task_id)
        assert ok is False
        saved = store.get(task.task_id)
        assert saved is not None
        assert saved.status == "durdu"


def test_granted_approval_allows_write_step() -> None:
    assert grant_explicit_approval() is True
    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        task = store.create("Yaz", "özet ver", PROFILE_KISITLI_OTONOM)
        task.steps = [TaskStep("Dosyaya yaz", kind=STEP_TYPE_WRITE_LOCAL)]
        store.update(task)
        engine = TaskEngine(
            store,
            PROFILE_KISITLI_OTONOM,
            general_approval=is_explicit_approval_open(),
        )
        ok, _msg = engine.run_task(task.task_id)
        assert ok is True
        saved = store.get(task.task_id)
        assert saved is not None
        assert saved.status == "tamamlandi"


def test_unattended_entries_do_not_hardcode_approval() -> None:
    for path in _UNATTENDED:
        text = path.read_text(encoding="utf-8")
        assert "general_approval=True" not in text
        assert "is_explicit_approval_open()" in text
