"""Dosya akışı (DOSYA-PANEL-SINK-01): panel `.lumos` yazımları merkezi
workspace_contract guard'ından geçer.

- Canlı modda (varsayılan) davranış birebir korunur: tasks.json ve trash yazımı
  başarılı.
- Sandbox modunda (LUMOS_SANDBOX_MODE=true) canlı çekirdek state path'ine panel
  yazımı CoreWriteForbidden ile reddedilir (fail-closed); panel artık merkezi
  sözleşmeyi/guard'ı atlamaz.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from core.workspace_contract import CoreWriteForbidden  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _load_panel_tasks_server():
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    return pts


def _doc() -> dict:
    return {"v": 1, "tasks": [{"id": "tsk_1", "title": "keep"}], "events": []}


# --- Canlı mod: davranış korunur -------------------------------------------


def test_write_doc_live_mode_writes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    monkeypatch.delenv("LUMOS_SANDBOX_MODE", raising=False)
    pts = _load_panel_tasks_server()
    pts._write_doc(_doc(), evidence=None)
    assert (tmp_path / "tasks.json").is_file()
    assert "keep" in (tmp_path / "tasks.json").read_text(encoding="utf-8")


def test_write_trash_task_file_live_mode_writes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    monkeypatch.delenv("LUMOS_SANDBOX_MODE", raising=False)
    pts = _load_panel_tasks_server()
    pts._write_trash_task_file("tsk_1", {"title": "silinen"}, "2026-07-21T00:00:00Z")
    trash_files = list((tmp_path / "trash").glob("*.json"))
    assert len(trash_files) == 1
    assert "silinen" in trash_files[0].read_text(encoding="utf-8")


# --- Sandbox mod: canlı çekirdeğe yazım reddedilir (fail-closed) -------------


def test_write_doc_sandbox_mode_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("LUMOS_SANDBOX_MODE", "true")
    pts = _load_panel_tasks_server()
    with pytest.raises(CoreWriteForbidden):
        pts._write_doc(_doc(), evidence=None)
    # Canlı çekirdek tasks.json yazılmadı.
    assert not (tmp_path / "tasks.json").exists()


def test_write_trash_task_file_sandbox_mode_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("LUMOS_SANDBOX_MODE", "true")
    pts = _load_panel_tasks_server()
    with pytest.raises(CoreWriteForbidden):
        pts._write_trash_task_file("tsk_1", {"title": "silinen"}, "2026-07-21T00:00:00Z")
    trash_dir = tmp_path / "trash"
    assert not trash_dir.exists() or not list(trash_dir.glob("*.json"))


# --- Kaynak düzeyi: guard fiilen bağlı -------------------------------------


def test_panel_write_paths_wired_to_guard() -> None:
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    assert "def _guard_core_write" in src
    assert "allow_write_to_core" in src
    # _write_doc ve _write_trash_task_file guard'ı çağırır.
    write_doc = src.split("def _write_doc")[1].split("\ndef ")[0]
    assert "_guard_core_write(" in write_doc
    trash_fn = src.split("def _write_trash_task_file")[1].split("\ndef ")[0]
    assert "_guard_core_write(" in trash_fn
    # Trash: guard, canlı dizin mkdir'inden önce çağrılır (sandbox'ta mkdir bile olmaz).
    assert trash_fn.index("_guard_core_write(") < trash_fn.index("d.mkdir(")


def test_handlers_translate_core_write_forbidden_to_client_error() -> None:
    """CoreWriteForbidden işlenmeyen istisna olarak 500'e düşmez; yapılandırılmış 403'e çevrilir."""
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    do_post = src.split("def do_POST")[1].split("\n    def ")[0]
    assert "except CoreWriteForbidden" in do_post
    assert "403" in do_post
    do_put = src.split("def do_PUT")[1].split("\n    def ")[0]
    assert "except CoreWriteForbidden" in do_put
    assert "403" in do_put


def test_permanent_delete_guards_before_destructive_unlink() -> None:
    """Kalıcı silme: guard, yıkıcı unlink'ten ÖNCE çağrılır (sandbox'ta kısmi mutasyon olmaz)."""
    src = (_REPO_ROOT / "panel" / "scripts" / "panel_tasks_server.py").read_text(encoding="utf-8")
    fn = src.split("def _post_delete_permanent")[1].split("\n    def ")[0]
    assert "_guard_core_write(tpath)" in fn
    assert "tpath.unlink(" in fn
    # Guard, unlink'ten önce gelmeli.
    assert fn.index("_guard_core_write(tpath)") < fn.index("tpath.unlink(")
