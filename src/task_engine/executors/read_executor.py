"""
Read step executor: read notes/tasks; verified when data read successfully.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from task_engine.action_registry import ExecutionContext

if TYPE_CHECKING:
    from task_engine.engine import TaskRecord, TaskStep


def _read_notes_or_tasks_verified(base_dir: Path | None) -> tuple[bool, str]:
    """
    Gerçekten görev deposu (tasks.json) okunabildiyse doğrulanmış sayılır.
    TaskStore aynı base_dir ile base_dir/tasks.json kullanır; burada da onu okuyoruz.
    base_dir yoksa veya okuma yapılamadıysa (simülasyon) verified=False.
    """
    if not base_dir:
        return False, "Veri okunamadı (bağlam yok)."
    tasks_file = base_dir / "tasks.json"
    if tasks_file.is_file():
        try:
            data = json.loads(tasks_file.read_text(encoding="utf-8"))
            n = len(data.get("tasks", []))
            return True, f"Görev listesi okundu. Kayıtlı görev sayısı: {n}."
        except Exception:
            pass
    return False, "Kayıtlı veri okunamadı (simülasyon)."


def read_executor(
    step: "TaskStep",
    task: "TaskRecord",
    context: ExecutionContext,
) -> tuple[bool, str, str, bool]:
    """Run read step; verified when base_dir and tasks.json read successfully."""
    verified, msg = _read_notes_or_tasks_verified(context.base_dir)
    return True, msg, "", verified
