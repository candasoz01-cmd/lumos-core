#!/usr/bin/env python3
"""OpenAI tool-loop demo: Responses API tool call → bridge approval → stub execute."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PKG = _REPO / "packages" / "kando_bridge" / "src"
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from kando_bridge.mobile_approval_client import require_bridge_token  # noqa: E402
from kando_bridge.openai_tool_adapter import (  # noqa: E402
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
        help="Optional LAN relay base URL (demo only; loop still uses bridge execute)",
    )
    parser.add_argument(
        "--relay-token",
        default=os.environ.get("LUMOS_RELAY_TOKEN", ""),
        help="Optional paired relay token",
    )
    parser.add_argument(
        "--no-auto-approve",
        action="store_true",
        help="Stop at pending_approval (do not auto-approve)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        help="OpenAI model for --live",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _apply_bridge_env(args)

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

    results = run_openai_response_loop(
        payload,
        auto_approve=not args.no_auto_approve,
    )
    summary = {
        "mode": "live" if use_live else "mock",
        "tool_calls": [{"name": c.name, "arguments": c.arguments} for c in calls],
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    ok = all(r.get("ok") for r in results)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
