"""Privacy-preserving Account Activity Correlation kernel.

This is not activity tracking. It correlates a third-party security alert
with consented, device-bound session evidence and returns a non-definitive
verdict. It never stores raw browsing history, passwords, content, or
plaintext IP addresses, and it never auto-executes account actions.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

SCHEMA = "lumos.account_activity.v1"

VERDICT_OWNER_MATCH = "owner_match"
VERDICT_LIKELY_OWNER = "likely_owner"
VERDICT_UNKNOWN = "unknown"
VERDICT_SUSPICIOUS = "suspicious"
VERDICTS = frozenset(
    {
        VERDICT_OWNER_MATCH,
        VERDICT_LIKELY_OWNER,
        VERDICT_UNKNOWN,
        VERDICT_SUSPICIOUS,
    }
)

SOURCE_THIRD_PARTY_ALERT = "third_party_alert"
SOURCE_DEVICE_ACTIVITY = "lumos_device_activity"
SOURCE_NETWORK = "network_observation"

NETWORK_SAME = "same_network"
NETWORK_DIFFERENT = "different_network"
NETWORK_VPN_POSSIBLE = "vpn_possible"
NETWORK_UNKNOWN = "unknown"

NETWORK_CLASSES = frozenset({"mobile", "wifi", "wired", "vpn", "unknown"})
SESSION_KINDS = frozenset({"user_session", "background", "unknown"})
RISK_ORDINARY = "ordinary"
RISK_HIGH = "high"

WINDOW_DEFAULT = timedelta(minutes=10)
WINDOW_TIGHT = timedelta(minutes=5)
RETENTION_ORDINARY = timedelta(days=14)
RETENTION_HIGH = timedelta(days=90)

DECISION_ACKNOWLEDGE = "acknowledge"
DECISION_INVESTIGATE = "investigate"
DECISION_DISMISS = "dismiss"
DECISION_APPROVE_ACTION = "approve_action"

AUTO_FORBIDDEN_ACTIONS = frozenset(
    {
        "password_change",
        "session_revoke",
        "logout_all",
        "disable_account",
    }
)

FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "body",
        "content",
        "cookie",
        "cookies",
        "history",
        "href",
        "html",
        "ip",
        "ip_address",
        "page_title",
        "password",
        "passwd",
        "path",
        "query",
        "raw_ip",
        "secret",
        "title",
        "token",
        "url",
        "uri",
        "user_agent",
        "useragent",
    }
)

_IPV4_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_IPV6_RE = re.compile(r"\b(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\b")
_DEVICE_ID_RE = re.compile(r"^[0-9a-f]{64}$")
_SERVICE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_HEX_REF_RE = re.compile(r"^[0-9a-f]{64}$")

SERVICE_LABELS = {
    "xai.grok": "xAI/Grok",
    "google": "Google",
    "apple": "Apple",
}

NETWORK_LABELS = {
    "mobile": "mobil ağ",
    "wifi": "Wi-Fi",
    "wired": "kablolu ağ",
    "vpn": "VPN",
    "unknown": "bilinmeyen ağ",
}

SESSION_LABELS = {
    "user_session": "kullanıcı oturumu",
    "background": "arka plan",
    "unknown": "oturum",
}

NETWORK_RESULT_LABELS = {
    NETWORK_SAME: "aynı ağ",
    NETWORK_DIFFERENT: "farklı ağ",
    NETWORK_VPN_POSSIBLE: "VPN olası",
    NETWORK_UNKNOWN: "ağ belirsiz",
}


class CorrelationError(ValueError):
    """Rejected input or forbidden auto-action."""


@dataclass(frozen=True)
class RegisteredDevice:
    device_id: str
    public_key_fingerprint: str
    display_label: str
    attestation_ref: str | None
    registered_at: datetime


@dataclass(frozen=True)
class DeviceActivity:
    event_id: str
    observed_at: datetime
    service_id: str
    device_id: str
    session_kind: str
    network_class: str
    network_fingerprint: str | None
    attestation_ref: str | None
    risk_class: str


@dataclass(frozen=True)
class ThirdPartyAlert:
    alert_id: str
    observed_at: datetime
    service_id: str
    source_label: str
    ingest_agent_id: str
    claimed_device_id: str | None = None
    claimed_network_class: str | None = None
    network_fingerprint: str | None = None


@dataclass(frozen=True)
class SourceCitation:
    kind: str
    label: str
    observed_at: datetime
    summary: str


@dataclass(frozen=True)
class Signal:
    name: str
    matched: bool
    weight: str
    detail: str


@dataclass(frozen=True)
class CorrelationResult:
    correlation_id: str
    alert_id: str
    verdict: str
    confidence: str
    window: timedelta
    sources: tuple[SourceCitation, ...]
    signals: tuple[Signal, ...]
    matched_activity_ids: tuple[str, ...]
    explanation: str
    recommended_review: str
    auto_action: str
    network_result: str


@dataclass(frozen=True)
class ProvenanceEvent:
    sequence: int
    event_id: str
    kind: str
    agent_id: str
    at: datetime
    details: dict[str, Any]
    previous_hash: str
    digest: str


@dataclass(frozen=True)
class UserDecision:
    decision: str
    at: datetime
    action: str | None
    note: str


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def service_label(service_id: str) -> str:
    return SERVICE_LABELS.get(service_id, service_id)


def format_activity_line(activity: DeviceActivity, device: RegisteredDevice) -> str:
    stamp = _minute_utc(activity.observed_at)
    network = NETWORK_LABELS.get(activity.network_class, activity.network_class)
    session = SESSION_LABELS.get(activity.session_kind, activity.session_kind)
    return (
        f"{stamp} — {service_label(activity.service_id)} — "
        f"{device.display_label} — {network} — {session}"
    )


def hash_network_material(salt: str, material: str) -> str:
    _reject_network_plaintext(material)
    payload = f"{salt}:{material}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class AccountActivityCorrelator:
    """Local consent-gated ledger + multi-signal correlator."""

    def __init__(self, persist_dir: Path | str | None = None) -> None:
        self._persist_dir = Path(persist_dir) if persist_dir is not None else None
        self._consent = False
        self._devices: dict[str, RegisteredDevice] = {}
        self._activities: dict[str, DeviceActivity] = {}
        self._alerts: dict[str, ThirdPartyAlert] = {}
        self._results: dict[str, CorrelationResult] = {}
        self._decisions: dict[str, UserDecision] = {}
        self._provenance: list[ProvenanceEvent] = []
        self._network_salt = secrets.token_hex(16)
        if self._persist_dir is not None:
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            salt_path = self._persist_dir / "network_salt.txt"
            if salt_path.exists():
                self._network_salt = salt_path.read_text(encoding="utf-8").strip()
            else:
                salt_path.write_text(self._network_salt, encoding="utf-8")

    @property
    def consent_granted(self) -> bool:
        return self._consent

    @property
    def provenance(self) -> tuple[ProvenanceEvent, ...]:
        return tuple(self._provenance)

    def set_consent(self, granted: bool, *, agent_id: str = "lumos.local") -> None:
        previous = self._consent
        self._consent = bool(granted)
        if previous and not self._consent:
            self._activities.clear()
        self._record_provenance(
            "consent_changed",
            agent_id,
            {"granted": self._consent, "purged_on_revoke": previous and not self._consent},
        )

    def register_device(
        self,
        *,
        device_id: str,
        public_key_fingerprint: str,
        display_label: str,
        attestation_ref: str | None = None,
        agent_id: str = "lumos.local",
        registered_at: datetime | None = None,
    ) -> RegisteredDevice:
        device_id = _require_device_id(device_id)
        fingerprint = _require_hex_ref(public_key_fingerprint, "public_key_fingerprint")
        label = _require_display_label(display_label)
        att = _optional_hex_ref(attestation_ref, "attestation_ref")
        device = RegisteredDevice(
            device_id=device_id,
            public_key_fingerprint=fingerprint,
            display_label=label,
            attestation_ref=att,
            registered_at=_aware(registered_at or utcnow()),
        )
        self._devices[device_id] = device
        self._record_provenance(
            "device_registered",
            agent_id,
            {
                "device_id": device_id,
                "public_key_fingerprint": fingerprint,
                "attested": att is not None,
            },
        )
        return device

    def record_activity(
        self,
        payload: Mapping[str, Any],
        *,
        agent_id: str = "lumos.local",
    ) -> DeviceActivity:
        _reject_forbidden_payload(payload)
        if not self._consent:
            raise CorrelationError("recording_disabled")
        device_id = _require_device_id(str(payload.get("device_id") or ""))
        device = self._devices.get(device_id)
        if device is None:
            raise CorrelationError("device_not_registered")
        service_id = _require_service_id(str(payload.get("service_id") or ""))
        session_kind = _require_choice(payload.get("session_kind"), SESSION_KINDS, "session_kind")
        network_class = _require_choice(
            payload.get("network_class"), NETWORK_CLASSES, "network_class"
        )
        observed_at = _aware(payload["observed_at"]) if "observed_at" in payload else utcnow()
        fingerprint = self._fingerprint_from_payload(payload)
        attestation_ref = _optional_hex_ref(payload.get("attestation_ref"), "attestation_ref")
        if attestation_ref is None:
            attestation_ref = device.attestation_ref
        activity = DeviceActivity(
            event_id=str(payload.get("event_id") or uuid4()),
            observed_at=observed_at,
            service_id=service_id,
            device_id=device_id,
            session_kind=session_kind,
            network_class=network_class,
            network_fingerprint=fingerprint,
            attestation_ref=attestation_ref,
            risk_class=RISK_ORDINARY,
        )
        self._activities[activity.event_id] = activity
        self._persist_jsonl("activities.jsonl", _activity_record(activity))
        self._record_provenance(
            "activity_recorded",
            agent_id,
            {
                "event_id": activity.event_id,
                "service_id": service_id,
                "device_id": device_id,
                "session_kind": session_kind,
                "network_class": network_class,
            },
        )
        return activity

    def ingest_alert(
        self,
        payload: Mapping[str, Any],
        *,
        agent_id: str | None = None,
    ) -> ThirdPartyAlert:
        _reject_forbidden_payload(payload)
        ingest_agent = str(agent_id or payload.get("ingest_agent_id") or "lumos.local")
        claimed_device = payload.get("claimed_device_id")
        claimed_network = payload.get("claimed_network_class")
        alert = ThirdPartyAlert(
            alert_id=str(payload.get("alert_id") or uuid4()),
            observed_at=_aware(payload["observed_at"]),
            service_id=_require_service_id(str(payload.get("service_id") or "")),
            source_label=_require_source_label(str(payload.get("source_label") or "")),
            ingest_agent_id=ingest_agent,
            claimed_device_id=(
                _require_device_id(str(claimed_device)) if claimed_device else None
            ),
            claimed_network_class=(
                _require_choice(claimed_network, NETWORK_CLASSES, "claimed_network_class")
                if claimed_network
                else None
            ),
            network_fingerprint=self._fingerprint_from_payload(payload),
        )
        self._alerts[alert.alert_id] = alert
        self._persist_jsonl("alerts.jsonl", _alert_record(alert))
        self._record_provenance(
            "alert_ingested",
            ingest_agent,
            {
                "alert_id": alert.alert_id,
                "service_id": alert.service_id,
                "source_label": alert.source_label,
            },
        )
        return alert

    def correlate(
        self,
        alert: ThirdPartyAlert | Mapping[str, Any],
        *,
        agent_id: str = "lumos.local",
        window: timedelta | None = None,
        now: datetime | None = None,
    ) -> CorrelationResult:
        if not isinstance(alert, ThirdPartyAlert):
            alert = self.ingest_alert(alert, agent_id=agent_id)
        elif alert.alert_id not in self._alerts:
            self._alerts[alert.alert_id] = alert
            self._record_provenance(
                "alert_ingested",
                alert.ingest_agent_id,
                {
                    "alert_id": alert.alert_id,
                    "service_id": alert.service_id,
                    "source_label": alert.source_label,
                },
            )
        chosen_window = window or WINDOW_DEFAULT
        if chosen_window > WINDOW_DEFAULT:
            raise CorrelationError("window_exceeds_maximum")
        if chosen_window <= timedelta(0):
            raise CorrelationError("window_invalid")

        if not self._consent:
            result = self._result(
                alert,
                VERDICT_UNKNOWN,
                "none",
                chosen_window,
                (),
                (
                    Signal(
                        "consent",
                        False,
                        "required",
                        "recording_disabled",
                    ),
                ),
                (),
                "Cihaz oturum kaydı kapalı; eşleştirme yapılamaz. Bu bir kesin hüküm değildir.",
                "enable_recording",
                NETWORK_UNKNOWN,
            )
            return self._commit_result(result, agent_id)

        matches = [
            activity
            for activity in self._activities.values()
            if activity.service_id == alert.service_id
            and _within_window(activity.observed_at, alert.observed_at, chosen_window)
        ]
        in_window_any = [
            activity
            for activity in self._activities.values()
            if _within_window(activity.observed_at, alert.observed_at, chosen_window)
        ]

        device_match = False
        attested = False
        chosen: DeviceActivity | None = None
        device_conflict = False
        for activity in matches:
            device = self._devices.get(activity.device_id)
            if device is None:
                continue
            if (
                alert.claimed_device_id
                and alert.claimed_device_id != activity.device_id
            ):
                device_conflict = True
                continue
            device_match = True
            attested = bool(activity.attestation_ref or device.attestation_ref)
            chosen = activity
            break
        if matches and alert.claimed_device_id:
            if all(item.device_id != alert.claimed_device_id for item in matches):
                device_conflict = True

        network_result = NETWORK_UNKNOWN
        if chosen is not None:
            network_result = _compare_network(alert, chosen)

        time_match = chosen is not None or bool(matches)
        service_match = bool(matches)
        signals = (
            Signal(
                "service",
                service_match,
                "required",
                alert.service_id if service_match else "no_service_match",
            ),
            Signal(
                "time",
                time_match,
                "required",
                f"window_{int(chosen_window.total_seconds())}s",
            ),
            Signal(
                "device",
                device_match,
                "required",
                "registered_device" if device_match else "no_bound_device",
            ),
            Signal(
                "attestation",
                attested,
                "supporting",
                "attestation_ref" if attested else "unattested",
            ),
            Signal(
                "network",
                network_result in {NETWORK_SAME, NETWORK_VPN_POSSIBLE},
                "supporting",
                network_result,
            ),
        )

        sources = self._sources(alert, chosen, network_result)
        matched_ids = tuple(item.event_id for item in matches)

        if device_conflict:
            verdict = VERDICT_SUSPICIOUS
            confidence = "moderate"
            review = "investigate"
            explanation = (
                "Kayıtlı cihaz kimliği uyarıdaki cihaz referansıyla çelişiyor; incele. "
                "Kesin hüküm değildir."
            )
        elif not device_match:
            if not matches:
                verdict = VERDICT_SUSPICIOUS
                confidence = "moderate"
                review = "investigate"
                explanation = (
                    "Eşleşen kayıtlı cihaz aktivitesi yok; incele. "
                    "Kesin hüküm değildir."
                )
            else:
                verdict = VERDICT_UNKNOWN
                confidence = "weak"
                review = "review"
                explanation = (
                    "Zaman penceresinde servis izi var ama doğrulanabilir cihaz "
                    "kimliği yok; belirsiz. Kesin hüküm değildir."
                )
        else:
            core = (service_match, time_match, device_match)
            if all(core) and network_result != NETWORK_DIFFERENT:
                verdict = VERDICT_OWNER_MATCH
                confidence = "strong" if attested else "moderate"
                review = "acknowledge"
                device = self._devices[chosen.device_id]  # type: ignore[union-attr]
                explanation = (
                    "Bu giriş kayıtlı cihazın aynı penceredeki oturumuyla "
                    f"örtüşüyor ({device.display_label}). "
                    "owner_match kesin kimlik hükmü değildir."
                )
            elif all(core) and network_result == NETWORK_DIFFERENT:
                verdict = VERDICT_LIKELY_OWNER
                confidence = "moderate"
                review = "review"
                explanation = (
                    "Cihaz, zaman ve servis örtüşüyor ama ağ sınıfı farklı; "
                    "likely_owner. Kesin hüküm değildir."
                )
            else:
                verdict = VERDICT_LIKELY_OWNER
                confidence = "moderate"
                review = "review"
                explanation = (
                    "Birden fazla sinyal var ama üçlü eşleşme yok; likely_owner. "
                    "Kesin hüküm değildir."
                )

        if not device_match and in_window_any and not matches:
            verdict = VERDICT_UNKNOWN
            confidence = "weak"
            review = "review"
            explanation = (
                "Aynı dakikalarda başka bir servis aktivitesi var; bu uyarıyla "
                "çoklu sinyal oluşmadı. Kesin hüküm değildir."
            )

        result = self._result(
            alert,
            verdict,
            confidence,
            chosen_window,
            sources,
            signals,
            matched_ids,
            explanation,
            review,
            network_result,
            now=now,
        )
        return self._commit_result(result, agent_id)

    def explain(self, correlation_id: str) -> str:
        result = self._results.get(correlation_id)
        if result is None:
            raise CorrelationError("unknown_correlation")
        lines = [
            result.explanation,
            f"Sonuç: {result.verdict} (kesin hüküm değil)",
            "Kaynaklar:",
        ]
        for source in result.sources:
            lines.append(
                f"- {source.label} ({_minute_utc(source.observed_at)}): {source.summary}"
            )
        lines.append("Sinyaller:")
        for signal in result.signals:
            state = "eşleşti" if signal.matched else "eşleşmedi"
            lines.append(f"- {signal.name}: {state} ({signal.detail})")
        return "\n".join(lines)

    def record_user_decision(
        self,
        correlation_id: str,
        decision: str,
        *,
        action: str | None = None,
        note: str = "",
        agent_id: str = "user",
    ) -> UserDecision:
        if correlation_id not in self._results:
            raise CorrelationError("unknown_correlation")
        if decision not in {
            DECISION_ACKNOWLEDGE,
            DECISION_INVESTIGATE,
            DECISION_DISMISS,
            DECISION_APPROVE_ACTION,
        }:
            raise CorrelationError("unknown_decision")
        if decision == DECISION_APPROVE_ACTION:
            if action not in AUTO_FORBIDDEN_ACTIONS:
                raise CorrelationError("unknown_action")
        elif action:
            raise CorrelationError("action_requires_approve_action")
        recorded = UserDecision(
            decision=decision,
            at=utcnow(),
            action=action,
            note=note[:120],
        )
        self._decisions[correlation_id] = recorded
        self._record_provenance(
            "user_decided",
            agent_id,
            {
                "correlation_id": correlation_id,
                "decision": decision,
                "action": action,
                "executed": False,
            },
        )
        return recorded

    def execute_action(self, correlation_id: str, action: str) -> None:
        self._record_provenance(
            "auto_action_refused",
            "lumos.local",
            {
                "correlation_id": correlation_id,
                "action": action,
                "reason": "human_approval_required",
            },
        )
        raise CorrelationError("human_approval_required")

    def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = _aware(now or utcnow())
        removed = 0
        for event_id, activity in list(self._activities.items()):
            limit = (
                RETENTION_HIGH
                if activity.risk_class == RISK_HIGH
                else RETENTION_ORDINARY
            )
            if moment - activity.observed_at > limit:
                del self._activities[event_id]
                removed += 1
        for alert_id, alert in list(self._alerts.items()):
            related = [
                result
                for result in self._results.values()
                if result.alert_id == alert.alert_id
            ]
            is_high = any(item.verdict == VERDICT_SUSPICIOUS for item in related)
            limit = RETENTION_HIGH if is_high else RETENTION_ORDINARY
            if moment - alert.observed_at > limit:
                del self._alerts[alert_id]
                removed += 1
        return removed

    def mark_high_risk(self, event_id: str) -> None:
        activity = self._activities.get(event_id)
        if activity is None:
            raise CorrelationError("unknown_activity")
        self._activities[event_id] = DeviceActivity(
            **{**activity.__dict__, "risk_class": RISK_HIGH}
        )

    def delete_activity(self, event_id: str, *, agent_id: str = "user") -> None:
        if event_id not in self._activities:
            raise CorrelationError("unknown_activity")
        del self._activities[event_id]
        self._record_provenance(
            "activity_deleted",
            agent_id,
            {"event_id": event_id},
        )

    def verify_provenance_chain(self) -> bool:
        previous = "GENESIS"
        for event in self._provenance:
            if event.previous_hash != previous:
                return False
            payload = _provenance_payload(
                sequence=event.sequence,
                event_id=event.event_id,
                kind=event.kind,
                agent_id=event.agent_id,
                at=event.at.isoformat(),
                details=event.details,
                previous_hash=event.previous_hash,
            )
            if _digest(payload) != event.digest:
                return False
            previous = event.digest
        return True

    def known_devices(self) -> tuple[RegisteredDevice, ...]:
        return tuple(self._devices.values())

    def activities(self) -> tuple[DeviceActivity, ...]:
        return tuple(self._activities.values())

    def decision_for(self, correlation_id: str) -> UserDecision | None:
        return self._decisions.get(correlation_id)

    def _fingerprint_from_payload(self, payload: Mapping[str, Any]) -> str | None:
        provided = payload.get("network_fingerprint")
        if provided:
            return _require_hex_ref(str(provided), "network_fingerprint")
        material = payload.get("network_material")
        if not material:
            return None
        return hash_network_material(self._network_salt, str(material))

    def _sources(
        self,
        alert: ThirdPartyAlert,
        activity: DeviceActivity | None,
        network_result: str,
    ) -> tuple[SourceCitation, ...]:
        sources = [
            SourceCitation(
                SOURCE_THIRD_PARTY_ALERT,
                alert.source_label,
                alert.observed_at,
                f"{service_label(alert.service_id)} güvenlik uyarısı",
            )
        ]
        if activity is not None:
            device = self._devices[activity.device_id]
            sources.append(
                SourceCitation(
                    SOURCE_DEVICE_ACTIVITY,
                    "Lumos device activity",
                    activity.observed_at,
                    format_activity_line(activity, device),
                )
            )
        sources.append(
            SourceCitation(
                SOURCE_NETWORK,
                "network observation",
                activity.observed_at if activity is not None else alert.observed_at,
                NETWORK_RESULT_LABELS[network_result],
            )
        )
        return tuple(sources)

    def _result(
        self,
        alert: ThirdPartyAlert,
        verdict: str,
        confidence: str,
        window: timedelta,
        sources: tuple[SourceCitation, ...],
        signals: tuple[Signal, ...],
        matched_ids: tuple[str, ...],
        explanation: str,
        review: str,
        network_result: str,
        *,
        now: datetime | None = None,
    ) -> CorrelationResult:
        del now
        return CorrelationResult(
            correlation_id=str(uuid4()),
            alert_id=alert.alert_id,
            verdict=verdict,
            confidence=confidence,
            window=window,
            sources=sources,
            signals=signals,
            matched_activity_ids=matched_ids,
            explanation=explanation,
            recommended_review=review,
            auto_action="none",
            network_result=network_result,
        )

    def _commit_result(
        self, result: CorrelationResult, agent_id: str
    ) -> CorrelationResult:
        self._results[result.correlation_id] = result
        self._persist_jsonl("correlations.jsonl", _result_record(result))
        self._record_provenance(
            "correlated",
            agent_id,
            {
                "correlation_id": result.correlation_id,
                "verdict": result.verdict,
                "matched_activity_ids": list(result.matched_activity_ids),
                "auto_action": result.auto_action,
                "source_kinds": [source.kind for source in result.sources],
            },
        )
        return result

    def _record_provenance(
        self, kind: str, agent_id: str, details: dict[str, Any]
    ) -> ProvenanceEvent:
        previous = self._provenance[-1].digest if self._provenance else "GENESIS"
        sequence = len(self._provenance) + 1
        event_id = str(uuid4())
        at = utcnow()
        payload = _provenance_payload(
            sequence=sequence,
            event_id=event_id,
            kind=kind,
            agent_id=agent_id,
            at=at.isoformat(),
            details=details,
            previous_hash=previous,
        )
        event = ProvenanceEvent(
            sequence=sequence,
            event_id=event_id,
            kind=kind,
            agent_id=agent_id,
            at=at,
            details=dict(details),
            previous_hash=previous,
            digest=_digest(payload),
        )
        self._provenance.append(event)
        self._persist_jsonl("provenance.jsonl", _provenance_record(event))
        return event

    def _persist_jsonl(self, name: str, record: dict[str, Any]) -> None:
        if self._persist_dir is None:
            return
        path = self._persist_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")


def _activity_record(activity: DeviceActivity) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "event_id": activity.event_id,
        "observed_at": activity.observed_at.isoformat(),
        "service_id": activity.service_id,
        "device_id": activity.device_id,
        "session_kind": activity.session_kind,
        "network_class": activity.network_class,
        "network_fingerprint": activity.network_fingerprint,
        "attestation_ref": activity.attestation_ref,
        "risk_class": activity.risk_class,
    }


def _alert_record(alert: ThirdPartyAlert) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "alert_id": alert.alert_id,
        "observed_at": alert.observed_at.isoformat(),
        "service_id": alert.service_id,
        "source_label": alert.source_label,
        "ingest_agent_id": alert.ingest_agent_id,
        "claimed_device_id": alert.claimed_device_id,
        "claimed_network_class": alert.claimed_network_class,
        "network_fingerprint": alert.network_fingerprint,
    }


def _result_record(result: CorrelationResult) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "correlation_id": result.correlation_id,
        "alert_id": result.alert_id,
        "verdict": result.verdict,
        "confidence": result.confidence,
        "auto_action": result.auto_action,
        "network_result": result.network_result,
        "matched_activity_ids": list(result.matched_activity_ids),
        "source_kinds": [source.kind for source in result.sources],
    }


def _provenance_record(event: ProvenanceEvent) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "sequence": event.sequence,
        "event_id": event.event_id,
        "kind": event.kind,
        "agent_id": event.agent_id,
        "at": event.at.isoformat(),
        "details": event.details,
        "previous_hash": event.previous_hash,
        "digest": event.digest,
    }


def _provenance_payload(**values: Any) -> str:
    return json.dumps(values, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _minute_utc(value: datetime) -> str:
    return _aware(value).strftime("%Y-%m-%d %H:%M")


def _within_window(left: datetime, right: datetime, window: timedelta) -> bool:
    return abs(_aware(left) - _aware(right)) <= window


def _compare_network(alert: ThirdPartyAlert, activity: DeviceActivity) -> str:
    if activity.network_class == "vpn" or alert.claimed_network_class == "vpn":
        return NETWORK_VPN_POSSIBLE
    if alert.network_fingerprint and activity.network_fingerprint:
        if alert.network_fingerprint == activity.network_fingerprint:
            return NETWORK_SAME
        return NETWORK_DIFFERENT
    if (
        alert.claimed_network_class
        and alert.claimed_network_class != "unknown"
        and activity.network_class != "unknown"
    ):
        if alert.claimed_network_class == activity.network_class:
            return NETWORK_SAME
        return NETWORK_DIFFERENT
    return NETWORK_UNKNOWN


def _require_device_id(value: str) -> str:
    value = value.strip().lower()
    if not _DEVICE_ID_RE.fullmatch(value):
        raise CorrelationError("device_id_not_bound")
    return value


def _require_hex_ref(value: str, field: str) -> str:
    value = value.strip().lower()
    if not _HEX_REF_RE.fullmatch(value):
        raise CorrelationError(f"{field}_invalid")
    return value


def _optional_hex_ref(value: Any, field: str) -> str | None:
    if value in (None, ""):
        return None
    return _require_hex_ref(str(value), field)


def _require_service_id(value: str) -> str:
    value = value.strip().lower()
    if not _SERVICE_ID_RE.fullmatch(value):
        raise CorrelationError("service_id_invalid")
    return value


def _require_display_label(value: str) -> str:
    label = value.strip()
    if not 1 <= len(label) <= 64:
        raise CorrelationError("display_label_invalid")
    _reject_network_plaintext(label)
    if "://" in label or "/" in label:
        raise CorrelationError("display_label_invalid")
    return label


def _require_source_label(value: str) -> str:
    label = " ".join(value.split())
    if not 3 <= len(label) <= 80:
        raise CorrelationError("source_label_invalid")
    _reject_network_plaintext(label)
    return label


def _require_choice(value: Any, allowed: Iterable[str], field: str) -> str:
    text = str(value or "").strip()
    if text not in set(allowed):
        raise CorrelationError(f"{field}_invalid")
    return text


def _reject_forbidden_payload(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        lowered = str(key).lower()
        if lowered in FORBIDDEN_FIELD_NAMES:
            raise CorrelationError(f"forbidden_field:{lowered}")
        if isinstance(value, str):
            _reject_network_plaintext(value)
            if lowered in {"url", "href", "history"}:
                raise CorrelationError(f"forbidden_field:{lowered}")


def _reject_network_plaintext(value: str) -> None:
    if _IPV4_RE.search(value) or _IPV6_RE.search(value):
        raise CorrelationError("plaintext_ip_forbidden")


def make_device_id(public_key_bytes: bytes) -> str:
    """Bind a device the same way DeviceIdentity derives lumos_id."""
    return hashlib.sha256(public_key_bytes).hexdigest()
