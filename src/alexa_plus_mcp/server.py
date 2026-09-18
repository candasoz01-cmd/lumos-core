"""Streamable HTTP transport for the Alexa+ MCP server (MCP 2025-11-25).

JSON responses on POST /mcp. GET /mcp returns 405 (no standalone SSE stream).
Local bind defaults to 127.0.0.1. Alexa+ account linking / deploy is out of
this slice — see docs/analysis/amazon-alexa-plus-mcp-2026.md.
"""

from __future__ import annotations

import json
import secrets
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from alexa_plus_mcp.protocol import PROTOCOL_VERSION, RpcOutcome, Session, handle_jsonrpc

MCP_PATH = "/mcp"
HEALTH_PATH = "/health"


@dataclass
class ServerConfig:
    token: str
    allowed_origins: frozenset[str] = field(default_factory=frozenset)
    host: str = "127.0.0.1"
    port: int = 8766


class SessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        sid = secrets.token_urlsafe(24)
        session = Session(session_id=sid)
        with self._lock:
            self._sessions[sid] = session
        return session

    def get(self, session_id: str | None) -> Session | None:
        if not session_id:
            return None
        with self._lock:
            return self._sessions.get(session_id)


def origin_allowed(origin: str | None, extra: frozenset[str]) -> bool:
    if origin is None or origin == "":
        return True
    if origin in extra:
        return True
    parsed = urlparse(origin)
    return parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _bearer_ok(header: str | None, token: str) -> bool:
    if not header or not token:
        return False
    prefix = "Bearer "
    if not header.startswith(prefix):
        return False
    given = header[len(prefix):].strip()
    if len(given) != len(token):
        return False
    return secrets.compare_digest(given, token)


def make_handler(config: ServerConfig, store: SessionStore):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send(self, status: int, body: bytes | None, headers: dict[str, str] | None = None) -> None:
            self.send_response(status)
            extra = dict(headers or {})
            content_type = extra.pop("Content-Type", "application/json")
            for key, value in extra.items():
                self.send_header(key, value)
            if body is not None:
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
            else:
                self.send_header("Content-Length", "0")
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _send_rpc(self, outcome: RpcOutcome) -> None:
            headers: dict[str, str] = dict(outcome.headers)
            if outcome.session_id:
                headers["MCP-Session-Id"] = outcome.session_id
            body = None
            if outcome.body is not None:
                body = json.dumps(outcome.body).encode("utf-8")
                headers.setdefault("Content-Type", "application/json")
            self._send(outcome.status, body, headers)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] == HEALTH_PATH:
                payload = json.dumps(
                    {"ok": True, "protocolVersion": PROTOCOL_VERSION, "transport": "streamable-http"}
                ).encode("utf-8")
                self._send(200, payload)
                return
            if self.path.split("?", 1)[0] == MCP_PATH:
                self._send(405, None, {"Allow": "POST"})
                return
            self._send(404, None)

        def do_DELETE(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] == MCP_PATH:
                self._send(405, None, {"Allow": "POST"})
                return
            self._send(404, None)

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path != MCP_PATH:
                self._send(404, None)
                return
            origin = self.headers.get("Origin")
            if not origin_allowed(origin, config.allowed_origins):
                self._send(403, json.dumps({"error": "origin_forbidden"}).encode("utf-8"))
                return
            if not _bearer_ok(self.headers.get("Authorization"), config.token):
                self._send(401, json.dumps({"error": "unauthorized"}).encode("utf-8"))
                return
            accept = (self.headers.get("Accept") or "").lower()
            if "application/json" not in accept and "text/event-stream" not in accept:
                self._send(406, json.dumps({"error": "accept_required"}).encode("utf-8"))
                return
            length = int(self.headers.get("Content-Length") or "0")
            if length < 0 or length > 1_000_000:
                self._send(413, None)
                return
            raw = self.rfile.read(length) if length else b""
            try:
                message = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_rpc(
                    RpcOutcome(
                        status=400,
                        body={"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}},
                    )
                )
                return
            if not isinstance(message, dict):
                self._send(400, json.dumps({"error": "object_required"}).encode("utf-8"))
                return

            method = message.get("method")
            session_header = self.headers.get("MCP-Session-Id")
            proto = self.headers.get("MCP-Protocol-Version")
            if method != "initialize":
                assumed = proto or "2025-03-26"
                if assumed != PROTOCOL_VERSION:
                    self._send(400, json.dumps({"error": "unsupported_protocol_version"}).encode("utf-8"))
                    return
                session = store.get(session_header)
            else:
                session = store.create()

            outcome = handle_jsonrpc(
                message,
                None if method == "initialize" else session,
                new_session_id=session.session_id if method == "initialize" else None,
            )
            if "application/json" in accept:
                self._send_rpc(outcome)
                return
            # Client asked only for SSE: wrap one JSON-RPC payload as a single event.
            if outcome.body is None:
                self._send(outcome.status, None, outcome.headers)
                return
            event = f"data: {json.dumps(outcome.body)}\n\n".encode("utf-8")
            headers = {"Content-Type": "text/event-stream"}
            if outcome.session_id:
                headers["MCP-Session-Id"] = outcome.session_id
            self._send(outcome.status, event, headers)

    return Handler


def serve(config: ServerConfig) -> ThreadingHTTPServer:
    if not config.token:
        raise ValueError("LUMOS_ALEXA_MCP_TOKEN is required")
    handler = make_handler(config, SessionStore())
    httpd = ThreadingHTTPServer((config.host, config.port), handler)
    httpd.allow_reuse_address = True
    return httpd
