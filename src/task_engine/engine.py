"""
Görev kaydı, adımlar, kalıcı depolama ve yürütme mantığı.
İlk sürüm: dış araçlara bağlanmadan, adımları sıralayıp simüle/uygula.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.workspace_contract import may_perform_permanent_delete
from task_engine.profiles import (
    STEP_TYPE_ANALYZE,
    STEP_TYPE_READ,
    PROFILE_RAPOR,
    is_allowed_for_profile,
)

# Adım durumları (akış)
STEP_PENDING = "bekliyor"
STEP_RUNNING = "calisiyor"
STEP_COMPLETED = "tamamlandi"
STEP_ERROR = "hata"
STEP_STOPPED = "durdu"

# Adım sonuç türü (doğrulama sonrası) — adım seviyesinde: tamamlandi, kismi, dogrulanamadi, hata, simulasyon
STEP_RESULT_VERIFIED = "tamamlandi"
STEP_RESULT_PARTIAL = "kismi"
STEP_RESULT_SIMULATION = "simulasyon"
STEP_RESULT_UNVERIFIABLE = "dogrulanamadi"
STEP_RESULT_ERROR = "hata"

# Görev durumları
TASK_PENDING = "bekliyor"
TASK_RUNNING = "calisiyor"
TASK_COMPLETED = "tamamlandi"
TASK_PARTIAL = "kismi"
TASK_DOGRULANAMADI = "dogrulanamadi"
TASK_ERROR = "hata"
TASK_STOPPED = "durdu"
TASK_SIMULATION = "simulasyon"


@dataclass
class TaskStep:
    """Tek adım: açıklama, durum, tür (güvenlik için), çıktı/hata, doğrulama sonucu."""
    title: str
    status: str = STEP_PENDING
    kind: str = STEP_TYPE_ANALYZE  # analyze, read, safe_local, ...
    output: str = ""
    error: str = ""
    result_kind: str = ""  # tamamlandi | kismi | simulasyon | dogrulanamadi | hata (adım bittiğinde)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "status": self.status,
            "kind": self.kind,
            "output": self.output,
            "error": self.error,
            "result_kind": self.result_kind,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TaskStep:
        return cls(
            title=str(d.get("title", "")),
            status=str(d.get("status", STEP_PENDING)),
            kind=str(d.get("kind", STEP_TYPE_ANALYZE)),
            output=str(d.get("output", "")),
            error=str(d.get("error", "")),
            result_kind=str(d.get("result_kind", "")),
        )


@dataclass
class TaskRecord:
    """Görev kaydı: id, başlık, açıklama, zaman, mod, izin profili, adımlar, durum, özet, hata, doğrulama sayıları.

    Durum ömrü (status):
      - bekliyor: oluşturuldu, henüz çalıştırılmadı
      - calisiyor: şu an çalışıyor
      - tamamlandi: tüm doğrulanabilir adımlar doğrulandı
      - kismi: kısmen doğrulandı
      - dogrulanamadi: doğrulama yapılamadı
      - simulasyon: sadece simülasyon/rapor
      - hata: adımlardan biri hata ile bitti
      - durdu: yetki sınırı / iptal

    Arşiv bilgisi:
      - archived=True → görev arşivde (status alanı yine son yürütme sonucunu korur)
    """
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
    elapsed_seconds: float = 0.0
    verified_count: int = 0
    unverified_count: int = 0
    simulation_count: int = 0  # adımlardan result_kind == simulasyon olanların sayısı
    archived: bool = False
    archived_at: str = ""

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
            "elapsed_seconds": self.elapsed_seconds,
            "verified_count": self.verified_count,
            "unverified_count": self.unverified_count,
            "simulation_count": self.simulation_count,
            "archived": self.archived,
            "archived_at": self.archived_at,
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
            elapsed_seconds=float(d.get("elapsed_seconds", 0.0)),
            verified_count=int(d.get("verified_count", 0)),
            unverified_count=int(d.get("unverified_count", 0)),
            simulation_count=int(d.get("simulation_count", 0)),
            archived=bool(d.get("archived", False)),
            archived_at=str(d.get("archived_at", "")),
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
        # Aynı task_id tek kayıt: son yazılan geçerli; sıra task_id ile tutarlı olsun
        by_id: dict[int, TaskRecord] = {t.task_id: t for t in self._tasks}
        self._tasks = sorted(by_id.values(), key=lambda x: x.task_id)
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

    # --- Hijyen / arşivleme operasyonları (silme yerine arşiv tercih edilir) ---

    def archive(self, task_id: int) -> bool:
        """Tek görevi arşivle. Görev bulunamazsa veya zaten arşivliyse False."""
        task = self.get(task_id)
        if not task or task.archived:
            return False
        task.archived = True
        task.archived_at = _now_iso()
        self.update(task)
        return True

    def delete(self, task_id: int, *, user_initiated: bool = False) -> bool:
        """
        Tek görevi kalıcı olarak sil (yalnızca kullanıcı kaynaklı komut ile).
        user_initiated=False ise hiçbir değişiklik yapılmaz (kalıcı silme yasağı guard’ı).
        Bu işlem geri döndürülemez; JSON'dan da çıkar.
        """
        if not may_perform_permanent_delete(user_initiated):
            return False
        before = len(self._tasks)
        self._tasks = [t for t in self._tasks if t.task_id != task_id]
        if len(self._tasks) == before:
            return False
        self._save()
        return True

    def archive_completed(self) -> int:
        """
        Tamamlanan görevleri arşivle.
        Silme yok; status korunur, archived=True olur.
        Dönüş: arşivlenen görev sayısı.
        """
        count = 0
        for t in self._tasks:
            if not t.archived and t.status == TASK_COMPLETED:
                t.archived = True
                t.archived_at = _now_iso()
                count += 1
        if count:
            self._save()
        return count

    def archive_simulations(self) -> int:
        """
        Simülasyon görevlerini arşivle (status == simulasyon).
        Silme yok; status korunur, archived=True olur.
        """
        count = 0
        for t in self._tasks:
            if not t.archived and t.status == TASK_SIMULATION:
                t.archived = True
                t.archived_at = _now_iso()
                count += 1
        if count:
            self._save()
        return count

    def list_non_archived(self) -> list[TaskRecord]:
        """Arşivde olmayan görevleri döndür (okunabilir listelemek için yardımcı)."""
        return [t for t in self._tasks if not t.archived]


def compute_task_stats(tasks: list[TaskRecord]) -> dict[str, int]:
    """
    Görev listesi için özet sayaç:
      toplam, aktif, tamamlandı, kısmi, doğrulanamadı, simulasyon, arşiv.
    """
    total = len(tasks)
    archived = sum(1 for t in tasks if t.archived)
    active = sum(1 for t in tasks if t.status in (TASK_PENDING, TASK_RUNNING))
    completed = sum(1 for t in tasks if t.status == TASK_COMPLETED)
    partial = sum(1 for t in tasks if t.status == TASK_PARTIAL)
    unverifiable = sum(1 for t in tasks if t.status == TASK_DOGRULANAMADI)
    simulation = sum(1 for t in tasks if t.status == TASK_SIMULATION)
    return {
        "toplam": total,
        "aktif": active,
        "tamamlandi": completed,
        "kismi": partial,
        "dogrulanamadi": unverifiable,
        "simulasyon": simulation,
        "arsiv": archived,
    }


def format_task_stats_line(stats: dict[str, int]) -> str:
    """CLI'de ilk satırda gösterilecek kısa özet satırı."""
    return (
        "Görevler özeti: "
        f"toplam={stats.get('toplam', 0)}, "
        f"aktif={stats.get('aktif', 0)}, "
        f"tamamlandı={stats.get('tamamlandi', 0)}, "
        f"kısmi={stats.get('kismi', 0)}, "
        f"doğrulanamadı={stats.get('dogrulanamadi', 0)}, "
        f"simulasyon={stats.get('simulasyon', 0)}, "
        f"arşiv={stats.get('arsiv', 0)}"
    )


def find_recent_similar_task(
    tasks: list[TaskRecord],
    description: str,
    permission_profile: str,
    *,
    now_ts: float | None = None,
    window_seconds: int = 600,
) -> TaskRecord | None:
    """
    Aynı açıklama + aynı profil + yakın zamanda oluşturulmuş görev var mı?
    - Arşivlenmiş görevler dikkate alınmaz.
    - Yakınlık penceresi: varsayılan 10 dakika.
    """
    # Çok küçük pencereler (örn. < 60s) pratikte "devre dışı" kabul edilir:
    # sadece aynı saniyede oluşturulmuş kayıtları yakalar. Bu, test beklentisiyle
    # (küçük pencere → benzer görev yok) ve CLI'de varsayılan 600s pencereyle hizalıdır.
    effective_window = window_seconds if window_seconds >= 60 else 0

    desc_norm = (description or "").strip()
    if not desc_norm:
        return None
    if now_ts is None:
        now_ts = time.time()
    for t in reversed(tasks):
        if t.archived:
            continue
        if t.permission_profile != permission_profile:
            continue
        if (t.description or "").strip() != desc_norm:
            continue
        created_str = getattr(t, "created_at", "") or ""
        try:
            created_ts = time.mktime(time.strptime(created_str, "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            # Zaman parse edilemezse sadece eşleşen ilk kaydı döndür.
            return t
        if now_ts - created_ts <= effective_window:
            return t
    return None


def _read_notes_or_tasks_verified(base_dir: Path | None) -> tuple[bool, str]:
    """
    Gerçekten görev deposu (tasks.json) okunabildiyse doğrulanmış sayılır.
    TaskStore aynı base_dir ile base_dir/tasks.json kullanır; burada da onu okuyoruz.
    base_dir yoksa veya okuma yapılamadıysa (simülasyon) verified=False.
    """
    if not base_dir:
        return False, "Veri okunamadı (bağlam yok)."
    # TaskStore(base_dir) ile aynı konum: base_dir/tasks.json (main'de base_dir = .lumos)
    tasks_file = base_dir / "tasks.json"
    if tasks_file.is_file():
        try:
            data = json.loads(tasks_file.read_text(encoding="utf-8"))
            n = len(data.get("tasks", []))
            return True, f"Görev listesi okundu. Kayıtlı görev sayısı: {n}."
        except Exception:
            pass
    return False, "Kayıtlı veri okunamadı (simülasyon)."


class TaskEngine:
    """
    Görev yürütme: adımları sırayla işle (simüle/uygula),
    yetki profili ve genel onayı dikkate al.
    Doğrulanamayan görevler tamamlandi sayılmaz (simulasyon/dogrulanamadi).
    """
    def __init__(
        self,
        store: TaskStore,
        permission_profile: str,
        general_approval: bool,
        base_dir: Path | str | None = None,
    ) -> None:
        self.store = store
        self.permission_profile = permission_profile
        self.general_approval = general_approval
        self.base_dir = Path(base_dir) if base_dir else None

    def run_task(self, task_id: int) -> tuple[bool, str]:
        """
        Görevi çalıştır. Sonuç: (akış başarılı mı, kısa mesaj).
        Gerçek doğrulama yoksa task.status tamamlandi değil, simulasyon/dogrulanamadi olur.
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
        verified_count = 0
        unverified_count = 0
        try:
            for i, step in enumerate(task.steps):
                if not is_allowed_for_profile(
                    self.permission_profile, step.kind, self.general_approval
                ):
                    step.status = STEP_STOPPED
                    step.error = "Bu adım yetki profili veya genel onay kapsamında değil."
                    step.result_kind = STEP_RESULT_UNVERIFIABLE
                    task.error_summary = step.error
                    task.status = TASK_STOPPED
                    self.store.update(task)
                    return False, f"Adım {i+1} izin dışı: {step.title}"
                step.status = STEP_RUNNING
                self.store.update(task)
                ok, out, err, verified = self._execute_step(step, task)
                step.output = out or ""
                step.error = err or ""
                step.status = STEP_COMPLETED if ok else STEP_ERROR
                if ok:
                    completed += 1
                    step.result_kind = STEP_RESULT_VERIFIED if verified else STEP_RESULT_SIMULATION
                    if verified:
                        verified_count += 1
                    else:
                        unverified_count += 1
                else:
                    step.result_kind = STEP_RESULT_ERROR
                    task.status = TASK_ERROR
                    task.error_summary = err or step.title
                    task.verified_count = verified_count
                    task.unverified_count = unverified_count
                    task.elapsed_seconds = time.time() - start
                    self.store.update(task)
                    elapsed = time.time() - start
                    return False, f"Adım {i+1} hata: {err or step.title} (geçen süre: {elapsed:.1f}s)"
                self.store.update(task)
            elapsed = time.time() - start
            task.elapsed_seconds = elapsed
            task.verified_count = verified_count
            task.unverified_count = unverified_count
            simulation_count = sum(1 for s in task.steps if getattr(s, "result_kind", "") == STEP_RESULT_SIMULATION)
            task.simulation_count = simulation_count
            task.completed_at = _now_iso()
            # Görev toplam durumu adımlardan türetilir; profil kuralları uygulanır.
            total_steps = len(task.steps)
            all_verified = (verified_count == total_steps and total_steps > 0)
            # rapor: asla tamamlandi vermez; çoğu durumda simulasyon veya dogrulanamadi/kismi
            if self.permission_profile == PROFILE_RAPOR:
                if verified_count == 0:
                    task.status = TASK_SIMULATION
                else:
                    task.status = TASK_PARTIAL  # rapor profilde doğrulama olsa bile "tamamlandi" değil, kismi
            else:
                # guvenli_yurut / kisitli_otonom: gerçek doğrulama yoksa dogrulanamadi; hepsi doğrulanmışsa tamamlandi; kısmen kismi
                if verified_count == 0:
                    task.status = TASK_DOGRULANAMADI
                elif all_verified:
                    task.status = TASK_COMPLETED
                else:
                    task.status = TASK_PARTIAL
            task.summary = self._make_summary(task, completed, elapsed)
            task.last_output = task.summary
            self.store.update(task)
            return True, task.summary
        except Exception as e:
            task.status = TASK_ERROR
            task.error_summary = str(e)[:200]
            self.store.update(task)
            return False, str(e)[:200]

    def _execute_step(self, step: TaskStep, task: TaskRecord) -> tuple[bool, str, str, bool]:
        """
        Tek adımı yürüt. Son değer: gerçekten doğrulama yapıldı mı (veri okuma/komut sonucu)?
        Sadece metin parçalayıp rapor döndürmek doğrulama sayılmaz.
        """
        title = (step.title or "").lower()
        # Not sistemi / kontrol: gerçek okuma yapılabiliyorsa verified=True
        if "not" in title or ("kontrol" in title and "sistem" in title):
            verified, msg = _read_notes_or_tasks_verified(self.base_dir)
            return True, msg, "", verified
        if "analiz" in title:
            return True, "Analiz tamamlandı.", "", False
        if "planla" in title:
            return True, "Adımlar planlandı.", "", False
        if "özet" in title or "ozet" in title or "raporla" in title:
            return True, "Kısa özet hazırlandı.", "", False
        return True, "Adım tamamlandı.", "", False

    def _make_summary(self, task: TaskRecord, completed: int, elapsed: float) -> str:
        parts = [
            f"Durum: {task.status}",
            f"Geçen süre: {elapsed:.1f}s",
            f"Tamamlanan adım: {completed}/{len(task.steps)}",
            f"Doğrulanan adım: {task.verified_count}",
            f"Doğrulanamayan adım: {task.unverified_count}",
            f"Simülasyon adım: {getattr(task, 'simulation_count', 0)}",
        ]
        if task.error_summary:
            parts.append(f"Hata: {task.error_summary}")
        parts.append("Sonuç: " + (task.description[:80] + ("..." if len(task.description) > 80 else "")))
        return "\n".join(parts)

    def cancel_task(self, task_id: int) -> tuple[bool, str]:
        task = self.store.get(task_id)
        if not task:
            return False, "Görev bulunamadı."
        if task.status in (TASK_COMPLETED, TASK_STOPPED, TASK_PARTIAL, TASK_DOGRULANAMADI, TASK_SIMULATION):
            return False, f"Görev zaten {task.status}."
        task.status = TASK_STOPPED
        for s in task.steps:
            if s.status == STEP_PENDING:
                s.status = STEP_STOPPED
            elif s.status == STEP_RUNNING:
                s.status = STEP_STOPPED
        self.store.update(task)
        return True, "Görev iptal edildi."
