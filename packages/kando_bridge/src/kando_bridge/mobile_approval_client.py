"""
Lumos Mobile approval CLI — list / approve / reject PC remote pending via LAN relay.

Demo-safe: no OS automation; talks to lan_relay which proxies loopback bridge.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from kando_bridge.lan_relay import (
    DEFAULT_BEACON_PORT,
    RELAY_TOKEN_HEADER,
    listen_beacon_once,
)

DEFAULT_RELAY_URL = os.environ.get("LAN_RELAY_URL", "http://127.0.0.1:8766")


def _relay_base(url: str) -> str:
    return (url or DEFAULT_RELAY_URL).rstrip("/")


def _request_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    relay_token: str | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any]]:
    headers: dict[str, str] = {"Accept": "application/json"}
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    if relay_token:
        headers[RELAY_TOKEN_HEADER] = relay_token
    req = Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw.strip() else {}
            if not isinstance(payload, dict):
                return resp.status, {"raw": payload}
            return resp.status, payload
    except HTTPError as e:
        try:
            err_raw = e.read().decode("utf-8")
            payload = json.loads(err_raw) if err_raw.strip() else {"error": str(e)}
        except (OSError, json.JSONDecodeError):
            payload = {"error": str(e)}
        if not isinstance(payload, dict):
            payload = {"error": str(payload)}
        return e.code, payload
    except (URLError, OSError, json.JSONDecodeError) as e:
        return 0, {"ok": False, "error": "request_failed", "detail": str(e)}


def cmd_discover(args: argparse.Namespace) -> int:
    if args.beacon:
        beacon = listen_beacon_once(timeout=args.timeout, port=args.beacon_port)
        if beacon is None:
            print("No beacon received.", file=sys.stderr)
            return 1
        print(json.dumps(beacon, ensure_ascii=False, indent=2))
        return 0
    base = _relay_base(args.relay_url)
    status, payload = _request_json("GET", urljoin(base + "/", "relay/discover"), timeout=args.timeout)
    if status != 200 or not payload.get("ok", True):
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_pair(args: argparse.Namespace) -> int:
    base = _relay_base(args.relay_url)
    body: dict[str, Any] = {"pairing_code": args.pairing_code}
    if args.mobile_device_id:
        body["mobile_device_id"] = args.mobile_device_id
    status, payload = _request_json(
        "POST",
        urljoin(base + "/", "relay/pair"),
        body=body,
        timeout=args.timeout,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if status != 200 or not payload.get("relay_token"):
        return 1
    if args.save_token:
        print(f"\nexport LUMOS_RELAY_TOKEN={payload['relay_token']}", file=sys.stderr)
    return 0


def _relay_token_from_args(args: argparse.Namespace) -> str:
    return (args.relay_token or os.environ.get("LUMOS_RELAY_TOKEN") or "").strip()


def cmd_pending(args: argparse.Namespace) -> int:
    token = _relay_token_from_args(args)
    if not token:
        print("relay token required (--relay-token or LUMOS_RELAY_TOKEN)", file=sys.stderr)
        return 1
    base = _relay_base(args.relay_url)
    status, payload = _request_json(
        "GET",
        urljoin(base + "/", "relay/pending"),
        relay_token=token,
        timeout=args.timeout,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if status == 200 else 1


def cmd_approve(args: argparse.Namespace) -> int:
    return _approve_or_reject(args, approved=True)


def cmd_reject(args: argparse.Namespace) -> int:
    return _approve_or_reject(args, approved=False)


def _approve_or_reject(args: argparse.Namespace, *, approved: bool) -> int:
    token = _relay_token_from_args(args)
    if not token:
        print("relay token required (--relay-token or LUMOS_RELAY_TOKEN)", file=sys.stderr)
        return 1
    if not args.approval_token:
        print("--approval-token required", file=sys.stderr)
        return 1
    base = _relay_base(args.relay_url)
    path = "relay/approve" if approved else "relay/reject"
    body: dict[str, Any] = {"approval_token": args.approval_token}
    if args.approval_file:
        body["approval_file"] = args.approval_file
    if args.approval_id:
        body["approval_id"] = args.approval_id
    status, payload = _request_json(
        "POST",
        urljoin(base + "/", path),
        body=body,
        relay_token=token,
        timeout=args.timeout,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if 200 <= status < 300 and payload.get("accepted", payload.get("ok")) else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Lumos mobile approval client (LAN relay)")
    ap.add_argument("--relay-url", default=DEFAULT_RELAY_URL, help="LAN relay base URL")
    ap.add_argument("--relay-token", default="", help="Paired relay token (or LUMOS_RELAY_TOKEN)")
    ap.add_argument("--timeout", type=float, default=10.0)

    sub = ap.add_subparsers(dest="command", required=True)

    p_disc = sub.add_parser("discover", help="Find PC relay (HTTP discover or UDP beacon)")
    p_disc.add_argument("--beacon", action="store_true", help="Listen for UDP beacon")
    p_disc.add_argument("--beacon-port", type=int, default=DEFAULT_BEACON_PORT)
    p_disc.set_defaults(func=cmd_discover)

    p_pair = sub.add_parser("pair", help="Exchange pairing code for relay token")
    p_pair.add_argument("pairing_code", help="6-char pairing code from PC beacon/discover")
    p_pair.add_argument("--mobile-device-id", default="")
    p_pair.add_argument("--save-token", action="store_true", help="Print export LUMOS_RELAY_TOKEN=…")
    p_pair.set_defaults(func=cmd_pair)

    p_pending = sub.add_parser("pending", help="List pc_remote pending approvals")
    p_pending.set_defaults(func=cmd_pending)

    p_app = sub.add_parser("approve", help="Approve a pending request")
    p_app.add_argument("--approval-file", default="")
    p_app.add_argument("--approval-id", default="")
    p_app.add_argument("--approval-token", required=True)
    p_app.set_defaults(func=cmd_approve)

    p_rej = sub.add_parser("reject", help="Reject a pending request")
    p_rej.add_argument("--approval-file", default="")
    p_rej.add_argument("--approval-id", default="")
    p_rej.add_argument("--approval-token", required=True)
    p_rej.set_defaults(func=cmd_reject)

    return ap


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
