"""TD-01: tek görev kaynağı sözleşmesinin ayna katmanı.

Sözleşme (docs/contracts/task-store-v1.md):
- Kullanıcı-görünür tek görev kaynağı canonical panel dokümanıdır:
  ``<base>/tasks.json`` (``{"v": 1, "tasks": [...], "events": [...]}``).
- TaskEngine deposu (``<base>/tasks/tasks.json``) çalıştırma günlüğüdür;
  kullanıcı yüzeyleri onu doğrudan okumaz. Her engine görevi canonical
  listeye ``engine-<task_id>`` kimlikli tek satır yansıtır.
- Sandbox çalıştırmaları canonical listeye yansımaz.

Bu modül yalnız canonical dokümana yazar; engine deposuna dokunmaz.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

ENGINE_TASK_ID_PREFIX = "engine-"

# Engine durum sözlüğü → canonical (active|done) eşlemesi. Arşiv ve çöp,
# satırın listeden kaldırılmasıyla temsil edilir (panel delete ile hizalı).
_DONE_STATUSES = {"tamamlandi"}


def canonical_tasks_file(base_dir: Path | str) -> Path:
    return Path(base_dir) / "tasks.json"


def engine_row_id(task_id: int | str) -> str:
    return f"{ENGINE_TASK_ID_PREFIX}{task_id}"


def _read_doc(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"v": 1, "tasks": [], "events": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        # Bozuk canonical dokümanın üstüne yazıp veri kaybetmeyelim.
        raise
    if not isinstance(data, dict):
        raise ValueError("canonical tasks.json bir obje değil")
    data.setdefault("v", 1)
    if not isinstance(data.get("tasks"), list):
        data["tasks"] = []
    if not isinstance(data.get("events"), list):
        data["events"] = []
    return data


def _write_doc(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="tasks.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(doc, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def engine_task_to_row(task: dict[str, Any]) -> dict[str, Any] | None:
    """TaskRecord.to_dict() çıktısını canonical satıra çevirir.

    Arşivli görev satır üretmez (None) — listeden kaldırılması beklenir.
    """
    task_id = task.get("task_id")
    if task_id is None:
        return None
    if task.get("archived"):
        return None
    title = str(task.get("title") or "").strip() or f"Görev {task_id}"
    status = "done" if str(task.get("status") or "") in _DONE_STATUSES else "active"
    row: dict[str, Any] = {
        "id": engine_row_id(task_id),
        "title": title,
        "status": status,
        "source": "engine",
    }
    created = task.get("created_at")
    if created:
        row["createdAt"] = str(created)
    return row


def upsert_engine_task(base_dir: Path | str, task: dict[str, Any]) -> bool:
    """Engine görevini canonical listeye yansıtır; satır değişmediyse yazmaz."""
    row = engine_task_to_row(task)
    if row is None:
        task_id = task.get("task_id")
        return remove_engine_task(base_dir, task_id) if task_id is not None else False
    path = canonical_tasks_file(base_dir)
    doc = _read_doc(path)
    tasks = doc["tasks"]
    for index, existing in enumerate(tasks):
        if isinstance(existing, dict) and existing.get("id") == row["id"]:
            merged = {**existing, **row}
            if merged == existing:
                return False
            tasks[index] = merged
            _write_doc(path, doc)
            return True
    tasks.append(row)
    _write_doc(path, doc)
    return True


def remove_engine_task(base_dir: Path | str, task_id: int | str) -> bool:
    """Çöpe/arşive giden engine görevinin canonical satırını kaldırır."""
    path = canonical_tasks_file(base_dir)
    if not path.is_file():
        return False
    doc = _read_doc(path)
    row_id = engine_row_id(task_id)
    kept = [t for t in doc["tasks"] if not (isinstance(t, dict) and t.get("id") == row_id)]
    if len(kept) == len(doc["tasks"]):
        return False
    doc["tasks"] = kept
    _write_doc(path, doc)
    return True


def migrate_engine_tasks(engine_tasks_file: Path | str, base_dir: Path | str) -> int:
    """Tek seferlik göç: mevcut engine görevlerini canonical listeye yansıtır.

    Idempotenttir — ikinci çalıştırma değişiklik üretmez. Dönüş: değişen
    satır sayısı.
    """
    engine_path = Path(engine_tasks_file)
    if not engine_path.is_file():
        return 0
    try:
        data = json.loads(engine_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return 0
    changed = 0
    for task in data.get("tasks", []):
        if isinstance(task, dict) and upsert_engine_task(base_dir, task):
            changed += 1
    return changed
