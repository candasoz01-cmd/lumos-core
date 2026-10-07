#!/usr/bin/env python3
"""HTTP relay: JSON { "goal": "..." } → kando bridge (text/plain gövde)."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

PORT = int(os.environ.get("RELAY_PORT", "8766"))
_bridge_url = urlsplit((os.environ.get("BRIDGE_URL") or "http://localhost:8765/task").strip())
# Older local configs specified only the origin; POST / is not a task route.
BRIDGE_URL = urlunsplit(_bridge_url._replace(path="/task" if _bridge_url.path in ("", "/") else _bridge_url.path))


def _preview(s: str, max_len: int = 96) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


class _RelayHTTPServer(HTTPServer):
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    def _forward_response(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[relay] {self.address_string()} — {format % args}", flush=True)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"expected JSON body with \"goal\" string")
            print("[relay] 400 geçersiz JSON", flush=True)
            return

        if not isinstance(data, dict):
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"JSON object required")
            print("[relay] 400 gövde nesne değil", flush=True)
            return

        goal = data.get("goal", "")
        if not isinstance(goal, str):
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"\"goal\" must be a string")
            print("[relay] 400 goal tipi", flush=True)
            return

        goal = goal.strip()
        if not goal:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"empty goal")
            print("[relay] 400 boş goal", flush=True)
            return

        payload = f"görev: {goal}".encode("utf-8")
        req = Request(
            BRIDGE_URL,
            data=payload,
            method="POST",
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        try:
            with urlopen(req, timeout=120) as resp:
                status = resp.status
                body = resp.read()
                content_type = resp.headers.get("Content-Type", "application/json")
        except HTTPError as e:
            self._forward_response(e.code, e.read(), e.headers.get("Content-Type", "application/json"))
            return
        except (URLError, OSError, HTTPException) as e:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            msg = f"bridge response unavailable; delivery uncertain, not retried: {e}"
            self.wfile.write(msg.encode("utf-8", errors="replace"))
            print(f"[relay] 502 → {BRIDGE_URL} ({e})", flush=True)
            return

        # Preserve accepted/pending/failure/job_id; HTTP 200 is not completion.
        self._forward_response(status, body, content_type)
        print(f"[relay] bridge HTTP {status} goal={_preview(goal)} → {BRIDGE_URL}", flush=True)


def run() -> None:
    server = _RelayHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"relay {PORT} → bridge {BRIDGE_URL}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run()
