"""Lumos Board için tipli Agent Status sözleşmesi (v1 + v2) — salt okunur dilim.

Tek şema hem burada hem `docs/contracts/agent-status-v1.md` ve
`docs/contracts/agent-status-v2.md` içinde tanımlıdır; ayrışma olursa doküman
güncellenene kadar bu modül esas alınır.

Sürüm kuralı (agent-status-v2.md § v1 geriye uyumluluk, normatif):
versionsuz kayıt eski format sayılıp v1'e normalize edilir; açık `version: 1`
v1, açık `version: 2` v2 kurallarıyla doğrulanır; başka her açık sürüm fail
closed reddedilir ve asla sessizce eski format sayılmaz.

Kapsam sınırı (reader-v2, bilinçli):
- Yalnız okuma ve normalize etme; hiçbir dosyaya yazılmaz. Yazıcı yoktur —
  yazıcı yetkilendirmesi ayrı onay kapısıdır (agent-status-v2.md
  § Güvenilir-yazıcı sınırı).
- `src/kando/agent_runner.py` üretim davranışı değişmez.
- Yeni mesajlaşma sistemi, event bus, endpoint, kilit veya orkestrasyon yok.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
SCHEMA_VERSION_V2 = 2
SUPPORTED_SCHEMA_VERSIONS = (SCHEMA_VERSION, SCHEMA_VERSION_V2)

STATUS_RUNNING = "running"
STATUS_BLOCKED = "blocked"
STATUS_AWAITING_DECISION = "awaiting_decision"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_UNKNOWN = "unknown"
VALID_STATUSES = (STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED, STATUS_UNKNOWN)
V2_VALID_STATUSES = (
    STATUS_RUNNING,
    STATUS_BLOCKED,
    STATUS_AWAITING_DECISION,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_UNKNOWN,
)

WAIT_REASON_DEPENDENCY = "dependency"
WAIT_REASON_AGENT_RESULT = "agent_result"
WAIT_REASON_EXTERNAL_EVENT = "external_event"
WAIT_REASON_HUMAN_DECISION = "human_decision"

# agent-status-v2.md § wait_reason eşleme kuralları: wait_reason yalnız bekleme
# durumlarında bulunabilir ve zorunludur; human_decision yalnız
# awaiting_decision ile geçerlidir.
WAIT_REASONS_BY_STATUS = {
    STATUS_BLOCKED: (
        WAIT_REASON_DEPENDENCY,
        WAIT_REASON_AGENT_RESULT,
        WAIT_REASON_EXTERNAL_EVENT,
    ),
    STATUS_AWAITING_DECISION: (WAIT_REASON_HUMAN_DECISION,),
}

# Eski agent_status_{job_id}.json dosyaları üretici kimliği taşımaz; tek
# üreticileri agent_runner olduğu için normalize ederken bu kimlik atanır.
LEGACY_AGENT_ID = "kando.agent_runner"

_STATUS_FILE_RE = re.compile(r"^agent_status_(?P<job_id>[0-9a-f]+)\.json$")


@dataclass(frozen=True)
class AgentStatusRecord:
    """Tek bir ajanın tek bir iş üzerindeki durum kaydı (şema v1/v2).

    `wait_reason` ve `decision_ref` yalnız v2 kayıtlarında dolu olabilir; v1
    kayıtlarında her zaman None'dır ve v1'den çıkarım yapılmaz.
    """

    version: int
    agent_id: str
    job_id: str
    status: str
    owner: str
    started_at: str | None
    updated_at: str | None
    evidence_ref: str
    progress: int | None = None
    message: str | None = None
    wait_reason: str | None = None
    decision_ref: str | None = None


@dataclass(frozen=True)
class OwnershipConflict:
    """Aynı job_id'yi birden fazla sahibin iddia etmesi."""

    job_id: str
    owners: tuple[str, ...]


@dataclass
class AgentStatusReadResult:
    """Salt okunur tarama sonucu: geçerli kayıtlar + kayıt üretemeyen dosyalar."""

    records: list[AgentStatusRecord] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def _parse_iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_agent_status_payload(payload: object) -> list[str]:
    """Şema v1'e göre hataların listesini döndürür; boş liste = geçerli."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload_not_object"]
    if payload.get("version") != SCHEMA_VERSION:
        errors.append("version_invalid")
    for key in ("agent_id", "job_id", "owner", "evidence_ref"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key}_missing")
    if payload.get("status") not in VALID_STATUSES:
        errors.append("status_invalid")
    for key in ("started_at", "updated_at"):
        value = payload.get(key)
        if value is not None and (not isinstance(value, str) or not _parse_iso8601(value)):
            errors.append(f"{key}_invalid")
    progress = payload.get("progress")
    if progress is not None and (not isinstance(progress, int) or isinstance(progress, bool) or not 0 <= progress <= 100):
        errors.append("progress_invalid")
    message = payload.get("message")
    if message is not None and not isinstance(message, str):
        errors.append("message_invalid")
    return errors


def validate_agent_status_payload_v2(payload: object) -> list[str]:
    """Şema v2'ye göre hataların listesini döndürür; boş liste = geçerli."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload_not_object"]
    if payload.get("version") != SCHEMA_VERSION_V2:
        errors.append("version_invalid")
    for key in ("agent_id", "job_id", "owner", "evidence_ref"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key}_missing")
    status = payload.get("status")
    if status not in V2_VALID_STATUSES:
        errors.append("status_invalid")
    for key in ("started_at", "updated_at"):
        value = payload.get(key)
        if value is not None and (not isinstance(value, str) or not _parse_iso8601(value)):
            errors.append(f"{key}_invalid")
    progress = payload.get("progress")
    if progress is not None and (not isinstance(progress, int) or isinstance(progress, bool) or not 0 <= progress <= 100):
        errors.append("progress_invalid")
    message = payload.get("message")
    if message is not None and not isinstance(message, str):
        errors.append("message_invalid")
    # Sebepsiz bekleme yasak; bekleme dışı durumda wait_reason bulunamaz.
    wait_reason = payload.get("wait_reason")
    allowed_reasons = WAIT_REASONS_BY_STATUS.get(status)
    if allowed_reasons is not None:
        if wait_reason is None:
            errors.append("wait_reason_missing")
        elif wait_reason not in allowed_reasons:
            errors.append("wait_reason_invalid")
    elif wait_reason is not None:
        errors.append("wait_reason_forbidden")
    # decision_ref zorunlu ⇔ awaiting_decision; boş/jenerik değer geçersiz.
    decision_ref = payload.get("decision_ref")
    if status == STATUS_AWAITING_DECISION:
        if not isinstance(decision_ref, str) or not decision_ref.strip():
            errors.append("decision_ref_missing")
    elif decision_ref is not None:
        errors.append("decision_ref_forbidden")
    return errors


def record_from_payload(payload: dict) -> AgentStatusRecord:
    """Geçerli bir v1/v2 payload'ını tipli kayda çevirir; geçersizse ValueError.

    v1 payload'ları için davranış birebir eskisi gibidir; v2'den v1'e veya
    v1'den v2'ye hiçbir alan çıkarımı yapılmaz.
    """
    if isinstance(payload, dict) and payload.get("version") == SCHEMA_VERSION_V2:
        errors = validate_agent_status_payload_v2(payload)
        if errors:
            raise ValueError(f"agent_status_invalid: {', '.join(errors)}")
        decision_ref = payload.get("decision_ref")
        return AgentStatusRecord(
            version=SCHEMA_VERSION_V2,
            agent_id=payload["agent_id"].strip(),
            job_id=payload["job_id"].strip(),
            status=payload["status"],
            owner=payload["owner"].strip(),
            started_at=payload.get("started_at"),
            updated_at=payload.get("updated_at"),
            evidence_ref=payload["evidence_ref"].strip(),
            progress=payload.get("progress"),
            message=payload.get("message"),
            wait_reason=payload.get("wait_reason"),
            decision_ref=decision_ref.strip() if isinstance(decision_ref, str) else decision_ref,
        )
    errors = validate_agent_status_payload(payload)
    if errors:
        raise ValueError(f"agent_status_invalid: {', '.join(errors)}")
    return AgentStatusRecord(
        version=SCHEMA_VERSION,
        agent_id=payload["agent_id"].strip(),
        job_id=payload["job_id"].strip(),
        status=payload["status"],
        owner=payload["owner"].strip(),
        started_at=payload.get("started_at"),
        updated_at=payload.get("updated_at"),
        evidence_ref=payload["evidence_ref"].strip(),
        progress=payload.get("progress"),
        message=payload.get("message"),
    )


def normalize_legacy_status_payload(payload: dict, *, source_path: Path) -> dict:
    """Eski `agent_status_{job_id}.json` içeriğini v1 payload'ına çevirir.

    Eski dosyalar yalnız job_id/phase/status/final_report/errors taşır; eksik
    alanlar burada üretilir: updated_at dosya mtime'ından, evidence_ref dosya
    yolundan, message phase alanından gelir. started_at eski dosyada yoktur ve
    uydurulmaz — None kalır.
    """
    raw_status = payload.get("status")
    status = raw_status if raw_status in VALID_STATUSES else STATUS_UNKNOWN
    job_id = payload.get("job_id")
    if not isinstance(job_id, str) or not job_id.strip():
        match = _STATUS_FILE_RE.match(source_path.name)
        job_id = match.group("job_id") if match else ""
    try:
        mtime = source_path.stat().st_mtime
        updated_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    except OSError:
        updated_at = None
    phase = payload.get("phase")
    return {
        "version": SCHEMA_VERSION,
        "agent_id": LEGACY_AGENT_ID,
        "job_id": job_id,
        "status": status,
        "owner": LEGACY_AGENT_ID,
        "started_at": None,
        "updated_at": updated_at,
        "evidence_ref": str(source_path),
        "progress": None,
        "message": phase if isinstance(phase, str) and phase else None,
    }


class UnsupportedSchemaVersionError(ValueError):
    """Açık ama desteklenmeyen şema sürümü — fail closed, legacy sanılmaz."""


def resolve_status_payload(payload: dict, *, source_path: Path) -> dict:
    """Sürüm kuralını uygular (agent-status-v2.md § v1 geriye uyumluluk).

    Versionsuz (alan yok veya null) kayıt eski format sayılır ve v1'e
    normalize edilir; açık 1/2 sürümleri olduğu gibi kendi doğrulayıcısına
    gider; başka her açık sürüm UnsupportedSchemaVersionError ile reddedilir.
    """
    version = payload.get("version")
    if version is None:
        return normalize_legacy_status_payload(payload, source_path=source_path)
    if version in SUPPORTED_SCHEMA_VERSIONS:
        return payload
    raise UnsupportedSchemaVersionError(f"version_unsupported: {version!r}")


def load_agent_status_records(outbox_dir: Path) -> AgentStatusReadResult:
    """`agent_status_*.json` dosyalarını salt okunur tarar ve normalize eder.

    Bozuk JSON, dict olmayan içerik, normalize edilemeyen kayıtlar veya
    desteklenmeyen açık şema sürümleri sonucu durdurmaz; dosya adıyla birlikte
    `issues` listesine düşer.
    """
    result = AgentStatusReadResult()
    if not outbox_dir.is_dir():
        return result
    for path in sorted(outbox_dir.glob("agent_status_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            result.issues.append(f"{path.name}: unreadable_or_invalid_json")
            continue
        if not isinstance(payload, dict):
            result.issues.append(f"{path.name}: payload_not_object")
            continue
        try:
            payload = resolve_status_payload(payload, source_path=path)
            result.records.append(record_from_payload(payload))
        except ValueError as e:
            result.issues.append(f"{path.name}: {e}")
    return result


def detect_ownership_conflicts(records: list[AgentStatusRecord]) -> list[OwnershipConflict]:
    """Aynı job_id için birden fazla farklı owner görülen durumları döndürür."""
    owners_by_job: dict[str, set[str]] = {}
    for record in records:
        owners_by_job.setdefault(record.job_id, set()).add(record.owner)
    return [
        OwnershipConflict(job_id=job_id, owners=tuple(sorted(owners)))
        for job_id, owners in sorted(owners_by_job.items())
        if len(owners) > 1
    ]
