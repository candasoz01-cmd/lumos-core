"""
Demo-safe poll-based mobile approval client for kando_bridge.

Polls GET /pending_approvals (pc_remote filter), submits POST /approve.
No push, no QR — loopback MVP for OSS demo; real Lumos Mobile lives in private layer.
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

from kando_bridge.pending_approvals import (
    PC_REMOTE_SOURCE,
    STATUS_PENDING,
    is_pc_remote_pending,
)

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


def build_parser() -> argparse.ArgumentParser:
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


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        require_bridge_token()
    except RuntimeError as e:
        sys.stderr.write(f"Hata: {e}")
        raise SystemExit(2) from e
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
