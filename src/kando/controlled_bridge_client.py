"""
Lumos → kontrollü köprü istemcisi.

Yalnızca POST /controlled yüzeyini kullanır; terminal/silme/uygulama/posta yok.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _base_url() -> str:
    raw = (os.environ.get("LUMOS_CONTROLLED_BRIDGE_URL") or "").strip()
    if raw:
        return raw.rstrip("/")
    host = (os.environ.get("KANDO_BRIDGE_HOST") or "127.0.0.1").strip()
    port = (os.environ.get("KANDO_BRIDGE_PORT") or "8765").strip()
    return f"http://{host}:{port}"


def _token() -> str:
    return (os.environ.get("KANDO_BRIDGE_SECRET") or "").strip()


def call_controlled(body: dict[str, Any], *, timeout: float = 60.0) -> dict[str, Any]:
    url = f"{_base_url()}/controlled"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    token = _token()
    if token:
        req.add_header("X-Kando-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "error": f"http_{e.code}", "detail": raw}
    except OSError as e:
        return {"ok": False, "error": "connection_failed", "detail": str(e)}
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid_response", "detail": raw}
    return out if isinstance(out, dict) else {"ok": False, "error": "invalid_response"}


def ping() -> dict[str, Any]:
    return call_controlled(
        {"permission": "file_rw", "command": "ping"},
    )


def read_file(path: str) -> dict[str, Any]:
    return call_controlled(
        {"permission": "file_rw", "command": "read", "path": path},
    )


def write_file(path: str, content: str) -> dict[str, Any]:
    return call_controlled(
        {
            "permission": "file_rw",
            "command": "write",
            "path": path,
            "content": content,
        },
    )
