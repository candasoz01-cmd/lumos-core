"""
Görev kaydı, adımlar, kalıcı depolama ve yürütme mantığı.
İlk sürüm: dış araçlara bağlanmadan, adımları sıralayıp simüle/uygula.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from task_engine.profiles import (
    STEP_TYPE_ANALYZE,
    STEP_TYPE_READ,
    STEP_TYPE_SAFE_LOCAL,
    is_allowed_for_profile,
    is_safe_step_kind,
)

# Adım durumları
STEP_PENDING = "bekliyor"
STEP_RUNNING = "calisiyor"
STEP_COMPLETED = "tamamlandi"
STEP_ERROR = "hata"
STEP_STOPPED = "durdu"

# Görev durumları
TASK_PENDING = "bekliyor"
TASK_RUNNING = "calisiyor"
TASK_COMPLETED = "tamamlandi"
TASK_ERROR = "hata"
TASK_STOPPED = "durdu"


@dataclass
class TaskStep:
    """Tek adım: açıklama, durum, tür (güvenlik için), çıktı/hata."""
    title: str
    status: str = STEP_PENDING
    kind: str = STEP_TYPE_ANALYZE  # analyze, read, safe_local, ...
    output: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "status": self.status, "kind": self.kind, "output": self.output, "error": self.error}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TaskStep:
        return cls(
            title=str(d.get("title", "")),
            status=str(d.get("status", STEP_PENDING)),
            kind=str(d.get("kind", STEP_TYPE_ANALYZE)),
            output=str(d.get("output", "")),
            error=str(d.get("error", "")),
        )


@dataclass
class TaskRecord:
    """Görev kaydı: id, başlık, açıklama, zaman, mod, izin profili, adımlar, durum, özet, hata."""
    task_id: int
    title: str
    description: str
    created_at: str  # ISO format
    mode: str = "guvenli_yurut"
    permission_profile: str = "guvenli_yurut"
    steps: list[TaskStep] = field(default_factory=list)
    status: str = TASK_PENDING
    summary: str = ""
    error_summary: str = ""
    completed_at: str = ""
    last_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at,
            "mode": self.mode,
            "permission_profile": self.permission_profile,
            "steps": [st.to_dict() for st in self.steps],
            "status": self.status,
            "summary": self.summary,
            "error_summary": self.error_summary,
            "completed_at": self.completed_at,
            "last_output": self.last_output,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TaskRecord:
        steps = [TaskStep.from_dict(s) for s in d.get("steps", [])]
        return cls(
            task_id=int(d.get("task_id", 0)),
            title=str(d.get("title", "")),
            description=str(d.get("description", "")),
            created_at=str(d.get("created_at", "")),
            mode=str(d.get("mode", "guvenli_yurut")),
            permission_profile=str(d.get("permission_profile", "guvenli_yurut")),
            steps=steps,
            status=str(d.get("status", TASK_PENDING)),
            summary=str(d.get("summary", "")),
            error_summary=str(d.get("error_summary", "")),
            completed_at=str(d.get("completed_at", "")),
            last_output=str(d.get("last_output", "")),
        )


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _break_into_steps(description: str) -> list[TaskStep]:
    """
    Görev açıklamasından makul alt adımlar üret.
    İlk sürüm: basit sabit mantık — "kontrol et", "özet ver" gibi ifadeleri adıma çevir.
    """
    d = (description or "").strip().lower()
    steps: list[TaskStep] = []
    # Not sistemi / özet talebi
    if "not" in d or "özet" in d or "ozet" in d or "kontrol" in d:
        steps.append(TaskStep("Not sistemini kontrol et", kind=STEP_TYPE_READ))
        steps.append(TaskStep("Sonuçları analiz et", kind=STEP_TYPE_ANALYZE))
        steps.append(TaskStep("Kısa özet hazırla", kind=STEP_TYPE_ANALYZE))
    # Genel "sistem kontrol" veya boş
    if not steps:
        steps.append(TaskStep("Görevi analiz et", kind=STEP_TYPE_ANALYZE))
        steps.append(TaskStep("Adımları planla", kind=STEP_TYPE_ANALYZE))
        steps.append(TaskStep("Sonucu raporla", kind=STEP_TYPE_ANALYZE))
    return steps


class TaskStore:
    """Kalıcı görev kaydı: .lumos/tasks.json."""
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self._file = self.base_dir / "tasks.json"
        self._tasks: list[TaskRecord] = []
        self._next_id = 1
        self._load()

    def _load(self) -> None:
        if not self._file.exists():
            self._tasks = []
            self._next_id = 1
            return
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
            self._tasks = [TaskRecord.from_dict(t) for t in data.get("tasks", [])]
            self._next_id = int(data.get("next_id", 1))
            if self._tasks:
                self._next_id = max(self._next_id, max(t.task_id for t in self._tasks) + 1)
        except Exception:
            self._tasks = []
            self._next_id = 1

    def _save(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        data = {"tasks": [t.to_dict() for t in self._tasks], "next_id": self._next_id}
        self._file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def create(self, title: str, description: str, permission_profile: str) -> TaskRecord:
        task = TaskRecord(
            task_id=self._next_id,
            title=title or description[:80] or "Görev",
            description=description,
            created_at=_now_iso(),
            permission_profile=permission_profile,
            mode=permission_profile,
            steps=_break_into_steps(description),
            status=TASK_PENDING,
        )
        self._next_id += 1
        self._tasks.append(task)
        self._save()
        return task

    def get(self, task_id: int) -> TaskRecord | None:
        for t in self._tasks:
            if t.task_id == task_id:
                return t
        return None

    def list_all(self) -> list[TaskRecord]:
        return list(self._tasks)

    def update(self, task: TaskRecord) -> None:
        for i, t in enumerate(self._tasks):
            if t.task_id == task.task_id:
                self._tasks[i] = task
                self._save()
                return
        self._tasks.append(task)
        self._save()


class TaskEngine:
    """
    Görev yürütme: adımları sırayla işle (simüle/uygula),
    yetki profili ve genel onayı dikkate al.
    """
    def __init__(
        self,
        store: TaskStore,
        permission_profile: str,
        general_approval: bool,
    ) -> None:
        self.store = store
        self.permission_profile = permission_profile
        self.general_approval = general_approval

    def run_task(self, task_id: int) -> tuple[bool, str]:
        """
        Görevi çalıştır. Sonuç: (başarılı mı, kısa mesaj).
        """
        task = self.store.get(task_id)
        if not task:
            return False, "Görev bulunamadı."
        if task.status not in (TASK_PENDING, TASK_ERROR, TASK_STOPPED):
            return False, f"Görev zaten {task.status}."
        task.status = TASK_RUNNING
        self.store.update(task)
        start = time.time()
        completed = 0
        last_error_step: str | None = None
        try:
            for i, step in enumerate(task.steps):
                if not is_allowed_for_profile(
                    self.permission_profile, step.kind, self.general_approval
                ):
                    step.status = STEP_STOPPED
                    step.error = "Bu adım yetki profili veya genel onay kapsamında değil."
                    task.error_summary = step.error
                    task.status = TASK_STOPPED
                    self.store.update(task)
                    return False, f"Adım {i+1} izin dışı: {step.title}"
                step.status = STEP_RUNNING
                self.store.update(task)
                # Yürüt (simüle veya gerçek)
                ok, out, err = self._execute_step(step, task)
                step.output = out or ""
                step.error = err or ""
                step.status = STEP_COMPLETED if ok else STEP_ERROR
                if ok:
                    completed += 1
                else:
                    last_error_step = step.title
                    task.status = TASK_ERROR
                    task.error_summary = err or step.title
                    self.store.update(task)
                    elapsed = time.time() - start
                    return False, f"Adım {i+1} hata: {err or step.title} (geçen süre: {elapsed:.1f}s)"
                self.store.update(task)
            task.status = TASK_COMPLETED
            task.completed_at = _now_iso()
            task.summary = self._make_summary(task, completed, time.time() - start)
            task.last_output = task.summary
            self.store.update(task)
            return True, task.summary
        except Exception as e:
            task.status = TASK_ERROR
            task.error_summary = str(e)[:200]
            self.store.update(task)
            return False, str(e)[:200]

    def _execute_step(self, step: TaskStep, task: TaskRecord) -> tuple[bool, str, str]:
        """
        Tek adımı yürüt. İlk sürüm: gerçek dış araç yok; simüle et.
        """
        title = (step.title or "").lower()
        if "not" in title or "kontrol" in title:
            return True, "Not sistemi kontrol edildi (simüle). Kayıtlı not sayısı ve durum okundu.", ""
        if "analiz" in title:
            return True, "Analiz tamamlandı.", ""
        if "planla" in title:
            return True, "Adımlar planlandı.", ""
        if "özet" in title or "ozet" in title or "raporla" in title:
            return True, "Kısa özet hazırlandı.", ""
        return True, "Adım tamamlandı.", ""

    def _make_summary(self, task: TaskRecord, completed: int, elapsed: float) -> str:
        parts = [
            f"Görev: {task.status}",
            f"Geçen süre: {elapsed:.1f}s",
            f"Tamamlanan adım: {completed}/{len(task.steps)}",
        ]
        if task.error_summary:
            parts.append(f"Hata: {task.error_summary}")
        parts.append(task.description[:100] + ("..." if len(task.description) > 100 else ""))
        return "\n".join(parts)

    def cancel_task(self, task_id: int) -> tuple[bool, str]:
        task = self.store.get(task_id)
        if not task:
            return False, "Görev bulunamadı."
        if task.status in (TASK_COMPLETED, TASK_STOPPED):
            return False, f"Görev zaten {task.status}."
        task.status = TASK_STOPPED
        for s in task.steps:
            if s.status == STEP_PENDING:
                s.status = STEP_STOPPED
            elif s.status == STEP_RUNNING:
                s.status = STEP_STOPPED
        self.store.update(task)
        return True, "Görev iptal edildi."
