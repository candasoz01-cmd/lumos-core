#!/usr/bin/env python3
"""OpenAI tool-loop demo: Responses API tool call → bridge approval → stub execute."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PKG = _REPO / "packages" / "kando_bridge" / "src"
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from kando_bridge.lan_relay import DEFAULT_RELAY_PORT, mobile_ui_path  # noqa: E402
from kando_bridge.mobile_approval_client import (  # noqa: E402
    approve_pending,
    require_bridge_token,
)
from kando_bridge.openai_tool_adapter import (  # noqa: E402
    approve_and_reexecute,
    dev_auto_approve_allowed,
    fetch_live_openai_response,
    mock_openai_response_payload,
    parse_openai_tool_calls,
    run_openai_response_loop,
)


def _apply_bridge_env(args: argparse.Namespace) -> None:
    if args.bridge_url:
        os.environ["KANDO_BRIDGE_URL"] = args.bridge_url
    if args.bridge_secret:
        os.environ["KANDO_BRIDGE_SECRET"] = args.bridge_secret
    if args.relay_url:
        os.environ["LAN_RELAY_URL"] = args.relay_url
    if args.relay_token:
        os.environ["LUMOS_RELAY_TOKEN"] = args.relay_token


def _mobile_ui_hint(args: argparse.Namespace) -> str:
    relay_base = (args.relay_url or os.environ.get("LAN_RELAY_URL") or "").strip()
    if relay_base:
        return f"{relay_base.rstrip('/')}{mobile_ui_path()}"
    host = os.environ.get("LAN_RELAY_HOST", "127.0.0.1")
    port = os.environ.get("LAN_RELAY_PORT", str(DEFAULT_RELAY_PORT))
    return f"http://{host}:{port}{mobile_ui_path()}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OpenAI Responses API → kando_bridge tool loop (mock default, live optional)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use canned pc_open_url function_call JSON (default when --live omitted)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call OpenAI Responses API (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--prompt",
        default="Please open https://example.com in my browser.",
        help="User message for --live mode",
    )
    parser.add_argument(
        "--url",
        default="https://example.com",
        help="URL embedded in --mock canned response",
    )
    parser.add_argument(
        "--bridge-url",
        default=os.environ.get("KANDO_BRIDGE_URL", ""),
        help="Bridge base URL (or KANDO_BRIDGE_URL)",
    )
    parser.add_argument(
        "--bridge-secret",
        default=os.environ.get("KANDO_BRIDGE_SECRET", ""),
        help="Bridge token (or KANDO_BRIDGE_SECRET)",
    )
    parser.add_argument(
        "--relay-url",
        default=os.environ.get("LAN_RELAY_URL", ""),
        help="LAN relay base URL for mobile UI hint",
    )
    parser.add_argument(
        "--relay-token",
        default=os.environ.get("LUMOS_RELAY_TOKEN", ""),
        help="Optional paired relay token",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="DEV ONLY: skip mobile UI and auto-approve pending (not for production demos)",
    )
    parser.add_argument(
        "--wait-approve",
        action="store_true",
        help="Poll until pending is approved via mobile UI or CLI, then re-execute",
    )
    parser.add_argument(
        "--wait-timeout",
        type=float,
        default=120.0,
        help="Seconds to wait for approval when --wait-approve (default 120)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        help="OpenAI model for --live",
    )
    return parser


def _wait_for_manual_approve(
    calls: list,
    pending_results: list[dict],
    *,
    timeout: float,
) -> list[dict]:
    """Poll disk until user approves via mobile UI / CLI, then re-execute."""
    deadline = time.time() + max(1.0, timeout)
    final: list[dict] = []
    for call, pending_result in zip(calls, pending_results, strict=True):
        pending = pending_result.get("pending") or {}
        approval_id = str(pending.get("approval_id") or "")
        approval_token = str(pending.get("approval_token") or "")
        if not approval_id or not approval_token:
            final.append(pending_result)
            continue
        while time.time() < deadline:
            approve_out = approve_pending(approval_id, approval_token)
            if approve_out.get("accepted"):
                exec_status, loop_out = approve_and_reexecute(call, pending)
                loop_out["http_status"] = exec_status
                loop_out["tool_call"] = {
                    "name": call.name,
                    "arguments": call.arguments,
                    "call_id": call.call_id,
                }
                final.append(loop_out)
                break
            time.sleep(1.0)
        else:
            final.append(
                {
                    **pending_result,
                    "error": "approval_timeout",
                    "message": "Timed out waiting for mobile approval",
                }
            )
    return final


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _apply_bridge_env(args)

    if args.auto_approve:
        if not dev_auto_approve_allowed():
            sys.stderr.write(
                "HATA / ERROR: --auto-approve requires LUMOS_DEV_AUTO_APPROVE=1 "
                "(dev-only; not for production demos).\n"
            )
            return 2
        sys.stderr.write(
            "UYARI / WARNING: --auto-approve dev-only bypass; "
            "use mobile UI for real demos.\n"
        )

    try:
        require_bridge_token()
    except RuntimeError as e:
        sys.stderr.write(f"Hata: {e}")
        return 2

    use_live = args.live and not args.mock
    if use_live:
        try:
            response = fetch_live_openai_response(args.prompt, model=args.model)
        except RuntimeError as e:
            sys.stderr.write(f"Hata: {e}\n")
            return 2
        except Exception as e:
            sys.stderr.write(f"OpenAI hatası: {e}\n")
            return 1
        payload = response
    else:
        payload = mock_openai_response_payload(url=args.url)

    calls = parse_openai_tool_calls(payload)
    if not calls:
        print(json.dumps({"ok": False, "error": "no_tool_calls", "payload": payload}, indent=2))
        return 1

    auto_approve = bool(args.auto_approve)
    results = run_openai_response_loop(payload, auto_approve=auto_approve)

    pending_stages = [r for r in results if r.get("stage") == "pending"]
    if pending_stages and not auto_approve:
        mobile_url = _mobile_ui_hint(args)
        sys.stderr.write(
            f"\nOnay gerekli / Approval required — open mobile UI:\n  {mobile_url}\n"
            f"Pair first: POST /relay/pair → open /relay/mobile?token=…\n"
        )
        if args.wait_approve:
            sys.stderr.write("Waiting for approval (--wait-approve)…\n")
            results = _wait_for_manual_approve(calls, results, timeout=args.wait_timeout)

    summary = {
        "mode": "live" if use_live else "mock",
        "auto_approve": auto_approve,
        "mobile_ui": _mobile_ui_hint(args),
        "tool_calls": [{"name": c.name, "arguments": c.arguments} for c in calls],
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    ok = all(r.get("ok") for r in results)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
