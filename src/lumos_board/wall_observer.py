"""
Agent Wall gözlem katmanı — Faz-1, salt-okunur.

Sözleşme: `docs/contracts/agent-wall-observation-v1.md`.

Bu modül **hiçbir şeyi değiştirmez**: claim store'a, `agent_status_*.json`'a
veya çalışma ağaçlarına yazmaz, hiçbir ajanı durdurmaz, hiçbir yazmayı
engellemez. Tek yan etkisi kendi gözlem güncesine append yapmaktır ve o da
`observe(...)` çağrısının ayrı bir adımıdır (`write_observations`).

Faz-1 üç sinyal üretir, üçü de **türetilmiş** kaynaklardan:

    S1  OUT_OF_SCOPE / FOREIGN_SCOPE   claim.scopes  vs  fiilen dokunulan yollar
    S2  SILENT_DRIFT                   kapsam dışı dokunuşların tek başka işe kümelenmesi
    S3  STALE_CLAIM                    claim_events zaman damgaları

Faz-1 KAPSAM DIŞI (sözleşme §3): çağrı hacmi, ajan başına bütçe, egress,
kontrol/engelleme, ajan kimliğinin doğrulanması.

Güven modeli (sözleşme §1): tespit yalnız türetilmiş kaynaklara dayanır.
`agent_status_*.json` ve claim'in kendi `status` alanı **beyandır**; bu
modül onları tespit dayanağı olarak kullanmaz.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence

from lumos_board.agent_status import mask_secretlike
from lumos_board.task_claim import CLAIM_STORE_SCHEMA, ClaimStatus, TaskClaim

OBSERVATION_SCHEMA = "lumos.agent_wall_observation.v1"
OBSERVATION_LOG_NAME = "wall_observations.jsonl"

SIGNAL_OUT_OF_SCOPE = "OUT_OF_SCOPE"
SIGNAL_FOREIGN_SCOPE = "FOREIGN_SCOPE"
SIGNAL_SILENT_DRIFT = "SILENT_DRIFT"
SIGNAL_STALE_CLAIM = "STALE_CLAIM"

SOURCE_GIT = "git"
SOURCE_CLAIM_STORE = "claim_store"
SOURCE_CLAIM_EVENTS = "claim_events"

# S2: kapsam dışı dokunuşlar tek bir üst dizinde bu kadar yoğunlaşırsa
# "başka bir işe kümelenmiş" sayılır. Eşik bilinçli olarak muhafazakâr;
# Faz-1'in amacı yanlış pozitif oranını ölçmek (sözleşme §5).
DRIFT_MIN_PATHS = 3

# S3: son olaydan bu kadar süre geçmiş ve hâlâ ACTIVE ise ritim bulgusu.
STALE_AFTER = timedelta(hours=6)


@dataclass(frozen=True)
class Observation:
    """Tek bir gözlem bulgusu. `evidence` boş olamaz (sözleşme §4 kural 5)."""

    signal: str
    claim_id: str
    task_id: str
    repo: str
    owner: str
    evidence: dict
    derived_from: tuple[str, ...]
    at: datetime

    def to_record(self) -> dict:
        if not self.evidence:
            raise ValueError("evidence boş olamaz — kanıtsız bulgu kaydedilmez")
        return {
            "schema": OBSERVATION_SCHEMA,
            "at": _format_time(self.at),
            "signal": self.signal,
            "claim_id": self.claim_id,
            "task_id": self.task_id,
            "repo": self.repo,
            "owner": self.owner,
            "evidence": self.evidence,
            "derived_from": list(self.derived_from),
        }


@dataclass
class ObservationRun:
    observations: list[Observation] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_relative(paths: Iterable[str]) -> tuple[str, ...]:
    """Mutlak/makine yolu kaydedilmez (sözleşme §4 kural 2)."""
    out: set[str] = set()
    for raw in paths:
        text = str(raw or "").strip().replace("\\", "/")
        if not text:
            continue
        path = PurePosixPath(text)
        if path.is_absolute() or ".." in path.parts:
            continue
        out.add(str(path))
    return tuple(sorted(out))


def touched_paths(worktree: Path, *, base_ref: str = "origin/main") -> tuple[str, ...]:
    """
    Bir çalışma ağacının fiilen dokunduğu repo-relative yollar.

    Türetilmiş kaynak: git. Ajanın beyanı değil, etkisi okunur. Hem
    commit'lenmiş fark (base..HEAD) hem de commit'lenmemiş çalışma ağacı
    durumu toplanır — sessiz sapma çoğu zaman henüz commit edilmemiştir.
    """
    if not Path(worktree).is_dir():
        return ()
    collected: set[str] = set()
    for args in (
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        ["git", "status", "--porcelain"],
    ):
        try:
            proc = subprocess.run(
                args, cwd=str(worktree), capture_output=True, text=True, timeout=30, check=False
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode != 0:
            continue
        for line in proc.stdout.splitlines():
            text = line.strip()
            if not text:
                continue
            if args[1] == "status":
                # "XY path" veya "XY old -> new"
                text = text[3:].strip() if len(text) > 3 else ""
                if " -> " in text:
                    text = text.split(" -> ", 1)[1]
            collected.add(text.strip().strip('"'))
    return _repo_relative(collected)


def _path_in_scopes(path: str, scopes: Sequence[str]) -> bool:
    candidate = PurePosixPath(path)
    for scope in scopes:
        scope_path = PurePosixPath(scope)
        if candidate == scope_path or scope_path in candidate.parents:
            return True
    return False


def _active(claims: Sequence[TaskClaim]) -> tuple[TaskClaim, ...]:
    return tuple(c for c in claims if c.status == ClaimStatus.ACTIVE)


def observe_scope(
    claim: TaskClaim,
    paths: Sequence[str],
    *,
    other_active: Sequence[TaskClaim],
    now: datetime,
) -> list[Observation]:
    """
    S1 — kapsam dışı dokunuş.

    İki bulgu ayrılır: `FOREIGN_SCOPE` (yol BAŞKA bir ACTIVE claim'in
    kapsamında — Anayasa §3 adayı, daha ağır) ve `OUT_OF_SCOPE` (hiçbir
    claim kapsamında değil).
    """
    out: list[Observation] = []
    foreign: dict[str, list[str]] = {}
    orphan: list[str] = []

    for path in paths:
        if _path_in_scopes(path, claim.scopes):
            continue
        owner_claim = next(
            (o for o in other_active if o.claim_id != claim.claim_id and _path_in_scopes(path, o.scopes)),
            None,
        )
        if owner_claim is not None:
            foreign.setdefault(owner_claim.claim_id, []).append(path)
        else:
            orphan.append(path)

    for other_claim_id, hit_paths in sorted(foreign.items()):
        owner_of = next(o for o in other_active if o.claim_id == other_claim_id)
        out.append(
            Observation(
                signal=SIGNAL_FOREIGN_SCOPE,
                claim_id=claim.claim_id,
                task_id=claim.task_id,
                repo=claim.repo,
                owner=claim.owner,
                evidence={
                    "paths": sorted(hit_paths),
                    "declared_scopes": list(claim.scopes),
                    "owned_by_claim_id": other_claim_id,
                    "owned_by": owner_of.owner,
                    "owned_by_scopes": list(owner_of.scopes),
                },
                derived_from=(SOURCE_GIT, SOURCE_CLAIM_STORE),
                at=now,
            )
        )

    if orphan:
        out.append(
            Observation(
                signal=SIGNAL_OUT_OF_SCOPE,
                claim_id=claim.claim_id,
                task_id=claim.task_id,
                repo=claim.repo,
                owner=claim.owner,
                evidence={"paths": sorted(orphan), "declared_scopes": list(claim.scopes)},
                derived_from=(SOURCE_GIT, SOURCE_CLAIM_STORE),
                at=now,
            )
        )
    return out


def observe_drift(
    claim: TaskClaim,
    paths: Sequence[str],
    *,
    now: datetime,
    min_paths: int = DRIFT_MIN_PATHS,
) -> list[Observation]:
    """
    S2 — sessiz sapma.

    Kapsam dışı dokunuşlar tek bir üst dizinde kümeleniyorsa, claim'in
    `task_id`'si ile fiilen yapılan iş ayrışmış demektir. Dağınık tek tük
    dokunuş sapma sayılmaz; kümelenme sayılır.
    """
    outside = [p for p in paths if not _path_in_scopes(p, claim.scopes)]
    if len(outside) < min_paths:
        return []

    buckets: dict[str, list[str]] = {}
    for path in outside:
        parts = PurePosixPath(path).parts
        root = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        buckets.setdefault(root, []).append(path)

    root, hits = max(buckets.items(), key=lambda item: (len(item[1]), item[0]))
    if len(hits) < min_paths:
        return []

    return [
        Observation(
            signal=SIGNAL_SILENT_DRIFT,
            claim_id=claim.claim_id,
            task_id=claim.task_id,
            repo=claim.repo,
            owner=claim.owner,
            evidence={
                "cluster_root": root,
                "paths": sorted(hits),
                "declared_scopes": list(claim.scopes),
                "declared_task": mask_secretlike(claim.task_id),
                "outside_total": len(outside),
            },
            derived_from=(SOURCE_GIT, SOURCE_CLAIM_STORE),
            at=now,
        )
    ]


def observe_rhythm(
    claim: TaskClaim,
    *,
    last_event_at: datetime | None,
    now: datetime,
    stale_after: timedelta = STALE_AFTER,
) -> list[Observation]:
    """
    S3 — ritim / asılı claim.

    Ajanın kendi durum beyanına sorulmaz; `claim_events.jsonl` zaman
    damgaları ve claim'in kendi TTL alanları okunur.
    """
    reasons: list[str] = []
    if claim.expires_at <= now:
        reasons.append("ttl_expired_but_active")
    silent_for = None
    if last_event_at is not None:
        silent_for = now - last_event_at
        if silent_for >= stale_after:
            reasons.append("no_events_since_threshold")
    if claim.heartbeat_at < claim.started_at:
        reasons.append("heartbeat_before_start")
    if not reasons:
        return []

    evidence: dict = {
        "reasons": reasons,
        "started_at": _format_time(claim.started_at),
        "heartbeat_at": _format_time(claim.heartbeat_at),
        "expires_at": _format_time(claim.expires_at),
    }
    if last_event_at is not None:
        evidence["last_event_at"] = _format_time(last_event_at)
        evidence["silent_for_seconds"] = int(silent_for.total_seconds())

    return [
        Observation(
            signal=SIGNAL_STALE_CLAIM,
            claim_id=claim.claim_id,
            task_id=claim.task_id,
            repo=claim.repo,
            owner=claim.owner,
            evidence=evidence,
            derived_from=(SOURCE_CLAIM_STORE, SOURCE_CLAIM_EVENTS),
            at=now,
        )
    ]


def read_claims(store_dir: Path) -> tuple[TaskClaim, ...]:
    """
    Claim deposunu **salt-okunur** okur: kilit almaz, hiçbir şey yazmaz.

    `TaskClaimStore.list_claims()` bilerek kullanılmaz. O metot
    `_locked_state()` üzerinden çalışır; başarıyla bittiğinde `_write_state`
    çağırır ve **exclusive flock** tutar. Yani okuma niyetiyle çağrılsa bile
    (a) `claims.json`'a yazar — sözleşme §4 kural 4'ü ihlal eder,
    (b) çalışan ajanların claim kapısını kilitleyerek onların koşum yoluna
    girer. Gözlem katmanı ikisini de yapamaz.

    Yırtık dosya riski yok: `_write_state` geçici dosyaya yazıp
    `os.replace` ile atomik olarak yerine koyar, okuyucu ya eskisini ya
    yenisini görür.

    Ek fayda: `_expire_stale` çalışmadığı için TTL'i geçmiş ama hâlâ ACTIVE
    yazan claim'ler ham hâliyle görünür — S3'ün tam olarak aradığı durum.
    """
    state_path = Path(store_dir) / "claims.json"
    if not state_path.is_file():
        return ()
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ()  # bozuk/yarım tur atlanır; gözlemci onarmaya çalışmaz
    if not isinstance(payload, dict) or payload.get("schema") != CLAIM_STORE_SCHEMA:
        return ()
    values = payload.get("claims")
    if not isinstance(values, list):
        return ()
    claims: list[TaskClaim] = []
    for value in values:
        try:
            claims.append(TaskClaim.from_dict(value))
        except Exception:
            continue
    return tuple(claims)


def last_event_times(audit_path: Path) -> dict[str, datetime]:
    """`claim_events.jsonl` → claim_id başına en son olay zamanı."""
    result: dict[str, datetime] = {}
    if not Path(audit_path).is_file():
        return result
    with Path(audit_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                continue  # yarım satır sessizce atlanır; gözlem yazma yapmaz
            claim_id = str(row.get("claim_id") or "")
            raw_at = str(row.get("at") or "")
            if not claim_id or not raw_at:
                continue
            try:
                stamp = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            if claim_id not in result or stamp > result[claim_id]:
                result[claim_id] = stamp
    return result


def observe(
    store_dir: Path,
    *,
    worktree_paths: dict[str, Sequence[str]] | None = None,
    base_ref: str = "origin/main",
    now: datetime | None = None,
) -> ObservationRun:
    """
    Bir gözlem turu. Hiçbir şey YAZMAZ — yalnız okur ve bulgu döndürür.

    `store_dir`: claim deposu dizini (`claims.json` + `claim_events.jsonl`).
    `TaskClaimStore` nesnesi bilerek alınmaz; bkz. `read_claims`.

    `worktree_paths`: claim_id → dokunulan yollar. Verilmezse her ACTIVE
    claim'in kendi `worktree`'si git ile okunur.
    """
    moment = now or datetime.now(timezone.utc)
    run = ObservationRun()

    claims = read_claims(store_dir)
    active = _active(claims)
    events = last_event_times(Path(store_dir) / "claim_events.jsonl")

    for claim in active:
        if worktree_paths is not None and claim.claim_id in worktree_paths:
            paths = _repo_relative(worktree_paths[claim.claim_id])
        else:
            paths = touched_paths(Path(claim.worktree), base_ref=base_ref)
            if not paths and not Path(claim.worktree).is_dir():
                run.skipped.append(f"{claim.claim_id}: worktree okunamadı")

        run.observations.extend(
            observe_scope(claim, paths, other_active=active, now=moment)
        )
        run.observations.extend(observe_drift(claim, paths, now=moment))
        run.observations.extend(
            observe_rhythm(claim, last_event_at=events.get(claim.claim_id), now=moment)
        )
    return run


def write_observations(log_path: Path, observations: Sequence[Observation]) -> int:
    """
    Bulguları gözlem güncesine **append** eder (sözleşme §4 kural 1).

    Gözlemcinin tek yazma noktası burasıdır ve yalnız kendi güncesine yazar.
    Hiçbir satır geri dönüp değiştirilmez.
    """
    if not observations:
        return 0
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for observation in observations:
            handle.write(json.dumps(observation.to_record(), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return len(observations)
