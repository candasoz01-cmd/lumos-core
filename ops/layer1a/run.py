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
from urllib.parse import urljoin, urlparse

SCHEMA = "lumos.ops.layer1a.v1"
STATE_SCHEMA = "lumos.ops.layer1a.state.v1"
DEFAULT_BASE_URL = "https://welockai.com"
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_STALE_AFTER_SECONDS = 3600
DEFAULT_MAX_BODY_BYTES = 1_048_576
ALLOWED_HOSTS = frozenset({"welockai.com"})
USER_AGENT = "lumos-ops-layer1a/1.0"
HTTPS_SCHEME = "https"
HTTPS_PORT = 443

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


class UnsafeURLError(ValueError):
    """Raised when a URL is not HTTPS to an allowlisted host, or redirects away."""


class ResponseTooLargeError(ValueError):
    """Raised when a response body exceeds the Layer 1A size cap."""


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


def _hostname(parsed: Any) -> str:
    return (parsed.hostname or "").strip().lower().rstrip(".")


def _origin(parsed: Any) -> tuple[str, str, int]:
    scheme = (parsed.scheme or "").lower()
    host = _hostname(parsed)
    port = parsed.port
    if port is None:
        port = HTTPS_PORT if scheme == HTTPS_SCHEME else 80
    return scheme, host, port


def assert_safe_url(
    raw: str, *, expected_origin: tuple[str, str, int] | None = None
) -> str:
    """Return a stripped HTTPS URL or raise UnsafeURLError.

    When expected_origin is set, the URL must match that origin exactly
    (scheme, allowlisted host, port). Used to reject cross-origin redirects.
    """
    text = raw.strip()
    if not text:
        raise UnsafeURLError("URL empty")
    parsed = urlparse(text)
    scheme, host, port = _origin(parsed)
    if scheme != HTTPS_SCHEME:
        raise UnsafeURLError(f"URL scheme must be https, got {scheme!r}")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURLError("URL must not include userinfo")
    if not host or host not in ALLOWED_HOSTS:
        raise UnsafeURLError(f"host {host!r} is not allowlisted")
    if port != HTTPS_PORT:
        raise UnsafeURLError(f"non-default HTTPS port is not allowed: {port}")
    origin = (scheme, host, port)
    if expected_origin is not None and origin != expected_origin:
        raise UnsafeURLError(
            f"cross-origin redirect rejected: {expected_origin} -> {origin}"
        )
    return text


def normalize_base_url(raw: str) -> str:
    base = raw.strip().rstrip("/")
    if not base:
        raise ValueError("base URL empty")
    parsed = urlparse(base)
    if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
        raise UnsafeURLError(
            "base URL must be an https origin without path, query, or fragment"
        )
    return assert_safe_url(base).rstrip("/")


def read_limited(response: Any, limit: int = DEFAULT_MAX_BODY_BYTES) -> bytes:
    headers = getattr(response, "headers", None)
    declared = None
    if headers is not None:
        raw_length = headers.get("Content-Length")
        if raw_length is not None:
            try:
                declared = int(raw_length)
            except (TypeError, ValueError):
                declared = None
            else:
                if declared < 0:
                    declared = None
    if declared is not None and declared > limit:
        raise ResponseTooLargeError(
            f"response too large: Content-Length {declared} > {limit}"
        )
    chunks: list[bytes] = []
    total = 0
    while True:
        remaining_plus = limit - total + 1
        chunk = response.read(min(65536, remaining_plus))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ResponseTooLargeError(
                f"response too large: exceeded {limit} bytes"
            )
        chunks.append(chunk)
    return b"".join(chunks)


class SameOriginHTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow redirects only when the target is HTTPS to the same allowlisted origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        origin = _origin(urlparse(req.full_url))
        assert_safe_url(newurl, expected_origin=origin)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _https_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(SameOriginHTTPSRedirectHandler)


def default_fetch(
    url: str,
    timeout: float,
    *,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> tuple[int, str, bytes]:
    safe = assert_safe_url(url)
    request = urllib.request.Request(
        safe,
        method="GET",
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    opener = _https_opener()
    try:
        with opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
            assert_safe_url(final_url, expected_origin=_origin(urlparse(safe)))
            body = read_limited(response, max_body_bytes)
            content_type = str(response.headers.get("Content-Type") or "")
            return int(response.status), content_type, body
    except urllib.error.HTTPError as exc:
        if exc.url:
            assert_safe_url(str(exc.url), expected_origin=_origin(urlparse(safe)))
        body = read_limited(exc, max_body_bytes) if exc.fp is not None else b""
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


CHECK_IDS = tuple(item[0] for item in CHECKS)


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


def age_seconds_between(generated_at: str, last_success_at: str | None) -> int | None:
    generated = parse_utc(generated_at)
    prior = parse_utc(last_success_at) if isinstance(last_success_at, str) else None
    if generated is None or prior is None:
        return None
    return int((generated - prior).total_seconds())


def decide_overall(
    checks: list[Mapping[str, Any]],
    *,
    now: datetime,
    stale_after_seconds: int,
) -> str:
    results = [str(item.get("result")) for item in checks]
    if any(item == RESULT_FAIL for item in results):
        return RESULT_FAIL
    if all(item == RESULT_PASS for item in results):
        return RESULT_PASS
    for item in checks:
        if item.get("result") != RESULT_UNKNOWN:
            continue
        prior = item.get("last_success_at")
        if isinstance(prior, str) and last_success_is_stale(
            prior, now=now, stale_after_seconds=stale_after_seconds
        ):
            return OVERALL_STALE
    return RESULT_UNKNOWN


def load_state(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.loads(handle.read())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("schema") != STATE_SCHEMA:
        return {}
    raw = payload.get("last_success_at")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for check_id in CHECK_IDS:
        value = raw.get(check_id)
        if isinstance(value, str) and parse_utc(value) is not None:
            out[check_id] = value
    return out


def save_state(path: str | None, last_success_at: Mapping[str, str | None]) -> None:
    if not path:
        return
    stored = {
        check_id: last_success_at[check_id]
        for check_id in CHECK_IDS
        if isinstance(last_success_at.get(check_id), str)
        and parse_utc(str(last_success_at[check_id])) is not None
    }
    payload = {
        "schema": STATE_SCHEMA,
        "last_success_at": stored,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(encoded)


def run_checks(
    *,
    base_url: str,
    fetch: FetchFn,
    checked_at: str | None = None,
    last_success_at: Mapping[str, str] | None = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
    now: datetime | None = None,
    generated_at: str | None = None,
    run_attempt: int = 1,
) -> dict[str, Any]:
    base = normalize_base_url(base_url)
    moment = now or utc_now()
    checked = checked_at or format_utc(moment)
    previous: dict[str, str] = {}
    if isinstance(last_success_at, Mapping):
        for check_id in CHECK_IDS:
            value = last_success_at.get(check_id)
            if isinstance(value, str) and parse_utc(value) is not None:
                previous[check_id] = value

    results: list[dict[str, Any]] = []
    origin = _origin(urlparse(base))
    for check_id, path, evaluate in CHECKS:
        url = urljoin(base + "/", path.lstrip("/"))
        prior = previous.get(check_id)
        if not isinstance(prior, str) or parse_utc(prior) is None:
            prior = None
        entry: dict[str, Any] = {
            "id": check_id,
            "ok": False,
            "result": RESULT_UNKNOWN,
            "url": url,
            "method": "GET",
            "last_success_at": prior,
        }
        try:
            assert_safe_url(url, expected_origin=origin)
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
        if entry["result"] == RESULT_PASS:
            entry["last_success_at"] = checked
        results.append(entry)

    generated = generated_at or format_utc(moment)
    for item in results:
        item["age_seconds"] = age_seconds_between(generated, item.get("last_success_at"))

    overall = decide_overall(
        results,
        now=moment,
        stale_after_seconds=stale_after_seconds,
    )
    persisted = {
        item["id"]: item["last_success_at"]
        for item in results
        if isinstance(item.get("last_success_at"), str)
    }
    return {
        "schema": SCHEMA,
        "checked_at": checked,
        "generated_at": generated,
        "run_attempt": run_attempt,
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
        help="JSON file that persists per-check last_success_at across runs",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--stale-after",
        type=int,
        default=DEFAULT_STALE_AFTER_SECONDS,
        help="seconds after a check's last_success_at when overall becomes stale",
    )
    parser.add_argument(
        "--run-attempt",
        type=int,
        default=int(os.environ.get("GITHUB_RUN_ATTEMPT") or "1"),
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
        run_attempt=args.run_attempt,
    )
    persisted = {
        item["id"]: item.get("last_success_at") for item in report["checks"]
    }
    save_state(args.state, persisted)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(encoded)
    else:
        sys.stdout.write(encoded)
    return 0 if report["overall"] == RESULT_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
