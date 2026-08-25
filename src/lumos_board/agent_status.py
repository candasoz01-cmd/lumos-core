"""KA-001 ikinci dilim: Lumos Board için salt-okunur Agent Status projeksiyonu.

Veri modeli, doğrulama, legacy normalizasyon ve sahiplik-çakışması semantiği
`core.agent_status_contract` (canonical v1 sözleşmesi) tarafından tanımlanır ve
buradan yalnız TÜKETİLİR — bu modül şemayı yeniden tanımlamaz.

Bu katmanın kendi sorumlulukları:
- Açıkça kayıtlı çoklu kaynak dizinlerinin birleştirilmesi (otomatik keşif yok).
- Dosya güvenliği: symlink ve boyut sınırı dışındaki dosyalar atlanır.
- Kaynak/kayıt hata izolasyonu: tek bozuk dosya veya kaynak diğerlerini düşürmez.
- Görünürlük sunumu: Board durum sözlüğü eşlemesi, sır maskeleme, stale ve
  truncation sinyalleri.

Hiçbir dosyaya yazılmaz; yeni store, writer, endpoint veya orkestrasyon yoktur.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from core.agent_status_contract import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    AgentStatusRecord,
    detect_ownership_conflicts,
    record_from_payload,
    resolve_status_payload,
)

AGENT_STATUS_PROJECTION_SCHEMA = "lumos.board.agent_status_projection.v1"
OWNER_CONFLICT = "OWNER_CONFLICT"
AGENT_STATUS_GLOB = "agent_status_*.json"
MAX_STATUS_FILE_BYTES = 256 * 1024
MAX_RECORDS_DEFAULT = 50
TASK_TITLE_LIMIT = 160

_SECRET_PATTERNS = (
    re.compile(
        r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"\b(?:api[_ -]?key|token|secret|password)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
)


class AgentState(str, Enum):
    """Board görünürlük sözlüğü (ADR-008 taksonomisi); kontrol yetkisi vermez."""

    WORKING = "WORKING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"


# Canonical sözleşme statülerinden Board görünürlük durumuna eşleme.
# Sözlük genişletme (IDLE, WAITING_APPROVAL) sözleşme v2 konusudur; burada
# uydurulmaz.
_STATE_BY_STATUS = {
    STATUS_RUNNING: AgentState.WORKING,
    STATUS_COMPLETED: AgentState.COMPLETED,
    STATUS_FAILED: AgentState.BLOCKED,
}


@dataclass(frozen=True)
class ProjectedAgentStatus:
    """Tek kaydın Board'a yansıyan hali: canonical kayıt + sunum alanları."""

    record: AgentStatusRecord
    source: str
    state: AgentState
    task_title: str
    stale: bool
    display_ref: str

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.record.version,
            "agent_id": self.record.agent_id,
            "job_id": self.record.job_id,
            "status": self.record.status,
            "owner": self.record.owner,
            "started_at": self.record.started_at,
            "updated_at": self.record.updated_at,
            "evidence_ref": self.display_ref,
            "progress": self.record.progress,
            "message": self.task_title or (self.record.message or ""),
            "source": self.source,
            "state": self.state.value,
            "stale": self.stale,
        }


@dataclass(frozen=True)
class ProjectedConflict:
    """Canonical çakışma tespiti + kaynak/kanıt zenginleştirmesi."""

    job_id: str
    owners: tuple[str, ...]
    sources: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    conflict_type: str = OWNER_CONFLICT

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.conflict_type,
            "job_id": self.job_id,
            "owners": list(self.owners),
            "sources": list(self.sources),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class AgentStatusProjection:
    """Okuma sonucu + açık tamlık sinyalleri."""

    records: tuple[ProjectedAgentStatus, ...]
    conflicts: tuple[ProjectedConflict, ...]
    sources_scanned: int
    invalid_records: int
    read_errors: tuple[str, ...]
    truncated: bool
    schema: str = AGENT_STATUS_PROJECTION_SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "read_only": True,
            "sources_scanned": self.sources_scanned,
            "invalid_records": self.invalid_records,
            "read_errors": list(self.read_errors),
            "has_conflicts": bool(self.conflicts),
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
            "truncated": self.truncated,
            "records": [record.to_dict() for record in self.records],
        }


def mask_secretlike(value: object, *, limit: int = TASK_TITLE_LIMIT) -> str:
    """Serbest metindeki sır benzeri değerleri maskeler ve uzunluğu sınırlar."""
    text = " ".join(str(value or "").split())
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text[:limit]


def _parse_datetime(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _task_title(payload: Mapping[str, object]) -> str:
    """Sunum başlığı: tipli kayıtta message, legacy kayıtta final_report.task."""
    final_report = payload.get("final_report")
    if isinstance(final_report, Mapping) and final_report.get("task"):
        return mask_secretlike(final_report.get("task"))
    return mask_secretlike(payload.get("message") or payload.get("phase"))


def read_agent_status_projection(
    sources: Mapping[str, Path | str],
    *,
    limit: int = MAX_RECORDS_DEFAULT,
    stale_after_seconds: float = 120.0,
    now: datetime | None = None,
) -> AgentStatusProjection:
    """Kayıtlı durum dizinlerini salt-okunur tarar ve Board görünümüne çevirir.

    Kaynaklar açıkça verilir; otomatik keşif yoktur. Symlink, boyut sınırını
    aşan dosya, bozuk JSON ve sözleşmeye göre geçersiz kayıtlar sayılarak
    atlanır; tek dosya veya tek kaynak hatası diğerlerini düşürmez. Aynı
    ``(source, agent_id)`` için yalnız en yeni kayıt yansıtılır.
    """
    safe_limit = max(0, int(limit))
    safe_stale_after = max(0.0, float(stale_after_seconds))
    read_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    by_identity: dict[tuple[str, str], tuple[datetime, ProjectedAgentStatus]] = {}
    invalid_records = 0
    read_errors: list[str] = []
    sources_scanned = 0

    for raw_source, raw_directory in sorted(sources.items(), key=lambda i: str(i[0])):
        source = mask_secretlike(raw_source, limit=80)
        directory = Path(raw_directory)
        if not source or not directory.is_dir() or directory.is_symlink():
            continue
        sources_scanned += 1

        # Path.glob izin hatalarını sessizce yutar; listeleme hatasının
        # raporlanabilmesi için os.listdir kullanılır.
        try:
            names = sorted(os.listdir(directory))
        except OSError:
            read_errors.append(f"{source}/*")
            continue
        status_paths = [
            directory / name for name in names if fnmatch.fnmatch(name, AGENT_STATUS_GLOB)
        ]

        for path in status_paths:
            try:
                if path.is_symlink() or not path.is_file():
                    invalid_records += 1
                    continue
                stat = path.stat()
                if stat.st_size > MAX_STATUS_FILE_BYTES:
                    invalid_records += 1
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                invalid_records += 1
                read_errors.append(f"{source}/{path.name}")
                continue
            if not isinstance(payload, Mapping):
                invalid_records += 1
                continue

            # Tipleme/doğrulama/normalize ve sürüm kuralı (versionsuz → v1
            # normalize, açık 1/2 → kendi kuralları, diğer açık sürüm fail
            # closed) canonical sözleşmenin işidir.
            try:
                typed_payload = resolve_status_payload(dict(payload), source_path=path)
                record = record_from_payload(typed_payload)
            except ValueError:
                invalid_records += 1
                continue

            started = _parse_datetime(record.started_at)
            observed = _parse_datetime(record.updated_at)
            if started is not None and observed is not None and observed < started:
                # Zaman sırası bozuk kayıt görünürlüğe taşınmaz (kaynak hijyeni).
                invalid_records += 1
                continue
            observed = observed or datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            )
            age_seconds = max(0.0, (read_now - observed).total_seconds())

            projected = ProjectedAgentStatus(
                record=record,
                source=source,
                state=_STATE_BY_STATUS.get(record.status, AgentState.UNKNOWN),
                task_title=_task_title(payload),
                stale=age_seconds > safe_stale_after,
                display_ref=f"{source}/{path.name}",
            )
            identity = (source, record.agent_id)
            current = by_identity.get(identity)
            if current is None or observed > current[0]:
                by_identity[identity] = (observed, projected)

    ordered = [
        item[1]
        for item in sorted(
            by_identity.values(),
            key=lambda item: (item[0], item[1].source, item[1].record.agent_id),
            reverse=True,
        )
    ]

    core_conflicts = detect_ownership_conflicts([p.record for p in ordered])
    projected_by_job: dict[str, list[ProjectedAgentStatus]] = {}
    for projected in ordered:
        projected_by_job.setdefault(projected.record.job_id, []).append(projected)
    conflicts = tuple(
        ProjectedConflict(
            job_id=conflict.job_id,
            owners=conflict.owners,
            sources=tuple(
                sorted({p.source for p in projected_by_job.get(conflict.job_id, [])})
            ),
            evidence_refs=tuple(
                sorted(p.display_ref for p in projected_by_job.get(conflict.job_id, []))
            ),
        )
        for conflict in core_conflicts
    )

    return AgentStatusProjection(
        records=tuple(ordered[:safe_limit]),
        conflicts=conflicts,
        sources_scanned=sources_scanned,
        invalid_records=invalid_records,
        read_errors=tuple(sorted(read_errors)),
        truncated=len(ordered) > safe_limit,
    )
