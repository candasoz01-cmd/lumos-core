#!/usr/bin/env python3
"""Layer 1A: five deterministic, read-only production checks.

Stdlib only. No secrets, LLM, panel writes, or first-party notifications.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping
from urllib.parse import urljoin

SCHEMA = "lumos.ops.layer1a.v1"
STATE_SCHEMA = "lumos.ops.layer1a.state.v1"
DEFAULT_BASE_URL = "https://welockai.com"
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_STALE_AFTER_SECONDS = 3600
USER_AGENT = "lumos-ops-layer1a/1.0"

RESULT_PASS = "pass"
RESULT_FAIL = "fail"
RESULT_UNKNOWN = "unknown"
OVERALL_STALE = "stale"

BRIDGE_PASS_ERROR = "bridge_proxy_unauthorized"
CheckOutcome = tuple[str, str | None]
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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(raw: str) -> datetime | None:
    text = raw.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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


def _http_200(status: int, _content_type: str, _body: bytes) -> CheckOutcome:
    if status != 200:
        return RESULT_FAIL, f"expected HTTP 200, got {status}"
    return RESULT_PASS, None


def _auth_readiness(status: int, _content_type: str, body: bytes) -> CheckOutcome:
    if status != 200:
        return RESULT_FAIL, f"expected HTTP 200, got {status}"
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return RESULT_FAIL, f"readiness body is not JSON: {exc}"
    if not isinstance(payload, dict):
        return RESULT_FAIL, "readiness JSON must be an object"
    if payload.get("ok") is not True:
        return RESULT_FAIL, "readiness ok is not true"
    leaked = _secret_leak(payload)
    if leaked:
        return RESULT_FAIL, leaked
    prefix = payload.get("client_id_prefix")
    if prefix is not None and (not isinstance(prefix, str) or len(prefix) > 8):
        return RESULT_FAIL, "client_id_prefix must be a string of at most 8 characters"
    return RESULT_PASS, None


def _bridge_fail_closed(status: int, _content_type: str, body: bytes) -> CheckOutcome:
    # Explicit exception to unexpected-HTTP → fail: classify 503 as unknown first.
    if status == 503:
        return RESULT_UNKNOWN, "bridge HTTP 503 is unknown"
    if status == 200:
        return RESULT_FAIL, "bridge proxy returned 200; expected fail-closed 401"
    if status != 401:
        return RESULT_FAIL, f"expected HTTP 401, got {status}"
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return RESULT_FAIL, f"bridge body is not JSON: {exc}"
    if not isinstance(payload, dict):
        return RESULT_FAIL, "bridge JSON must be an object"
    error = payload.get("error")
    if error != BRIDGE_PASS_ERROR:
        return RESULT_FAIL, f"unexpected bridge error {error!r}"
    leaked = _secret_leak(payload)
    if leaked:
        return RESULT_FAIL, leaked
    return RESULT_PASS, None


def _secret_leak(payload: Mapping[str, Any]) -> str | None:
    for key, value in payload.items():
        lowered = str(key).lower()
        if lowered in SECRET_KEY_NAMES and value not in (None, False, True, "", 0):
            return f"forbidden secret field present: {key}"
        if lowered.endswith("_secret") and isinstance(value, str) and value:
            return f"forbidden secret field present: {key}"
    return None


CHECKS: tuple[tuple[str, str, Callable[[int, str, bytes], CheckOutcome]], ...] = (
    ("landing", "/", _http_200),
    ("panel", "/panel", _http_200),
    ("integrations", "/integrations", _http_200),
    ("auth_readiness", "/auth/readiness", _auth_readiness),
    ("bridge_fail_closed", "/api/bridge/task", _bridge_fail_closed),
)


def last_success_is_stale(
    last_success_at: str | None,
    *,
    now: datetime,
    stale_after_seconds: int,
) -> bool:
    parsed = parse_utc(last_success_at) if last_success_at else None
    if parsed is None:
        return False
    return now - parsed > timedelta(seconds=stale_after_seconds)


def decide_overall(
    results: list[str],
    *,
    last_success_at: str | None,
    now: datetime,
    stale_after_seconds: int,
) -> str:
    if any(item == RESULT_FAIL for item in results):
        return RESULT_FAIL
    if all(item == RESULT_PASS for item in results):
        return RESULT_PASS
    if last_success_is_stale(
        last_success_at, now=now, stale_after_seconds=stale_after_seconds
    ):
        return OVERALL_STALE
    return RESULT_UNKNOWN


def load_state(path: str | None) -> str | None:
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.loads(handle.read())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != STATE_SCHEMA:
        return None
    value = payload.get("last_success_at")
    if not isinstance(value, str) or parse_utc(value) is None:
        return None
    return value


def save_state(path: str | None, last_success_at: str | None) -> None:
    if not path:
        return
    payload = {
        "schema": STATE_SCHEMA,
        "last_success_at": last_success_at,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(encoded)


def run_checks(
    *,
    base_url: str,
    fetch: FetchFn,
    checked_at: str | None = None,
    last_success_at: str | None = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    base = normalize_base_url(base_url)
    moment = now or utc_now()
    checked = checked_at or format_utc(moment)
    results: list[dict[str, Any]] = []
    for check_id, path, evaluate in CHECKS:
        url = urljoin(base + "/", path.lstrip("/"))
        entry: dict[str, Any] = {
            "id": check_id,
            "ok": False,
            "result": RESULT_UNKNOWN,
            "url": url,
            "method": "GET",
        }
        try:
            status, content_type, body = fetch(url)
            entry["status"] = status
            result, detail = evaluate(status, content_type, body)
            entry["result"] = result
            entry["ok"] = result == RESULT_PASS
            if detail:
                entry["detail"] = detail
        except Exception as exc:  # noqa: BLE001 — pulse must still emit an artifact
            entry["result"] = RESULT_UNKNOWN
            entry["detail"] = f"request failed: {type(exc).__name__}: {exc}"
        results.append(entry)

    overall = decide_overall(
        [item["result"] for item in results],
        last_success_at=last_success_at,
        now=moment,
        stale_after_seconds=stale_after_seconds,
    )
    persisted = checked if overall == RESULT_PASS else last_success_at
    return {
        "schema": SCHEMA,
        "checked_at": checked,
        "base_url": base,
        "overall": overall,
        "last_success_at": persisted,
        "stale_after_seconds": stale_after_seconds,
        "checks": results,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="ops/layer1a/run.py")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LAYER1A_BASE_URL", DEFAULT_BASE_URL),
    )
    parser.add_argument("--output")
    parser.add_argument(
        "--state",
        help="JSON file that persists last_success_at across runs",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--stale-after",
        type=int,
        default=DEFAULT_STALE_AFTER_SECONDS,
        help="seconds after last_success_at when overall becomes stale",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    timeout = args.timeout
    previous = load_state(args.state)

    def fetch(url: str) -> tuple[int, str, bytes]:
        return default_fetch(url, timeout)

    report = run_checks(
        base_url=args.base_url,
        fetch=fetch,
        last_success_at=previous,
        stale_after_seconds=args.stale_after,
    )
    save_state(args.state, report.get("last_success_at"))
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(encoded)
    else:
        sys.stdout.write(encoded)
    return 0 if report["overall"] == RESULT_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
