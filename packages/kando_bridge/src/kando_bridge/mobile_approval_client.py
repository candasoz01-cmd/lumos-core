"""
Demo-safe mobile approval clients for kando_bridge.

PR-RB-05: loopback poll via GET /pending_approvals + POST /approve (KANDO_BRIDGE_SECRET).
PR-RB-06: LAN relay discover/pair/pending/approve (relay token; bridge secret stays on PC).

No push, no QR — OSS demo; real Lumos Mobile lives in private layer.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from kando_bridge.lan_relay import (
    DEFAULT_BEACON_PORT,
    RELAY_TOKEN_HEADER,
    listen_beacon_once,
)
from kando_bridge.pending_approvals import (
    PC_REMOTE_SOURCE,
    STATUS_PENDING,
    is_pc_remote_pending,
)

# --- PR-RB-05 loopback bridge client ---

DEFAULT_TIMEOUT = 30.0



def bridge_base_url() -> str:
    raw = (os.environ.get("KANDO_BRIDGE_URL") or "").strip()
    if raw:
        base = raw.rstrip("/")
        for suffix in ("/task", "/pending_approvals", "/approve"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
        return base
    host = (os.environ.get("KANDO_BRIDGE_HOST") or "127.0.0.1").strip()
    port = (os.environ.get("KANDO_BRIDGE_PORT") or "8765").strip()
    return f"http://{host}:{port}"


def bridge_token() -> str:
    return (os.environ.get("KANDO_BRIDGE_SECRET") or "").strip()


def require_bridge_token() -> str:
    token = bridge_token()
    if not token:
        msg = (
            "KANDO_BRIDGE_SECRET tanımlı değil.\n"
            "  export KANDO_BRIDGE_SECRET='your-local-dev-secret'\n"
        )
        raise RuntimeError(msg)
    return token


def http_json(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, Any]:
    """HTTP call to kando_bridge; returns (status_code, parsed JSON)."""
    base = bridge_base_url()
    url = f"{base}{path}"
    if query:
        qs = urllib.parse.urlencode({k: v for k, v in query.items() if v})
        if qs:
            url = f"{url}?{qs}"
    data: bytes | None = None
    headers: dict[str, str] = {}
    token = bridge_token()
    if token:
        headers["X-Kando-Token"] = token
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = int(getattr(resp, "status", 200))
    except urllib.error.HTTPError as e:
        status = int(e.code)
        raw = e.read().decode("utf-8", errors="replace")
    except OSError as e:
        return 0, {"ok": False, "error": "connection_failed", "detail": str(e)}
    try:
        parsed = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return status, {"ok": False, "error": "invalid_response", "detail": raw}
    return status, parsed


def filter_pc_remote_records(
    items: list[Any],
    *,
    status: str | None = STATUS_PENDING,
) -> list[dict[str, Any]]:
    """Client-side pc_remote filter (fallback when query param unavailable)."""
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "")
        schema = str(item.get("schema_version") or "")
        command = str(item.get("command") or "")
        is_pc = (
            source == PC_REMOTE_SOURCE
            or schema.startswith("lumos.pc_remote")
            or (command.startswith("pc_") and command)
        )
        if not is_pc and not is_pc_remote_pending(item):
            continue
        if status is not None and str(item.get("status") or "") != status:
            continue
        out.append(item)
    return out


def list_pending_pc_remote(*, status: str | None = STATUS_PENDING) -> list[dict[str, Any]]:
    """Poll GET /pending_approvals with pc_remote source filter."""
    query: dict[str, str] = {"source": PC_REMOTE_SOURCE}
    status_code, data = http_json("GET", "/pending_approvals", query=query)
    if status_code != 200:
        return []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("pending"), list):
        items = data["pending"]
    else:
        return []
    if status is None:
        return filter_pc_remote_records(items, status=None)
    return filter_pc_remote_records(items, status=status)


def find_record_by_ref(
    ref: str,
    *,
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Resolve approval_id or approval_file path to a pending list record."""
    needle = (ref or "").strip().replace("\\", "/")
    if not needle:
        return None
    pool = items if items is not None else list_pending_pc_remote(status=None)
    for item in pool:
        aid = str(item.get("approval_id") or "").strip()
        afile = str(item.get("approval_file") or "").strip().replace("\\", "/")
        if needle == aid or needle == afile:
            return item
        if needle.endswith(".json") and afile.endswith(needle):
            return item
        if aid and needle.endswith(aid):
            return item
    return None


def validate_token_for_record(record: dict[str, Any], token: str) -> bool:
    """Token validation skeleton — birebir eşleşme zorunlu."""
    expected = str(record.get("approval_token") or "").strip()
    supplied = (token or "").strip()
    if not expected or not supplied:
        return False
    return supplied == expected


def submit_approval(
    approval_file: str,
    token: str,
    *,
    approved: bool,
) -> dict[str, Any]:
    """POST /approve with approval_file + approval_token."""
    body = {
        "approval_file": approval_file,
        "approval_token": token,
        "approved": approved,
    }
    status_code, data = http_json("POST", "/approve", body=body)
    if not isinstance(data, dict):
        return {"accepted": False, "error": "invalid_response", "http_status": status_code}
    data.setdefault("http_status", status_code)
    return data


def approve_pending(ref: str, token: str) -> dict[str, Any]:
    """List → token doğrula → POST /approve approved=true."""
    record = find_record_by_ref(ref)
    if record is None:
        return {"accepted": False, "error": "approval_not_found", "ref": ref}
    if not validate_token_for_record(record, token):
        return {"accepted": False, "error": "invalid_approval_token", "ref": ref}
    approval_file = str(record.get("approval_file") or "").strip()
    if not approval_file:
        return {"accepted": False, "error": "approval_file_missing", "ref": ref}
    return submit_approval(approval_file, token, approved=True)


def reject_pending(ref: str, token: str) -> dict[str, Any]:
    """List → token doğrula → POST /approve approved=false."""
    record = find_record_by_ref(ref)
    if record is None:
        return {"accepted": False, "error": "approval_not_found", "ref": ref}
    if not validate_token_for_record(record, token):
        return {"accepted": False, "error": "invalid_approval_token", "ref": ref}
    approval_file = str(record.get("approval_file") or "").strip()
    if not approval_file:
        return {"accepted": False, "error": "approval_file_missing", "ref": ref}
    return submit_approval(approval_file, token, approved=False)


def _cmd_list_pending(args: argparse.Namespace) -> int:
    status = None if args.all_status else STATUS_PENDING
    items = list_pending_pc_remote(status=status)
    print(json.dumps(items, ensure_ascii=False, indent=2))
    return 0 if items is not None else 1


def _cmd_approve(args: argparse.Namespace) -> int:
    result = approve_pending(args.ref, args.token)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("accepted") else 1


def _cmd_reject(args: argparse.Namespace) -> int:
    result = reject_pending(args.ref, args.token)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("accepted") else 1


def build_bridge_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mobile-approval",
        description="Poll-based demo mobile approval client (kando_bridge loopback MVP)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-pending", help="Poll GET /pending_approvals (pc_remote)")
    p_list.add_argument(
        "--all-status",
        action="store_true",
        help="Include non-pending records (approved, rejected, expired)",
    )
    p_list.set_defaults(func=_cmd_list_pending)

    p_approve = sub.add_parser("approve", help="Approve a pending PC remote record")
    p_approve.add_argument("ref", help="approval_id or approval_file path")
    p_approve.add_argument("--token", required=True, help="approval_token from pending record")
    p_approve.set_defaults(func=_cmd_approve)

    p_reject = sub.add_parser("reject", help="Reject a pending PC remote record")
    p_reject.add_argument("ref", help="approval_id or approval_file path")
    p_reject.add_argument("--token", required=True, help="approval_token from pending record")
    p_reject.set_defaults(func=_cmd_reject)

    return parser




# --- PR-RB-06 LAN relay client ---

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


def build_relay_parser() -> argparse.ArgumentParser:
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




def _is_relay_cli(argv: list[str]) -> bool:
    if "--relay-url" in argv or "--beacon" in argv:
        return True
    relay_only = {"discover", "pair", "pending"}
    for i, arg in enumerate(argv):
        if arg in relay_only:
            return True
        if arg in ("approve", "reject"):
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                return False
            if any(
                flag in argv
                for flag in ("--approval-token", "--approval-file", "--approval-id")
            ):
                return True
    return False


def _run_bridge_cli(argv: list[str]) -> int:
    try:
        require_bridge_token()
    except RuntimeError as e:
        sys.stderr.write(f"Hata: {e}")
        return 2
    parser = build_bridge_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


def _run_relay_cli(argv: list[str]) -> int:
    parser = build_relay_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if _is_relay_cli(argv):
        return _run_relay_cli(argv)
    return _run_bridge_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
