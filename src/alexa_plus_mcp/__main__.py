"""Run: LUMOS_ALEXA_MCP_TOKEN=... python -m alexa_plus_mcp --port 8766"""

from __future__ import annotations

import argparse
import os
import sys

from alexa_plus_mcp.server import ServerConfig, serve

_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


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
            print("refusing non-localhost bind; set LUMOS_ALEXA_MCP_ALLOW_REMOTE_BIND=1 for a tunnel", file=sys.stderr)
            return 2

    extra = os.environ.get("LUMOS_ALEXA_MCP_ALLOWED_ORIGINS", "")
    allowed = frozenset(item.strip() for item in extra.split(",") if item.strip())
    httpd = serve(ServerConfig(token=token, allowed_origins=allowed, host=args.host, port=args.port))
    print(f"lumos-alexa-plus MCP 2025-11-25 streamable-http on http://{args.host}:{httpd.server_address[1]}/mcp", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
