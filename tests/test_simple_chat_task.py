"""simple_chat_task: extract_task + run_task, verilen klasörün içinde."""

from __future__ import annotations

from pathlib import Path

import pytest

from core import simple_chat_task
from core.simple_chat_task import extract_task, run_task


def test_extract_py_create() -> None:
    task = extract_task("test.py oluştur içine print yaz")
    assert task is not None
    assert task["action"] == "create_file"
    assert task["input"]["filename"] == "test.py"


def test_extract_none_without_py() -> None:
    assert extract_task("sadece oluştur") is None


def test_run_task_requires_repo_root(tmp_path: Path) -> None:
    task = extract_task("test.py oluştur")
    assert task is not None
    with pytest.raises(ValueError, match="repo_root gerekli"):
        run_task(task, repo_root=None)
    assert list(tmp_path.iterdir()) == []


def test_run_task_writes_only_inside_repo_root(tmp_path: Path) -> None:
    task = extract_task("test.py oluştur içine print yaz")
    assert task is not None
    assert run_task(task, repo_root=tmp_path) == "OK"
    written = tmp_path / "test.py"
    assert written.read_text(encoding="utf-8") == "print('hello')\n"
    assert list(tmp_path.iterdir()) == [written]


def test_run_task_refuses_a_path_outside_repo_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside.py"
    task = {
        "action": "create_file",
        "input": {"filename": "../outside.py", "content": "print('no')\n"},
    }
    with pytest.raises(ValueError, match="tek bir .py"):
        run_task(task, repo_root=tmp_path)
    assert not outside.exists()


def test_run_task_has_no_personal_work_path() -> None:
    source = Path(simple_chat_task.__file__).read_text(encoding="utf-8")
    assert "WORK_2026" not in source
    assert "/Users/" not in source
