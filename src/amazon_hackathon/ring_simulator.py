"""Offline Ring sandbox shaped like the Amazon Vision Partner API.

Official live host is `https://api.amazonvision.com`. This module never opens a
network socket. List/status *documents* follow the published JSON:API contract
so a later credentialed adapter can replace the sandbox without changing
callers.

Return shape for list/status is a Lumos sandbox envelope, not a live Amazon
payload: honesty keys (`execution_live`, `origin_not_contacted`, `path`) and
the provider's singular `error` sit on the envelope. The JSON:API object is
`document` only (`meta` / `data` / `errors`). See jsonapi.org document-structure.

Reference: Ring Partner API device discovery (`GET /v1/devices`) and status
(`GET /v1/devices/{id}/status`). Starter sample: AmazonAppDev/ring-api-helloworld.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


AMAZON_VISION_API_ORIGIN = "https://api.amazonvision.com"
DEVICES_PATH = "/v1/devices"
LIVE_EXECUTION = False
JSONAPI_DEVICE_TYPE = "devices"
JSONAPI_STATUS_TYPE = "device-status"
JSONAPI_DOCUMENT_MEMBERS = frozenset({"data", "errors", "meta", "jsonapi", "links", "included"})
PUBLIC_DEVICE_PREFIX = "ava1.ring.device."


def _utc_meta_time() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def public_device_id(internal_id: str) -> str:
    if internal_id.startswith(PUBLIC_DEVICE_PREFIX):
        return internal_id
    return f"{PUBLIC_DEVICE_PREFIX}{internal_id}"


def public_status_id(internal_id: str) -> str:
    suffix = internal_id
    if suffix.startswith(PUBLIC_DEVICE_PREFIX):
        suffix = suffix[len(PUBLIC_DEVICE_PREFIX) :]
    return f"{PUBLIC_DEVICE_PREFIX}status.{suffix}"


def _internal_id(device_id: str) -> str:
    if device_id.startswith(PUBLIC_DEVICE_PREFIX):
        return device_id[len(PUBLIC_DEVICE_PREFIX) :]
    return device_id


def _jsonapi_document(**members: Any) -> dict[str, Any]:
    extra = set(members) - JSONAPI_DOCUMENT_MEMBERS
    if extra:
        raise ValueError(f"jsonapi_forbidden_members:{sorted(extra)}")
    return {"meta": {"time": _utc_meta_time()}, **members}


def _sandbox_envelope(
    *,
    path: str,
    document: dict[str, Any],
    error: str | None = None,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "path": path,
        "origin_not_contacted": AMAZON_VISION_API_ORIGIN,
        "execution_live": LIVE_EXECUTION,
        "document": document,
    }
    if error is not None:
        envelope["error"] = error
    return envelope


@dataclass(frozen=True)
class RingEvent:
    event_id: str
    device_id: str
    kind: str
    summary: str


@dataclass
class RingSandboxSimulator:
    """Synthetic doorbell + camera. No Ring account, no video, no unlock."""

    _devices: dict[str, dict[str, Any]] = field(default_factory=dict)
    _events: list[RingEvent] = field(default_factory=list)
    _event_seq: int = 0

    def __post_init__(self) -> None:
        if not self._devices:
            self._devices = {
                "sim-doorbell-front": {
                    "id": "sim-doorbell-front",
                    "type": "doorbell",
                    "attributes": {
                        "name": "Front Door",
                        "online": True,
                        "locked": True,
                    },
                },
                "sim-camera-driveway": {
                    "id": "sim-camera-driveway",
                    "type": "camera",
                    "attributes": {
                        "name": "Driveway",
                        "online": True,
                    },
                },
            }

    def _lookup(self, device_id: str) -> tuple[str, dict[str, Any]] | None:
        internal = _internal_id(device_id)
        device = self._devices.get(internal)
        if device is None:
            return None
        return internal, device

    def _device_resource(self, internal_id: str, device: dict[str, Any]) -> dict[str, Any]:
        public_id = public_device_id(internal_id)
        return {
            "type": JSONAPI_DEVICE_TYPE,
            "id": public_id,
            "attributes": {"name": device["attributes"].get("name")},
            "relationships": {
                "status": {
                    "data": {"type": JSONAPI_STATUS_TYPE, "id": public_status_id(internal_id)},
                    "links": {"related": f"{DEVICES_PATH}/{public_id}/status"},
                },
                "capabilities": {
                    "data": {
                        "type": "device-capabilities",
                        "id": f"{PUBLIC_DEVICE_PREFIX}capabilities.{internal_id}",
                    },
                    "links": {"related": f"{DEVICES_PATH}/{public_id}/capabilities"},
                },
                "configurations": {
                    "data": {
                        "type": "device-configurations",
                        "id": f"{PUBLIC_DEVICE_PREFIX}configurations.{internal_id}",
                    },
                    "links": {"related": f"{DEVICES_PATH}/{public_id}/configurations"},
                },
                "location": {
                    "data": {
                        "type": "locations",
                        "id": f"{PUBLIC_DEVICE_PREFIX}location.{internal_id}",
                    },
                    "links": {"related": f"{DEVICES_PATH}/{public_id}/location"},
                },
            },
        }

    def list_devices(self) -> dict[str, Any]:
        return _sandbox_envelope(
            path=DEVICES_PATH,
            document=_jsonapi_document(
                data=[
                    self._device_resource(internal_id, device)
                    for internal_id, device in self._devices.items()
                ]
            ),
        )

    def device_status(self, device_id: str) -> dict[str, Any]:
        found = self._lookup(device_id)
        public_id = public_device_id(device_id)
        path = f"{DEVICES_PATH}/{public_id}/status"
        if found is None:
            return _sandbox_envelope(
                path=path,
                document=_jsonapi_document(
                    errors=[
                        {
                            "status": "404",
                            "title": "Not Found",
                            "detail": "The requested resource could not be found",
                        }
                    ]
                ),
                error="device_not_found",
            )
        internal_id, device = found
        return _sandbox_envelope(
            path=path,
            document=_jsonapi_document(
                data={
                    "type": JSONAPI_STATUS_TYPE,
                    "id": public_status_id(internal_id),
                    "attributes": {"online": bool(device["attributes"].get("online"))},
                }
            ),
        )

    def inject_event(self, device_id: str, kind: str, summary: str) -> dict[str, Any]:
        if device_id not in self._devices:
            return {"ok": False, "error": "device_not_found", "execution_live": LIVE_EXECUTION}
        self._event_seq += 1
        event = RingEvent(
            event_id=f"evt-{self._event_seq}",
            device_id=device_id,
            kind=kind,
            summary=summary,
        )
        self._events.append(event)
        return {
            "ok": True,
            "execution_live": LIVE_EXECUTION,
            "event": {
                "event_id": event.event_id,
                "device_id": event.device_id,
                "kind": event.kind,
                "summary": event.summary,
            },
        }

    def latest_event(self) -> dict[str, Any]:
        if not self._events:
            return {"execution_live": LIVE_EXECUTION, "event": None}
        event = self._events[-1]
        return {
            "execution_live": LIVE_EXECUTION,
            "event": {
                "event_id": event.event_id,
                "device_id": event.device_id,
                "kind": event.kind,
                "summary": event.summary,
            },
        }

    def request_unlock(self, device_id: str, *, approved: bool) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if device is None:
            return {"ok": False, "error": "device_not_found", "execution_live": LIVE_EXECUTION}
        if device["type"] != "doorbell":
            return {"ok": False, "error": "unlock_not_supported", "execution_live": LIVE_EXECUTION}
        if not approved:
            return {
                "ok": False,
                "error": "approval_required",
                "execution_live": LIVE_EXECUTION,
                "execution_started": False,
            }
        # Sandbox never changes lock state to unlocked: demo of the gate only.
        return {
            "ok": False,
            "error": "sandbox_unlock_not_executed",
            "execution_live": LIVE_EXECUTION,
            "execution_started": False,
            "reason": "simulator_does_not_actuate_locks",
        }
