"""Single-reader coordination gateway for the Lumos Board."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Iterator, Sequence


EVENT_SCHEMA = "lumos.coordination_event.v1"
READER_SCHEMA = "lumos.single_reader_lease.v1"
DELIVERY_SCHEMA = "lumos.delivery_state.v1"
AUDIT_SCHEMA = "lumos.coordination_audit.v1"
MAX_MESSAGE_LENGTH = 500

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", re.I | re.S),
    re.compile(r"\b(?:api[_ -]?key|token|secret|password)\s*[:=]\s*\S+", re.I),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.I),
)


class CoordinationError(ValueError):
    """Base error for invalid gateway operations."""


class ReaderConflict(CoordinationError):
    """Raised when another live reader already owns the user-facing lease."""


class ReaderUnauthorized(CoordinationError):
    """Raised when the reader token is absent, invalid or stale."""


class EventKind(str, Enum):
    DECISION_REQUIRED = "DECISION_REQUIRED"
    RISK = "RISK"
    RECOMMENDATION = "RECOMMENDATION"
    INFORMATION = "INFORMATION"
    RESULT = "RESULT"
    DEPENDENCY = "DEPENDENCY"


class Route(str, Enum):
    USER = "USER"
    TASK = "TASK"
    AGENT = "AGENT"


@dataclass(frozen=True)
class ReaderSession:
    reader_id: str
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class CoordinationEvent:
    event_id: str
    dedupe_key: str
    source: str
    task_id: str
    kind: EventKind
    message: str
    created_at: datetime
    route: Route
    route_target: str
    severity: str = "normal"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": EVENT_SCHEMA,
            "event_id": self.event_id,
            "dedupe_key": self.dedupe_key,
            "source": self.source,
            "task_id": self.task_id,
            "kind": self.kind.value,
            "message": self.message,
            "created_at": _format_time(self.created_at),
            "route": self.route.value,
            "route_target": self.route_target,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, value: object) -> CoordinationEvent:
        if not isinstance(value, dict) or value.get("schema") != EVENT_SCHEMA:
            raise CoordinationError("coordination event şeması geçersiz")
        try:
            return cls(
                event_id=_required_text(value, "event_id"),
                dedupe_key=_required_text(value, "dedupe_key"),
                source=_required_text(value, "source"),
                task_id=_required_text(value, "task_id"),
                kind=EventKind(_required_text(value, "kind")),
                message=_required_text(value, "message"),
                created_at=_parse_time(_required_text(value, "created_at")),
                route=Route(_required_text(value, "route")),
                route_target=_required_text(value, "route_target"),
                severity=_required_text(value, "severity"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CoordinationError("coordination event kaydı geçersiz") from exc


@dataclass(frozen=True)
class EventReceipt:
    accepted: bool
    event: CoordinationEvent
    duplicate_of: str | None = None


@dataclass(frozen=True)
class UserDigest:
    decisions: tuple[CoordinationEvent, ...]
    risks: tuple[CoordinationEvent, ...]
    recommendations: tuple[CoordinationEvent, ...]
    information: tuple[CoordinationEvent, ...]

    @property
    def event_ids(self) -> tuple[str, ...]:
        return tuple(
            event.event_id
            for group in (self.decisions, self.risks, self.recommendations, self.information)
            for event in group
        )

    def to_dict(self) -> dict[str, object]:
        def values(events: Sequence[CoordinationEvent]) -> list[dict[str, object]]:
            return [
                {
                    "event_id": event.event_id,
                    "task_id": event.task_id,
                    "message": event.message,
                    "severity": event.severity,
                }
                for event in events
            ]

        return {
            "decisions": values(self.decisions),
            "risks": values(self.risks),
            "recommendations": values(self.recommendations),
            "information": values(self.information),
        }


class SingleReaderGateway:
    """Accept events from many writers but expose the user digest to one leased reader."""

    def __init__(
        self,
        store_dir: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store_dir = Path(store_dir)
        self.events_path = self.store_dir / "coordination_events.jsonl"
        self.reader_path = self.store_dir / "single_reader.json"
        self.delivery_path = self.store_dir / "delivery_state.json"
        self.audit_path = self.store_dir / "coordination_audit.jsonl"
        self.lock_path = self.store_dir / "coordination.lock"
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def claim_reader(self, *, reader_id: str, ttl_seconds: int = 900) -> ReaderSession:
        reader_id = _clean_text(reader_id, "reader_id")
        if ttl_seconds <= 0:
            raise CoordinationError("ttl_seconds sıfırdan büyük olmalı")
        with self._lock():
            now = self._now()
            current = self._read_reader()
            if current and _parse_time(_required_text(current, "expires_at")) > now:
                raise ReaderConflict(f"aktif Duvar okuyucusu: {_required_text(current, 'reader_id')}")
            if current:
                self._audit(
                    "READER_STALE_TAKEOVER",
                    actor=reader_id,
                    details={"previous_reader": current.get("reader_id")},
                    at=now,
                )
            token = secrets.token_urlsafe(32)
            expires_at = now + timedelta(seconds=ttl_seconds)
            previous = self.reader_path.read_bytes() if self.reader_path.exists() else None
            self._write_json(
                self.reader_path,
                {
                    "schema": READER_SCHEMA,
                    "reader_id": reader_id,
                    "token_hash": _token_hash(token),
                    "heartbeat_at": _format_time(now),
                    "expires_at": _format_time(expires_at),
                },
            )
            try:
                self._audit("READER_CLAIMED", actor=reader_id, at=now)
            except Exception as exc:
                # Audit yazılamazsa lease geri alınır; aksi halde token'ı
                # kimsenin almadığı, TTL bitene dek kilitli öksüz lease kalır.
                if previous is None:
                    self.reader_path.unlink(missing_ok=True)
                else:
                    self.reader_path.write_bytes(previous)
                raise CoordinationError("audit yazılamadı; reader claim geri alındı") from exc
            return ReaderSession(reader_id, token, expires_at)

    def heartbeat_reader(self, token: str, *, ttl_seconds: int = 900) -> datetime:
        if ttl_seconds <= 0:
            raise CoordinationError("ttl_seconds sıfırdan büyük olmalı")
        with self._lock():
            now = self._now()
            reader = self._require_reader(token, now)
            expires_at = now + timedelta(seconds=ttl_seconds)
            reader["heartbeat_at"] = _format_time(now)
            reader["expires_at"] = _format_time(expires_at)
            self._write_json(self.reader_path, reader)
            self._audit("READER_HEARTBEAT", actor=_required_text(reader, "reader_id"), at=now)
            return expires_at

    def release_reader(self, token: str) -> None:
        with self._lock():
            now = self._now()
            reader = self._require_reader(token, now)
            reader_id = _required_text(reader, "reader_id")
            self.reader_path.unlink(missing_ok=True)
            self._audit("READER_RELEASED", actor=reader_id, at=now)

    def submit_event(
        self,
        *,
        dedupe_key: str,
        source: str,
        task_id: str,
        kind: EventKind,
        message: str,
        severity: str = "normal",
        target_agent: str | None = None,
        user_relevant: bool = False,
    ) -> EventReceipt:
        dedupe_key = _clean_text(dedupe_key, "dedupe_key")
        source = _clean_text(source, "source")
        task_id = _clean_text(task_id, "task_id")
        message = _safe_message(message)
        severity = _clean_text(severity, "severity").lower()
        if severity not in {"normal", "low", "medium", "high", "critical"}:
            raise CoordinationError("severity geçersiz")
        with self._lock():
            events = self._read_events()
            duplicate = next((event for event in events if event.dedupe_key == dedupe_key), None)
            if duplicate:
                self._audit(
                    "EVENT_DEDUPLICATED",
                    actor=source,
                    details={"dedupe_key": dedupe_key, "event_id": duplicate.event_id},
                    at=self._now(),
                )
                return EventReceipt(False, duplicate, duplicate.event_id)
            route, route_target = _route_event(
                kind,
                task_id=task_id,
                severity=severity,
                target_agent=target_agent,
                user_relevant=user_relevant,
            )
            event = CoordinationEvent(
                event_id=str(uuid.uuid4()),
                dedupe_key=dedupe_key,
                source=source,
                task_id=task_id,
                kind=kind,
                message=message,
                created_at=self._now(),
                route=route,
                route_target=route_target,
                severity=severity,
            )
            self._append_json(self.events_path, event.to_dict())
            self._audit(
                "EVENT_ROUTED",
                actor=source,
                details={
                    "event_id": event.event_id,
                    "kind": event.kind.value,
                    "route": event.route.value,
                    "route_target": event.route_target,
                },
                at=event.created_at,
            )
            return EventReceipt(True, event)

    def read_user_digest(self, token: str) -> UserDigest:
        with self._lock():
            now = self._now()
            reader = self._require_reader(token, now)
            acknowledged = self._read_acknowledged()
            events = [
                event
                for event in self._read_events()
                if event.route is Route.USER and event.event_id not in acknowledged
            ]
            digest = UserDigest(
                decisions=tuple(event for event in events if event.kind is EventKind.DECISION_REQUIRED),
                risks=tuple(event for event in events if event.kind is EventKind.RISK),
                recommendations=tuple(event for event in events if event.kind is EventKind.RECOMMENDATION),
                information=tuple(event for event in events if event.kind is EventKind.INFORMATION),
            )
            self._audit(
                "USER_DIGEST_READ",
                actor=_required_text(reader, "reader_id"),
                details={"event_ids": list(digest.event_ids)},
                at=now,
            )
            return digest

    def read_internal_routes(self, token: str, *, target: str) -> tuple[CoordinationEvent, ...]:
        target = _clean_text(target, "target")
        with self._lock():
            now = self._now()
            reader = self._require_reader(token, now)
            # USER rotası yalnız read_user_digest + acknowledge akışına aittir;
            # internal rota okuması kullanıcı gelen kutusunu sızdıramaz.
            events = tuple(
                event
                for event in self._read_events()
                if event.route is not Route.USER and event.route_target == target
            )
            self._audit(
                "INTERNAL_ROUTES_READ",
                actor=_required_text(reader, "reader_id"),
                details={"target": target, "event_ids": [event.event_id for event in events]},
                at=now,
            )
            return events

    def acknowledge(self, token: str, event_ids: Sequence[str]) -> None:
        requested = {_clean_text(event_id, "event_id") for event_id in event_ids}
        with self._lock():
            now = self._now()
            reader = self._require_reader(token, now)
            user_event_ids = {
                event.event_id for event in self._read_events() if event.route is Route.USER
            }
            if not requested <= user_event_ids:
                raise CoordinationError("yalnız kullanıcı rotasındaki olaylar acknowledge edilebilir")
            acknowledged = self._read_acknowledged() | requested
            self._write_json(
                self.delivery_path,
                {"schema": DELIVERY_SCHEMA, "acknowledged_event_ids": sorted(acknowledged)},
            )
            self._audit(
                "USER_DIGEST_ACKNOWLEDGED",
                actor=_required_text(reader, "reader_id"),
                details={"event_ids": sorted(requested)},
                at=now,
            )

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _read_reader(self) -> dict[str, object] | None:
        if not self.reader_path.exists():
            return None
        value = self._read_json(self.reader_path)
        if value.get("schema") != READER_SCHEMA:
            raise CoordinationError("reader lease şeması geçersiz")
        return value

    def _require_reader(self, token: str, now: datetime) -> dict[str, object]:
        reader = self._read_reader()
        if reader is None or _parse_time(_required_text(reader, "expires_at")) <= now:
            raise ReaderUnauthorized("aktif Duvar okuyucu lease'i yok")
        if not hmac.compare_digest(_required_text(reader, "token_hash"), _token_hash(token)):
            raise ReaderUnauthorized("Duvar okuyucu token'ı geçersiz")
        return reader

    def _read_events(self) -> list[CoordinationEvent]:
        if not self.events_path.exists():
            return []
        try:
            return [
                CoordinationEvent.from_dict(json.loads(line))
                for line in self.events_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CoordinationError("coordination inbox okunamıyor") from exc

    def _read_acknowledged(self) -> set[str]:
        if not self.delivery_path.exists():
            return set()
        value = self._read_json(self.delivery_path)
        ids = value.get("acknowledged_event_ids")
        if value.get("schema") != DELIVERY_SCHEMA or not isinstance(ids, list):
            raise CoordinationError("delivery state geçersiz")
        if not all(isinstance(event_id, str) for event_id in ids):
            raise CoordinationError("delivery event id listesi geçersiz")
        return set(ids)

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CoordinationError(f"{path.name} okunamıyor") from exc
        if not isinstance(value, dict):
            raise CoordinationError(f"{path.name} geçersiz")
        return value

    def _write_json(self, path: Path, value: dict[str, object]) -> None:
        fd, temporary_name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=self.store_dir)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _append_json(path: Path, value: dict[str, object]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _audit(
        self,
        event: str,
        *,
        actor: str,
        at: datetime,
        details: dict[str, object] | None = None,
    ) -> None:
        self._append_json(
            self.audit_path,
            {
                "schema": AUDIT_SCHEMA,
                "event": event,
                "at": _format_time(at),
                "actor": actor,
                "details": details or {},
            },
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise CoordinationError("clock timezone içermeli")
        return value.astimezone(timezone.utc)


def _route_event(
    kind: EventKind,
    *,
    task_id: str,
    severity: str,
    target_agent: str | None,
    user_relevant: bool,
) -> tuple[Route, str]:
    if kind in {EventKind.DECISION_REQUIRED, EventKind.RECOMMENDATION}:
        return Route.USER, "user"
    if kind is EventKind.RISK and severity in {"high", "critical"}:
        return Route.USER, "user"
    if kind is EventKind.INFORMATION and user_relevant:
        return Route.USER, "user"
    if target_agent:
        return Route.AGENT, _clean_text(target_agent, "target_agent")
    return Route.TASK, task_id


def _safe_message(value: str) -> str:
    message = " ".join(_clean_text(value, "message").split())
    for pattern in _SECRET_PATTERNS:
        message = pattern.sub("[redacted]", message)
    return message[:MAX_MESSAGE_LENGTH]


def _token_hash(token: str) -> str:
    return hashlib.sha256(_clean_text(token, "token").encode("utf-8")).hexdigest()


def _clean_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CoordinationError(f"{field} boş olamaz")
    return value.strip()


def _required_text(value: dict[str, object], field: str) -> str:
    item = value[field]
    if not isinstance(item, str) or not item:
        raise TypeError(field)
    return item


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
