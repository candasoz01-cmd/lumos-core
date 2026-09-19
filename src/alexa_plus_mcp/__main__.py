"""Run: LUMOS_ALEXA_MCP_TOKEN=... python -m alexa_plus_mcp --port 8766"""

from __future__ import annotations

import argparse
import os
import secrets
import sys

from alexa_plus_mcp.oauth import AuthServer
from alexa_plus_mcp.server import ServerConfig, serve

_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _public_url(host: str, port: int) -> str:
    configured = os.environ.get("LUMOS_ALEXA_MCP_PUBLIC_URL", "").strip().rstrip("/")
    if configured:
        return configured
    return f"http://{host}:{port}"


def _redirect_uris(public_url: str) -> frozenset[str]:
    extra = os.environ.get("LUMOS_ALEXA_OAUTH_REDIRECT_URIS", "")
    configured = frozenset(item.strip() for item in extra.split(",") if item.strip())
    if configured:
        return configured
    return frozenset({f"{public_url}/oauth/dev-callback"})


def build_auth_server(public_url: str) -> tuple[AuthServer, bool]:
    client_id = os.environ.get("LUMOS_ALEXA_OAUTH_CLIENT_ID", "").strip() or "lumos-local"
    pinned = os.environ.get("LUMOS_ALEXA_OAUTH_CLIENT_SECRET", "").strip()
    ephemeral = not bool(pinned)
    client_secret = pinned or secrets.token_urlsafe(24)
    auth = AuthServer(
        public_url=public_url,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uris=_redirect_uris(public_url),
    )
    return auth, ephemeral


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m alexa_plus_mcp")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)

    token = os.environ.get("LUMOS_ALEXA_MCP_TOKEN", "").strip()
    if not token:
        print("LUMOS_ALEXA_MCP_TOKEN is required", file=sys.stderr)
        return 2
    if args.host not in _LOCAL_HOSTS:
        allow_remote = os.environ.get("LUMOS_ALEXA_MCP_ALLOW_REMOTE_BIND") == "1"
        if not allow_remote:
            print(
                "refusing non-localhost bind; set LUMOS_ALEXA_MCP_ALLOW_REMOTE_BIND=1 for a tunnel",
                file=sys.stderr,
            )
            return 2

    extra = os.environ.get("LUMOS_ALEXA_MCP_ALLOWED_ORIGINS", "")
    allowed = frozenset(item.strip() for item in extra.split(",") if item.strip())
    public_url = _public_url(args.host, args.port)
    auth, ephemeral_secret = build_auth_server(public_url)
    httpd = serve(
        ServerConfig(
            token=token,
            allowed_origins=allowed,
            host=args.host,
            port=args.port,
            auth=auth,
        )
    )
    bound = httpd.server_address[1]
    print(
        f"lumos-alexa-plus MCP 2025-11-25 streamable-http on http://{args.host}:{bound}/mcp",
        flush=True,
    )
    print(f"oauth issuer {auth.issuer}", flush=True)
    print(f"oauth client_id {auth.client_id}", flush=True)
    if ephemeral_secret:
        print(
            "oauth client_secret <ephemeral; set LUMOS_ALEXA_OAUTH_CLIENT_SECRET to pin>",
            flush=True,
        )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
