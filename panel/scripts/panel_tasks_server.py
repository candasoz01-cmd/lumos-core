#!/usr/bin/env python3
"""
Panel görev motoru: `.lumos/tasks.json` (LUMOS_BASE_DIR/tasks.json).

- Klasik: GET/PUT /tasks.json (tam doküman; panel local/demo modu)
- REST: GET /tasks (aynı doküman), POST /tasks, POST /tasks/complete, POST /tasks/delete (api modu)

Çalıştırma (repo kökünden):
  python3 panel/scripts/panel_tasks_server.py

Panel local: GET/PUT …/tasks.json
Panel varsayılan: API yolu (GET /tasks + POST); local için panel’de MODE=local veya API_BASE=false.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional

_DEFAULT_PORT = 8766

_WS_RE = re.compile(r"[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000\ufeff]")


def _base_dir() -> Path:
    return Path(os.environ.get("LUMOS_BASE_DIR", ".lumos")).resolve()


def _tasks_file() -> Path:
    return _base_dir() / "tasks.json"


def _empty_doc() -> dict:
    return {"v": 1, "tasks": [], "events": []}


def _read_doc() -> dict:
    p = _tasks_file()
    if not p.is_file():
        return _empty_doc()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _empty_doc()
    if not isinstance(data, dict):
        return _empty_doc()
    out = _empty_doc()
    if isinstance(data.get("tasks"), list):
        out["tasks"] = data["tasks"]
    if isinstance(data.get("events"), list):
        out["events"] = data["events"]
    return out


def _write_doc(data: dict) -> None:
    p = _tasks_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(p)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_task_id() -> str:
    return "tsk_%s_%s" % (int(time.time() * 1000), random.randint(1000, 9999))


def _new_event_id() -> str:
    return "ev_%s_%s" % (int(time.time() * 1000), random.randint(1000, 9999))


def _normalize_ws(s: str) -> str:
    t = _WS_RE.sub(" ", str(s or ""))
    return " ".join(t.split()).strip()


def _compare_key(s: str) -> str:
    return _normalize_ws(s).lower()


def _title_matches_ref(ref: str, title: str) -> bool:
    r = _compare_key(ref)
    t = _compare_key(title)
    if not r or not t:
        return False
    if t == r:
        return True
    if t.replace("-", " ") == r.replace("-", " "):
        return True
    if re.sub(r"\s+", "-", t) == re.sub(r"\s+", "-", r):
        return True
    return False


def _find_task_by_ref(doc: dict, ref: str) -> Optional[dict]:
    rtrim = _normalize_ws(ref)
    if not rtrim:
        return None
    tasks: list = doc.get("tasks") or []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if t.get("status") == "deleted":
            continue
        if t.get("status") not in ("active", "done"):
            continue
        if str(t.get("id", "")) == rtrim:
            return t
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if t.get("status") == "deleted":
            continue
        if t.get("status") not in ("active", "done"):
            continue
        if _title_matches_ref(rtrim, str(t.get("title", ""))):
            return t
    return None


def _send_json(handler: BaseHTTPRequestHandler, code: int, obj: dict) -> None:
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler._cors()
    handler.end_headers()
    handler.wfile.write(raw)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _parse_path(self) -> str:
        return (self.path.split("?")[0].rstrip("/") or "/")

    def do_OPTIONS(self) -> None:
        p = self._parse_path()
        if p not in ("/tasks.json", "/tasks", "/tasks/complete", "/tasks/delete"):
            self.send_error(404)
            return
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _read_json_body(self) -> Any:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return None

    def do_GET(self) -> None:
        p = self._parse_path()
        if p not in ("/tasks.json", "/tasks"):
            self.send_error(404)
            return
        doc = _read_doc()
        raw = json.dumps(doc, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self._cors()
        self.end_headers()
        self.wfile.write(raw)

    def do_PUT(self) -> None:
        if self._parse_path() != "/tasks.json":
            self.send_error(404)
            return
        data = self._read_json_body()
        if not isinstance(data, dict):
            self.send_error(400, "Invalid JSON")
            return
        doc = _empty_doc()
        doc["v"] = 1
        if isinstance(data.get("tasks"), list):
            doc["tasks"] = data["tasks"]
        if isinstance(data.get("events"), list):
            doc["events"] = data["events"]
        try:
            _write_doc(doc)
        except OSError as e:
            self.send_error(500, str(e))
            return
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self) -> None:
        p = self._parse_path()
        if p == "/tasks":
            self._post_create()
        elif p == "/tasks/complete":
            self._post_complete()
        elif p == "/tasks/delete":
            self._post_delete()
        else:
            self.send_error(404)

    def _post_create(self) -> None:
        body = self._read_json_body()
        if not isinstance(body, dict):
            _send_json(self, 400, {"ok": False, "error": "invalid_json"})
            return
        title = _normalize_ws(body.get("title", ""))
        if not title:
            _send_json(self, 400, {"ok": False, "error": "empty_title"})
            return
        doc = _read_doc()
        now = _now_iso()
        tid = _new_task_id()
        task = {
            "id": tid,
            "title": title,
            "status": "active",
            "createdAt": now,
            "completedAt": None,
        }
        ev = {
            "id": _new_event_id(),
            "type": "task_created",
            "taskId": tid,
            "text": title,
            "ts": now,
        }
        doc.setdefault("tasks", []).append(task)
        doc.setdefault("events", []).append(ev)
        try:
            _write_doc(doc)
        except OSError as e:
            _send_json(self, 500, {"ok": False, "error": str(e)})
            return
        _send_json(self, 200, {"ok": True, "task": task})

    def _post_complete(self) -> None:
        body = self._read_json_body()
        if not isinstance(body, dict):
            _send_json(self, 400, {"ok": False, "error": "invalid_json"})
            return
        ref = _normalize_ws(body.get("ref", ""))
        if not ref:
            _send_json(self, 400, {"ok": False, "error": "empty_ref"})
            return
        doc = _read_doc()
        t = _find_task_by_ref(doc, ref)
        if not t:
            _send_json(self, 404, {"ok": False, "error": "not_found"})
            return
        if t.get("status") == "done":
            _send_json(self, 409, {"ok": False, "error": "already_done"})
            return
        now = _now_iso()
        t["status"] = "done"
        t["completedAt"] = now
        title = str(t.get("title", ""))
        tid = str(t.get("id", ""))
        ev = {
            "id": _new_event_id(),
            "type": "task_completed",
            "taskId": tid,
            "text": title,
            "ts": now,
        }
        doc.setdefault("events", []).append(ev)
        try:
            _write_doc(doc)
        except OSError as e:
            _send_json(self, 500, {"ok": False, "error": str(e)})
            return
        _send_json(self, 200, {"ok": True, "task": t})

    def _post_delete(self) -> None:
        body = self._read_json_body()
        if not isinstance(body, dict):
            _send_json(self, 400, {"ok": False, "error": "invalid_json"})
            return
        ref = _normalize_ws(body.get("ref", ""))
        if not ref:
            _send_json(self, 400, {"ok": False, "error": "empty_ref"})
            return
        doc = _read_doc()
        t = _find_task_by_ref(doc, ref)
        if not t:
            _send_json(self, 404, {"ok": False, "error": "not_found"})
            return
        now = _now_iso()
        t["status"] = "deleted"
        t["deletedAt"] = now
        title = str(t.get("title", ""))
        tid = str(t.get("id", ""))
        ev = {
            "id": _new_event_id(),
            "type": "task_deleted",
            "taskId": tid,
            "text": title,
            "ts": now,
        }
        doc.setdefault("events", []).append(ev)
        try:
            _write_doc(doc)
        except OSError as e:
            _send_json(self, 500, {"ok": False, "error": str(e)})
            return
        _send_json(self, 200, {"ok": True, "task": t})


def main() -> None:
    port = int(os.environ.get("LUMOS_PANEL_TASKS_PORT", str(_DEFAULT_PORT)))
    host = os.environ.get("LUMOS_PANEL_TASKS_HOST", "127.0.0.1")
    httpd = HTTPServer((host, port), Handler)
    sys.stderr.write(
        "panel_tasks_server: %s\n  GET/PUT /tasks.json | GET /tasks | POST /tasks /tasks/complete /tasks/delete\n  → %s\n"
        % (f"http://{host}:{port}", _tasks_file())
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
