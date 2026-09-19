"""Credentialed adapter for the official Ring Partner API.

Counterpart to `ring_simulator.RingSandboxSimulator`: same caller-facing
envelope (`path` / `execution_live` / `document` / singular `error`), but this
module DOES open a network socket to `https://api.amazonvision.com` when a
token is provided. Without a token it fails closed and never touches the
network. The token comes from the Ring Developer Playground ("Generate Token",
short-lived ~30 min) via the `RING_API_TOKEN` environment variable or an
explicit argument; it is never logged and never placed in returned envelopes.

Live envelopes carry `origin_contacted` (the sandbox carries
`origin_not_contacted`) so a reader can always tell which world produced a
payload. The JSON:API response body is passed through unmodified under
`document`; this module validates transport-level outcomes only.

Reference: Ring Partner API (`GET /v1/devices`, `GET /v1/devices/{id}/status`).
Starter sample: AmazonAppDev/ring-api-helloworld.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from amazon_hackathon.ring_simulator import (
    AMAZON_VISION_API_ORIGIN,
    DEVICES_PATH,
    public_device_id,
)

RING_TOKEN_ENV = "RING_API_TOKEN"
REQUEST_TIMEOUT_SECONDS = 10.0

# transport(url, headers, timeout) -> (http_status, body_bytes)
Transport = Callable[[str, dict[str, str], float], tuple[int, bytes]]


def _urllib_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def token_from_env() -> str | None:
    token = os.environ.get(RING_TOKEN_ENV, "").strip()
    return token or None


@dataclass
class RingLiveAdapter:
    """Live `GET`-only client: device list and device status, nothing else."""

    token: str | None = None
    transport: Transport = _urllib_transport
    origin: str = AMAZON_VISION_API_ORIGIN

    def _envelope(
        self,
        *,
        path: str,
        document: dict[str, Any] | None,
        contacted: bool,
        http_status: int | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        origin_key = "origin_contacted" if contacted else "origin_not_contacted"
        envelope: dict[str, Any] = {
            "path": path,
            origin_key: self.origin,
            "execution_live": contacted,
            "document": document if document is not None else {},
        }
        if http_status is not None:
            envelope["http_status"] = http_status
        if error is not None:
            envelope["error"] = error
        return envelope

    def _get(self, path: str, *, not_found_error: str) -> dict[str, Any]:
        if not self.token:
            # Fail closed: no token, no socket. The transport is never called.
            return self._envelope(
                path=path, document=None, contacted=False, error="ring_token_missing"
            )
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            status, body = self.transport(f"{self.origin}{path}", headers, REQUEST_TIMEOUT_SECONDS)
        except Exception:
            return self._envelope(path=path, document=None, contacted=True, error="network_error")
        try:
            document = json.loads(body.decode("utf-8")) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            document = {}
            if 200 <= status < 300:
                return self._envelope(
                    path=path, document=None, contacted=True, http_status=status, error="invalid_json"
                )
        if not isinstance(document, dict):
            return self._envelope(
                path=path, document=None, contacted=True, http_status=status, error="invalid_json"
            )
        if status in (401, 403):
            return self._envelope(
                path=path,
                document=document,
                contacted=True,
                http_status=status,
                error="token_expired_or_invalid",
            )
        if status == 404:
            return self._envelope(
                path=path, document=document, contacted=True, http_status=status, error=not_found_error
            )
        if not 200 <= status < 300:
            return self._envelope(
                path=path, document=document, contacted=True, http_status=status, error=f"http_{status}"
            )
        return self._envelope(path=path, document=document, contacted=True, http_status=status)

    def list_devices(self) -> dict[str, Any]:
        return self._get(DEVICES_PATH, not_found_error="devices_endpoint_not_found")

    def device_status(self, device_id: str) -> dict[str, Any]:
        public_id = public_device_id(device_id)
        return self._get(
            f"{DEVICES_PATH}/{public_id}/status", not_found_error="device_not_found"
        )


def _main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Call the official Ring Partner API (read-only: list/status)."
    )
    parser.add_argument("command", choices=["list", "status"])
    parser.add_argument("device_id", nargs="?", default=None)
    args = parser.parse_args(argv)

    adapter = RingLiveAdapter(token=token_from_env())
    if args.command == "status":
        if not args.device_id:
            parser.error("status requires a device_id")
        result = adapter.device_status(args.device_id)
    else:
        result = adapter.list_devices()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if "error" not in result else 1


if __name__ == "__main__":  # pragma: no cover - exercised manually for the demo
    import sys

    raise SystemExit(_main(sys.argv[1:]))
