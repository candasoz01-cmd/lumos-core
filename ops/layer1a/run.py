#!/usr/bin/env python3
"""Layer 1A: five deterministic, read-only production checks.

Stdlib only. No secrets, LLM, panel writes, or notifications.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
from urllib.parse import urljoin

SCHEMA = "lumos.ops.layer1a.v1"
DEFAULT_BASE_URL = "https://welockai.com"
DEFAULT_TIMEOUT_SECONDS = 15
USER_AGENT = "lumos-ops-layer1a/1.0"

BRIDGE_FAIL_CLOSED_ERRORS = frozenset(
    {
        "bridge_proxy_unconfigured",
        "bridge_proxy_auth_unconfigured",
        "bridge_proxy_secret_unconfigured",
        "bridge_proxy_unauthorized",
    }
)
SECRET_KEY_NAMES = frozenset(
    {
        "access_token",
        "api_key",
        "client_secret",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)

FetchFn = Callable[[str], tuple[int, str, bytes]]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_base_url(raw: str) -> str:
    base = raw.strip().rstrip("/")
    if not base:
        raise ValueError("base URL empty")
    return base


def default_fetch(url: str, timeout: float) -> tuple[int, str, bytes]:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            content_type = str(response.headers.get("Content-Type") or "")
            return int(response.status), content_type, body
    except urllib.error.HTTPError as exc:
        body = exc.read()
        content_type = str(exc.headers.get("Content-Type") or "") if exc.headers else ""
        return int(exc.code), content_type, body


def _http_200(status: int, _content_type: str, _body: bytes) -> str | None:
    if status != 200:
        return f"expected HTTP 200, got {status}"
    return None


def _auth_readiness(status: int, _content_type: str, body: bytes) -> str | None:
    if status != 200:
        return f"expected HTTP 200, got {status}"
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return f"readiness body is not JSON: {exc}"
    if not isinstance(payload, dict):
        return "readiness JSON must be an object"
    if payload.get("ok") is not True:
        return "readiness ok is not true"
    leaked = _secret_leak(payload)
    if leaked:
        return leaked
    prefix = payload.get("client_id_prefix")
    if prefix is not None and (not isinstance(prefix, str) or len(prefix) > 8):
        return "client_id_prefix must be a string of at most 8 characters"
    return None


def _bridge_fail_closed(status: int, _content_type: str, body: bytes) -> str | None:
    if status == 200:
        return "bridge proxy returned 200; expected fail-closed 401 or 503"
    if status not in {401, 503}:
        return f"expected HTTP 401 or 503, got {status}"
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return f"bridge body is not JSON: {exc}"
    if not isinstance(payload, dict):
        return "bridge JSON must be an object"
    error = payload.get("error")
    if error not in BRIDGE_FAIL_CLOSED_ERRORS:
        return f"unexpected bridge error {error!r}"
    leaked = _secret_leak(payload)
    if leaked:
        return leaked
    return None


def _secret_leak(payload: Mapping[str, Any]) -> str | None:
    for key, value in payload.items():
        lowered = str(key).lower()
        if lowered in SECRET_KEY_NAMES and value not in (None, False, True, "", 0):
            return f"forbidden secret field present: {key}"
        if lowered.endswith("_secret") and isinstance(value, str) and value:
            return f"forbidden secret field present: {key}"
    return None


CHECKS: tuple[tuple[str, str, Callable[[int, str, bytes], str | None]], ...] = (
    ("landing", "/", _http_200),
    ("panel", "/panel", _http_200),
    ("integrations", "/integrations", _http_200),
    ("auth_readiness", "/auth/readiness", _auth_readiness),
    ("bridge_fail_closed", "/api/bridge/task", _bridge_fail_closed),
)


def run_checks(
    *,
    base_url: str,
    fetch: FetchFn,
    checked_at: str | None = None,
) -> dict[str, Any]:
    base = normalize_base_url(base_url)
    results: list[dict[str, Any]] = []
    for check_id, path, evaluate in CHECKS:
        url = urljoin(base + "/", path.lstrip("/"))
        entry: dict[str, Any] = {
            "id": check_id,
            "ok": False,
            "url": url,
            "method": "GET",
        }
        try:
            status, content_type, body = fetch(url)
            entry["status"] = status
            reason = evaluate(status, content_type, body)
            if reason is None:
                entry["ok"] = True
            else:
                entry["detail"] = reason
        except Exception as exc:  # noqa: BLE001 — pulse must never crash the artifact
            entry["detail"] = f"request failed: {type(exc).__name__}: {exc}"
        results.append(entry)
    overall = "pass" if all(item["ok"] for item in results) else "fail"
    return {
        "schema": SCHEMA,
        "checked_at": checked_at or utc_now(),
        "base_url": base,
        "overall": overall,
        "checks": results,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="ops/layer1a/run.py")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LAYER1A_BASE_URL", DEFAULT_BASE_URL),
    )
    parser.add_argument("--output")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    timeout = args.timeout

    def fetch(url: str) -> tuple[int, str, bytes]:
        return default_fetch(url, timeout)

    report = run_checks(base_url=args.base_url, fetch=fetch)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(encoded)
    else:
        sys.stdout.write(encoded)
    return 0 if report["overall"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
