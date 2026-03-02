"""
Web v1: minimal read-only HTTP server.
GET /health, GET /status. Core'a dokunmaz; sadece okuma.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Repo root = parent of web/
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    from lumos_core.version import VERSION
except Exception:
    VERSION = "0.1.0"


def _lumos_dir() -> Path:
    if (_REPO_ROOT / "src" / ".lumos").exists():
        return _REPO_ROOT / "src" / ".lumos"
    return _REPO_ROOT / ".lumos"


def _read_status_snapshot() -> dict:
    """Read-only snapshot: same shape as core state (offline, locked/presence)."""
    base = _lumos_dir()
    mode = (os.getenv("LUMOS_MODE") or "offline").strip().lower()
    mode = "offline" if mode == "offline" else "online"

    lock_status = "LOCKED"  # Web process does not run Lumos; safe default
    presence_enabled = False
    presence_running = False
    last_log_ts = ""

    try:
        import security.presence_lock as pl
        cfg = pl.load_presence_cfg(Path(base))
        presence_enabled = bool(getattr(cfg, "enabled", False))
        presence_running = bool(pl.is_running())
    except Exception:
        pass

    try:
        logp = base / "log.txt"
        if logp.exists():
            lines = logp.read_text(encoding="utf-8", errors="replace").strip().splitlines()
            if lines:
                first_part = lines[-1].strip().split(" | ")[0].strip()
                if first_part:
                    last_log_ts = first_part
    except Exception:
        pass

    return {
        "lock_status": lock_status,
        "presence_enabled": presence_enabled,
        "presence_running": presence_running,
        "mode": mode,
        "last_log_ts": last_log_ts,
    }


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj: dict, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path == "/health":
            self._json({"ok": True, "version": VERSION})
            return
        if path == "/status":
            self._json(_read_status_snapshot())
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass  # optional: keep quiet for smoke/curl


def main() -> None:
    port = int(os.getenv("PORT", "8765"))
    server = HTTPServer(("", port), Handler)
    print(f"Web v1 http://127.0.0.1:{port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.shutdown()


if __name__ == "__main__":
    main()
