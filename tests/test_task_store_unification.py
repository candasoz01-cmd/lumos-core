"""TD-01: tek görev kaynağı — engine↔panel ayna sözleşmesi kanıtları."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.panel_bridge_state import _read_tasks_payload  # noqa: E402
from core.task_store_mirror import (  # noqa: E402
    canonical_tasks_file,
    engine_row_id,
    migrate_engine_tasks,
    upsert_engine_task,
)
from task_engine.engine import TASK_COMPLETED, TaskStore  # noqa: E402
from task_engine.profiles import PROFILE_GUVENLI_YURUT  # noqa: E402


def _engine_store(base: Path) -> TaskStore:
    return TaskStore(base / "tasks")


def _canonical_rows(base: Path) -> list[dict]:
    path = canonical_tasks_file(base)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["tasks"]


def test_engine_create_appears_in_canonical_list(tmp_path: Path) -> None:
    store = _engine_store(tmp_path)
    task = store.create("Rapor hazırla", "aylık rapor", PROFILE_GUVENLI_YURUT)

    rows = _canonical_rows(tmp_path)
    assert [r["id"] for r in rows] == [engine_row_id(task.task_id)]
    assert rows[0]["title"] == "Rapor hazırla"
    assert rows[0]["status"] == "active"
    assert rows[0]["source"] == "engine"


def test_panel_surface_reads_engine_task_from_same_source(tmp_path: Path) -> None:
    """TD-01 çıkış kriteri: iki yüzey aynı kaynağı okur.

    Engine yüzeyi TaskStore'dan, panel yüzeyi panel_bridge_state'in
    canonical okuyucusundan aynı görevi görmelidir.
    """
    store = _engine_store(tmp_path)
    task = store.create("Ortak görev", "tek kaynak kanıtı", PROFILE_GUVENLI_YURUT)

    engine_titles = [t.title for t in store.list()] if hasattr(store, "list") else [
        t.title for t in store._tasks
    ]
    payload = _read_tasks_payload(tmp_path)
    panel_titles = [row.get("title") for row in payload["task_list"]]

    assert "Ortak görev" in engine_titles
    assert "Ortak görev" in panel_titles
    assert payload["task_count"] == 1
    assert payload["tasks_file_path"].endswith("tasks.json")
    assert engine_row_id(task.task_id) in [row.get("id") for row in payload["task_list"]]


def test_completed_engine_task_becomes_done_row(tmp_path: Path) -> None:
    store = _engine_store(tmp_path)
    task = store.create("Bitecek iş", "d", PROFILE_GUVENLI_YURUT)
    task.status = TASK_COMPLETED
    store.update(task)

    rows = _canonical_rows(tmp_path)
    assert rows[0]["status"] == "done"


def test_trash_and_archive_remove_canonical_row(tmp_path: Path) -> None:
    store = _engine_store(tmp_path)
    kept = store.create("Kalacak", "d", PROFILE_GUVENLI_YURUT)
    trashed = store.create("Çöpe gidecek", "d", PROFILE_GUVENLI_YURUT)
    archived = store.create("Arşive gidecek", "d", PROFILE_GUVENLI_YURUT)

    assert store.move_to_trash(trashed.task_id) is True
    assert store.archive(archived.task_id) is True

    rows = _canonical_rows(tmp_path)
    assert [r["id"] for r in rows] == [engine_row_id(kept.task_id)]


def test_sandbox_runs_do_not_touch_canonical(tmp_path: Path) -> None:
    live = tmp_path / "live"
    store = TaskStore(tmp_path / "tasks", sandbox_mode=True, live_base_dir=live)
    store.create("Sandbox işi", "d", PROFILE_GUVENLI_YURUT)

    assert not canonical_tasks_file(live).is_file()
    assert not canonical_tasks_file(tmp_path).is_file()


def test_mirror_preserves_existing_panel_tasks_and_is_idempotent(tmp_path: Path) -> None:
    canonical = canonical_tasks_file(tmp_path)
    canonical.write_text(
        json.dumps({"v": 1, "tasks": [{"id": "p1", "title": "Panel görevi", "status": "active"}], "events": []}),
        encoding="utf-8",
    )
    store = _engine_store(tmp_path)
    task = store.create("Engine görevi", "d", PROFILE_GUVENLI_YURUT)

    assert upsert_engine_task(tmp_path, task.to_dict()) is False  # değişiklik yok — idempotent

    rows = _canonical_rows(tmp_path)
    assert [r["id"] for r in rows] == ["p1", engine_row_id(task.task_id)]
    assert rows[0]["title"] == "Panel görevi"


def test_migration_projects_existing_engine_store_once(tmp_path: Path) -> None:
    engine_dir = tmp_path / "tasks"
    engine_dir.mkdir(parents=True)
    engine_file = engine_dir / "tasks.json"
    engine_file.write_text(
        json.dumps(
            {
                "tasks": [
                    {"task_id": 1, "title": "Eski görev", "status": "bekliyor"},
                    {"task_id": 2, "title": "Eski biten", "status": "tamamlandi"},
                    {"task_id": 3, "title": "Arşivli", "status": "tamamlandi", "archived": True},
                ],
                "next_id": 4,
            }
        ),
        encoding="utf-8",
    )

    changed = migrate_engine_tasks(engine_file, tmp_path)
    assert changed == 2
    rows = {r["id"]: r["status"] for r in _canonical_rows(tmp_path)}
    assert rows == {engine_row_id(1): "active", engine_row_id(2): "done"}

    assert migrate_engine_tasks(engine_file, tmp_path) == 0  # idempotent


def test_corrupt_canonical_is_not_overwritten(tmp_path: Path) -> None:
    canonical = canonical_tasks_file(tmp_path)
    canonical.write_text("{bozuk json", encoding="utf-8")
    store = _engine_store(tmp_path)
    store.create("Görev", "d", PROFILE_GUVENLI_YURUT)  # ayna hatası akışı bozmamalı

    assert canonical.read_text(encoding="utf-8") == "{bozuk json"
    assert len(store._tasks) == 1


def test_reader_normalizes_legacy_engine_rows(tmp_path: Path) -> None:
    """Geçiş köprüsü: base/tasks.json'da eski engine formatı da okunur."""
    canonical = canonical_tasks_file(tmp_path)
    canonical.write_text(
        json.dumps(
            {
                "v": 1,
                "tasks": [
                    {"task_id": 7, "title": "Eski motor görevi", "status": "calisiyor"},
                    {"task_id": 8, "title": "Eski biten", "status": "tamamlandi"},
                ],
                "events": [],
            }
        ),
        encoding="utf-8",
    )
    payload = _read_tasks_payload(tmp_path)
    by_id = {r["id"]: r for r in payload["task_list"]}
    assert by_id[engine_row_id(7)]["status"] == "active"
    assert by_id[engine_row_id(8)]["status"] == "done"
    assert payload["task_count"] == 2
    assert payload["skipped_rows"] == []


def test_reader_reports_unknown_status_as_warning_not_silent(tmp_path: Path) -> None:
    canonical = canonical_tasks_file(tmp_path)
    canonical.write_text(
        json.dumps(
            {"v": 1, "tasks": [{"task_id": 9, "title": "Tuhaf", "status": "uçtu"}], "events": []}
        ),
        encoding="utf-8",
    )
    payload = _read_tasks_payload(tmp_path)
    assert payload["task_list"][0]["status"] == "active"  # güvenli varsayılan
    assert any("uçtu" in str(w.get("reason", "")) for w in payload["warnings"])


def test_reader_skips_malformed_rows_and_reports_them(tmp_path: Path) -> None:
    canonical = canonical_tasks_file(tmp_path)
    canonical.write_text(
        json.dumps(
            {
                "v": 1,
                "tasks": [
                    {"id": "ok1", "title": "İyi", "status": "active"},
                    "bozuk-satır",
                    {"title": "kimliksiz", "status": "active"},
                ],
                "events": [],
            }
        ),
        encoding="utf-8",
    )
    payload = _read_tasks_payload(tmp_path)
    assert [r["id"] for r in payload["task_list"]] == ["ok1"]
    assert {s["reason"] for s in payload["skipped_rows"]} == {"row_not_object", "no_id_or_task_id"}


def test_reader_dedups_legacy_and_mirrored_same_task(tmp_path: Path) -> None:
    """Göç anı: eski engine satırı + aynalı canonical satır aynı id'ye iner."""
    canonical = canonical_tasks_file(tmp_path)
    canonical.write_text(
        json.dumps(
            {
                "v": 1,
                "tasks": [
                    {"task_id": 5, "title": "Göç öncesi", "status": "bekliyor"},
                    {"id": engine_row_id(5), "title": "Göç sonrası", "status": "active", "source": "engine"},
                ],
                "events": [],
            }
        ),
        encoding="utf-8",
    )
    payload = _read_tasks_payload(tmp_path)
    rows = [r for r in payload["task_list"] if r["id"] == engine_row_id(5)]
    assert len(rows) == 1
    assert rows[0]["title"] == "Göç sonrası"  # son yazılan kazanır
