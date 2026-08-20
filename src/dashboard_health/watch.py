"""Standing shift for bridge.llm → Observe.

Trigger → probe (optional URL, no credentials) → dashboard-health-v1 card →
evidence. Report only when the state needs a human glance. Not Fix. Not Layer 1-A.
Not the other 17 cards.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

from dashboard_health.bridge_llm import (
    CARD_ID,
    apply_freshness,
    card_from_http,
    unprobed_card,
)

SCHEMA = "lumos.dashboard_health.observe_shift.v1"
USER_AGENT = "lumos-bridge-llm-observe/1.0"
DEFAULT_TIMEOUT_SECONDS = 8
REPORT_STATES = frozenset({"failed", "stale", "not_configured"})
FetchFn = Callable[[str, float], tuple[int | None, dict[str, Any] | None]]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def health_url_from_env() -> str:
    return (os.environ.get("LUMOS_BRIDGE_HEALTH_URL") or "").strip()


def is_http_url(raw: str) -> bool:
    parsed = urlparse(raw)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def default_fetch(url: str, timeout: float) -> tuple[int | None, dict[str, Any] | None]:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 0) or 0)
            raw = response.read()
    except urllib.error.HTTPError as err:
        status = int(err.code)
        raw = err.read() if err.fp is not None else b""
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None
    body: dict[str, Any] | None
    try:
        parsed = json.loads(raw.decode("utf-8") or "null")
        body = parsed if isinstance(parsed, dict) else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = None
    return status, body


def run_shift(
    *,
    url: str = "",
    previous: dict[str, Any] | None = None,
    now: datetime | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    fetch: FetchFn = default_fetch,
) -> dict[str, Any]:
    """One observe tick. Empty url = not_checked (no probe started)."""
    stamp = now or utc_now()
    if not url:
        card = apply_freshness(unprobed_card(), stamp)
        probed = False
    elif not is_http_url(url):
        card = apply_freshness(unprobed_card(), stamp)
        card = dict(card)
        card["reason_code"] = "unmapped_value"
        card["evidence"] = "GET skipped: health URL is not http(s)"
        probed = False
    else:
        status, body = fetch(url, timeout)
        card = apply_freshness(card_from_http(status, body, fetched_at=stamp), stamp)
        probed = True
    prev_card = None
    if isinstance(previous, dict):
        prev_card = previous.get("card") if "card" in previous else previous
        if not isinstance(prev_card, dict):
            prev_card = None
    report = should_report(card, prev_card)
    return {
        "schema": SCHEMA,
        "grant_id": "DH-BRIDGE-LLM-OBSERVE",
        "action_class": "Observe",
        "data_scope": CARD_ID,
        "probed": probed,
        "report": report,
        "observed_at": iso(stamp),
        "card": card,
        "boundary": {
            "fix": False,
            "remediate": False,
            "other_cards": False,
            "credentials_chased": False,
        },
    }


def should_report(card: dict[str, Any], previous_card: dict[str, Any] | None) -> bool:
    state = str(card.get("state") or "")
    if state in REPORT_STATES:
        return True
    if previous_card is None:
        return False
    return (previous_card.get("state"), previous_card.get("reason_code")) != (
        card.get("state"),
        card.get("reason_code"),
    )


def load_previous(path: str) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        payload = json.loads(open(path, encoding="utf-8").read())
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def write_json(path: str, payload: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m dashboard_health.watch")
    parser.add_argument(
        "--url",
        default="",
        help="GET target. Empty skips the probe (not_checked). Never sends credentials.",
    )
    parser.add_argument("--output", default="")
    parser.add_argument("--state", default="", help="Previous shift JSON (for report-on-change).")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)
    url = args.url.strip() or health_url_from_env()
    previous = load_previous(args.state)
    result = run_shift(url=url, previous=previous, timeout=args.timeout)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    sys.stdout.write(text + "\n")
    if args.output:
        write_json(args.output, result)
    if args.state:
        write_json(args.state, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
