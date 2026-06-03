#!/usr/bin/env python3
"""
Panel görev motoru: `.lumos/tasks.json` (LUMOS_BASE_DIR/tasks.json).

- Klasik: GET/PUT /tasks.json (tam doküman; panel local/demo modu)
- REST: GET /tasks (tasks.json), GET /tasks/trash (yalnız disk çöpü), POST /tasks, …
- Köprü: GET /lumos-read-state, POST /lumos-consent (panel chat «kilit aç» API fallback)
- Statik panel: GET / ve /index.html, /js/*, /css/* → repo/panel/ (kilit aç ile aynı origin)

Çalıştırma (repo kökünden):
  python3 panel/scripts/panel_tasks_server.py
  Tarayıcı: http://127.0.0.1:8766/index.html#chat  (görev API + köprü + «kilit aç» aynı portta)
"""
from __future__ import annotations

import copy
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.lumos_base_dir import lumos_base_dir  # noqa: E402

if os.environ.get("LUMOS_BASE_DIR") is None:
    os.environ["LUMOS_BASE_DIR"] = str(_REPO_ROOT / ".lumos")

_DEFAULT_PORT = 8766

_WS_RE = re.compile(r"[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000\ufeff]")


def _base_dir() -> Path:
    return lumos_base_dir()


def _tasks_file() -> Path:
    return _base_dir() / "tasks.json"


def _simulate_photo_capture() -> tuple[str, str]:
    base = _base_dir()
    out_dir = base / "mock_camera"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"photo_{stamp}.txt"
    target = out_dir / fname
    target.write_text("mock photo bytes\n", encoding="utf-8")
    rel = str(target.relative_to(base))
    return ("photo_saved", rel)


def _task_actions_gate() -> dict:
    # Bu paket için aksiyon gate devre dışı: buton aktifse işlem çalışır.
    return {"enabled": True, "reason": ""}


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


def _trash_dir() -> Path:
    return _base_dir() / "trash"


def _iter_trash_json_paths(d: Path) -> list[Path]:
    """trash/*.json + trash/tasks/*.json (task_*.json dahil). Klasörler/.tmp atlanır."""
    out: list[Path] = []

    def _scan(folder: Path) -> None:
        try:
            entries = list(folder.iterdir())
        except OSError:
            return
        for p in entries:
            # Klasörler (örn. trash/tasks) liste öğesi olmaz; içine ayrıca inilir.
            if p.is_dir() or not p.is_file():
                continue
            if p.name.endswith(".tmp") or p.suffix.lower() != ".json":
                continue
            out.append(p)

    _scan(d)
    tasks_sub = d / "tasks"
    if tasks_sub.is_dir():
        _scan(tasks_sub)
    return out


def _list_trash_disk_records() -> list[dict[str, Any]]:
    """trash/*.json ve trash/tasks/*.json dosyaları (Silinenler tek kaynak)."""
    d = _trash_dir()
    d.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    try:
        paths = sorted(_iter_trash_json_paths(d), key=lambda x: x.stat().st_mtime, reverse=True)
    except OSError:
        paths = _iter_trash_json_paths(d)
    for p in paths:
        if not p.is_file() or p.name.endswith(".tmp") or p.suffix.lower() != ".json":
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        out.append({"path": str(p.resolve()), "record": raw})
    return out


def _path_must_be_under_workspace(requested: Path) -> Optional[Path]:
    """Yalnızca lumos çalışma kökü (.lumos) altındaki çözümlenmiş yol; değilse None."""
    try:
        target = requested.expanduser().resolve()
    except (OSError, ValueError):
        return None
    try:
        base = _base_dir().resolve()
    except (OSError, ValueError):
        return None
    try:
        target.relative_to(base)
    except ValueError:
        return None
    return target


def _open_folder_in_os_shell(path: Path) -> tuple[bool, str]:
    if not path.is_dir():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False, "not_a_directory"
    if not path.is_dir():
        return False, "not_a_directory"
    p = str(path)
    try:
        if sys.platform == "win32":
            os.startfile(p)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        return False, str(e)
    return True, ""


def _write_trash_task_file(tid: str, task: dict, deleted_at: str) -> None:
    """Bir silinen görev için trash/ altında yeni dosya (read tarafı iterdir ile uyumlu). Overwrite yok."""
    d = _trash_dir()
    d.mkdir(parents=True, exist_ok=True)
    fn = tid.replace("/", "_").replace("\\", "_").strip() or "task"
    path = d / f"{fn}.json"
    n = 0
    while path.exists():
        n += 1
        path = d / f"{fn}_{n}.json"
    title = str(task.get("title", ""))
    record = {
        "id": tid,
        "taskId": tid,
        "type": "task_deleted",
        "text": title,
        "ts": deleted_at,
        "title": title,
        "status": str(task.get("status", "")),
        "deleted_at": deleted_at,
        "payload": task,
    }
    tmp = path.parent / (path.name + ".tmp")
    body = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(path)
    print("TRASH WRITE:", str(path.resolve()), flush=True)


def _find_trash_json_for_task_id(tid: str) -> Optional[Path]:
    """trash/*.json içinde kayıt id veya payload.id eşleşmesi (en yeni mtime önce)."""
    want = _normalize_ws(tid)
    if not want:
        return None
    d = _trash_dir()
    if not d.is_dir():
        return None
    candidates: list[Path] = _iter_trash_json_paths(d)
    if not candidates:
        return None

    def _mtime(pp: Path) -> float:
        try:
            return pp.stat().st_mtime
        except OSError:
            return 0.0

    candidates.sort(key=_mtime, reverse=True)
    for p in candidates:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        pl = raw.get("payload")
        rid = ""
        if isinstance(pl, dict):
            rid = str(pl.get("id") or pl.get("taskId") or "").strip()
        if not rid:
            rid = str(raw.get("id") or raw.get("taskId") or "").strip()
        if rid == want:
            return p
    return None


def _task_from_trash_record(record: dict) -> Optional[dict]:
    """Trash kaydından tasks.json satırı; pending_delete/deleted durumlarını aktif/done'a normalize eder."""
    pl = record.get("payload")
    if isinstance(pl, dict) and str(pl.get("id", "") or pl.get("taskId", "")).strip():
        task = copy.deepcopy(pl)
        if not str(task.get("id", "")).strip() and str(task.get("taskId", "")).strip():
            task["id"] = str(task.get("taskId")).strip()
    else:
        tid = str(record.get("id", "") or record.get("taskId", "")).strip()
        if not tid:
            return None
        task = {
            "id": tid,
            "title": str(record.get("title", "") or record.get("text", "")),
            "status": str(record.get("status", "")) or "active",
            "createdAt": record.get("createdAt"),
            "completedAt": record.get("completedAt"),
        }
    for k in ("expireAt", "restoreStatus", "deletedAt"):
        task.pop(k, None)
    st = str(task.get("status", "active"))
    if st in ("pending_delete", "deleted"):
        task["status"] = "active"
        task["completedAt"] = None
    if task.get("status") not in ("active", "done"):
        task["status"] = "active"
    if task.get("status") == "active":
        task["completedAt"] = None
    return task


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


def _panel_static_root() -> Path:
    return (_REPO_ROOT / "panel").resolve()


def _panel_static_mime(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".html":
        return "text/html; charset=utf-8"
    if ext == ".js":
        return "text/javascript; charset=utf-8"
    if ext == ".css":
        return "text/css; charset=utf-8"
    return "application/octet-stream"


class Handler(BaseHTTPRequestHandler):
    _last_good_lumos_state: dict[str, Any] | None = None

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _parse_path(self) -> str:
        return (self.path.split("?")[0].rstrip("/") or "/")

    def _options_path_allowed(self, p: str) -> bool:
        if p in (
            "/tasks.json",
            "/tasks",
            "/tasks/trash",
            "/tasks/complete",
            "/tasks/delete",
            "/tasks/restore",
            "/tasks/delete-permanent",
            "/lumos-read-state",
            "/lumos-consent",
            "/open-folder",
        ):
            return True
        if p in ("/", "/index.html") or p.startswith("/js/") or p.startswith("/css/"):
            return True
        return False

    def do_OPTIONS(self) -> None:
        p = self._parse_path()
        if not self._options_path_allowed(p):
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

    def _get_lumos_read_state(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent
        src = repo_root / "src"
        panel_api_capability_ok = src.is_dir()
        if panel_api_capability_ok and str(src) not in sys.path:
            sys.path.insert(0, str(src))
        if not panel_api_capability_ok:
            fallback = Handler._last_good_lumos_state or {
                "lumos_status": {},
                "panel_meta": {"server_time_utc": _now_iso(), "live_state_fresh": False},
            }
            ls = fallback.get("lumos_status")
            if not isinstance(ls, dict):
                ls = {}
                fallback["lumos_status"] = ls
            ls["panel_api_capability_ok"] = False
            ls["panel_api_health_ok"] = False
            _send_json(self, 200, fallback)
            return
        try:
            from core.context_store import set_panel_api_health
            from core.panel_runtime import get_live_read_state

            state = get_live_read_state(repo_root=repo_root)
            ls = state.get("lumos_status")
            if isinstance(ls, dict):
                ls["panel_api_capability_ok"] = True
                ls["panel_api_health_ok"] = True
            Handler._last_good_lumos_state = state
            set_panel_api_health(ok=True)
            _send_json(self, 200, state)
        except Exception as e:
            try:
                from core.context_store import set_panel_api_health

                set_panel_api_health(ok=False, error=str(e))
            except Exception:
                pass
            fallback = Handler._last_good_lumos_state or {
                "lumos_status": {},
                "panel_meta": {"server_time_utc": _now_iso(), "live_state_fresh": False},
            }
            ls = fallback.get("lumos_status")
            if not isinstance(ls, dict):
                ls = {}
                fallback["lumos_status"] = ls
            ls["panel_api_capability_ok"] = True
            ls["panel_api_health_ok"] = False
            _send_json(self, 200, fallback)

    def _get_tasks_trash(self) -> None:
        items = _list_trash_disk_records()
        td = _trash_dir()
        _send_json(self, 200, {"ok": True, "trash_location": str(td.resolve()), "items": items})

    def _try_serve_panel_static(self, p: str) -> bool:
        root = _panel_static_root()
        if p == "/":
            rel = "index.html"
        elif p == "/index.html":
            rel = "index.html"
        elif p.startswith("/js/") or p.startswith("/css/"):
            rel = p.lstrip("/").replace("\\", "/")
        else:
            return False
        if not rel or ".." in rel:
            return False
        try:
            target = (root / rel).resolve()
            root_s = str(root)
            if not str(target).startswith(root_s):
                return False
        except OSError:
            return False
        if not target.is_file():
            return False
        try:
            data = target.read_bytes()
        except OSError:
            return False
        self.send_response(200)
        self.send_header("Content-Type", _panel_static_mime(target))
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)
        return True

    def do_GET(self) -> None:
        p = self._parse_path()
        if p == "/lumos-read-state":
            self._get_lumos_read_state()
            return
        if p == "/open-folder":
            self.send_error(405)
            return
        if p == "/tasks/trash":
            self._get_tasks_trash()
            return
        if p not in ("/tasks.json", "/tasks"):
            if self._try_serve_panel_static(p):
                return
            self.send_error(404)
            return
        doc = _read_doc()
        tasks = doc.get("tasks")
        if isinstance(tasks, list):
            for t in tasks:
                if not isinstance(t, dict):
                    continue
                t["actions"] = {
                    "complete": True,
                    "delete": True,
                }
        gate = _task_actions_gate()
        doc["action_gate"] = {
            "complete": {"enabled": gate["enabled"], "reason": gate["reason"]},
            "delete": {"enabled": gate["enabled"], "reason": gate["reason"]},
            "undo_pending": {"enabled": gate["enabled"], "reason": gate["reason"]},
        }
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
        # Tek yönlendirme: sorgu / sondaki slash normalize (_parse_path); self.path ham eşleşmesine güvenme.
        p = self._parse_path()
        if p == "/open-folder":
            self._post_open_folder()
            return
        if p == "/lumos-consent":
            self._post_lumos_consent()
            return
        if p == "/tasks/restore":
            self._post_restore()
            return
        if p == "/tasks/delete-permanent":
            self._post_delete_permanent()
            return
        if p == "/tasks/delete":
            self._post_delete()
            return
        if p == "/tasks/complete":
            self._post_complete()
            return
        if p == "/tasks":
            self._post_create()
            return
        _send_json(self, 404, {"ok": False, "error": "not_found"})

    def _post_lumos_consent(self) -> None:
        """Panel chat kilit aç API: JSON body passphrase (zorunlu); consent.json (şifre diske yazılmaz)."""
        body = self._read_json_body()
        if not isinstance(body, dict):
            body = {}
        raw = body.get("passphrase")
        if raw is None or not str(raw).strip():
            _send_json(self, 400, {"ok": False, "error": "passphrase_required"})
            return
        base = _base_dir()
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            _send_json(self, 500, {"ok": False, "error": str(e)})
            return
        p = base / "consent.json"
        doc = {
            "granted": True,
            "source": "panel_tasks_server",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        try:
            p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as e:
            _send_json(self, 500, {"ok": False, "error": str(e)})
            return
        _send_json(self, 200, {"ok": True, "path": str(p.resolve())})

    def _post_open_folder(self) -> None:
        body = self._read_json_body()
        if not isinstance(body, dict):
            _send_json(self, 400, {"ok": False, "error": "invalid_json"})
            return
        raw = str(body.get("path", "")).strip()
        if not raw:
            _send_json(self, 400, {"ok": False, "error": "empty_path"})
            return
        try:
            cand = Path(raw)
        except Exception:
            _send_json(self, 400, {"ok": False, "error": "bad_path"})
            return
        allowed = _path_must_be_under_workspace(cand)
        if allowed is None:
            _send_json(self, 403, {"ok": False, "error": "path_not_allowed"})
            return
        ok, err = _open_folder_in_os_shell(allowed)
        if not ok:
            _send_json(self, 500, {"ok": False, "error": err or "open_failed"})
            return
        _send_json(self, 200, {"ok": True, "opened": str(allowed)})

    def _post_create(self) -> None:
        gate = _task_actions_gate()
        if not gate["enabled"]:
            _send_json(self, 409, {"ok": False, "error": "action_disabled", "reason": gate["reason"]})
            return
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
        gate = _task_actions_gate()
        if not gate["enabled"]:
            _send_json(self, 409, {"ok": False, "error": "action_disabled", "reason": gate["reason"]})
            return
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
        if _compare_key(title) == _compare_key("fotoğraf çek"):
            result, rel_path = _simulate_photo_capture()
            t["result"] = result
            t["summary"] = f"Fotoğraf kaydedildi: {rel_path}"
        tid = str(t.get("id", ""))
        ev = {
            "id": _new_event_id(),
            "type": "task_completed",
            "taskId": tid,
            "text": (t.get("summary") or title),
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
        id_key = _normalize_ws(body.get("id", ""))
        ref_key = _normalize_ws(body.get("ref", ""))
        if not id_key and not ref_key:
            _send_json(self, 400, {"ok": False, "error": "empty_id"})
            return
        doc = _read_doc()
        tasks = doc.get("tasks") if isinstance(doc.get("tasks"), list) else []
        hit = None
        idx = -1
        if id_key:
            for i, t in enumerate(tasks):
                if isinstance(t, dict) and str(t.get("id", "")) == id_key:
                    hit = t
                    idx = i
                    break
        if hit is None and ref_key:
            hit = _find_task_by_ref(doc, ref_key)
            if hit is not None:
                for i, t in enumerate(tasks):
                    if t is hit:
                        idx = i
                        break
        if hit is None or idx < 0:
            _send_json(self, 404, {"ok": False, "error": "not_found"})
            return
        tid = str(hit.get("id", "")).strip()
        if not tid:
            _send_json(self, 404, {"ok": False, "error": "not_found"})
            return
        title = str(hit.get("title", ""))
        now = _now_iso()
        payload = copy.deepcopy(hit)
        try:
            _write_trash_task_file(tid, payload, now)
        except OSError as e:
            _send_json(self, 500, {"ok": False, "error": str(e)})
            return
        del tasks[idx]
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
        _send_json(self, 200, {"ok": True})

    def _post_restore(self) -> None:
        body = self._read_json_body()
        if not isinstance(body, dict):
            _send_json(self, 400, {"ok": False, "error": "invalid_json"})
            return
        tid = _normalize_ws(body.get("id", ""))
        if not tid:
            _send_json(self, 400, {"ok": False, "error": "empty_id"})
            return
        tpath = _find_trash_json_for_task_id(tid)
        if tpath is None or not tpath.is_file():
            _send_json(self, 404, {"ok": False, "error": "missing_trash_file"})
            return
        try:
            record = json.loads(tpath.read_text(encoding="utf-8"))
        except Exception:
            _send_json(self, 400, {"ok": False, "error": "invalid_trash_file"})
            return
        if not isinstance(record, dict):
            _send_json(self, 400, {"ok": False, "error": "invalid_trash_file"})
            return
        task = _task_from_trash_record(record)
        if not task or not str(task.get("id", "")).strip():
            _send_json(self, 400, {"ok": False, "error": "invalid_payload"})
            return
        doc = _read_doc()
        tasks = doc.setdefault("tasks", [])
        if not isinstance(tasks, list):
            tasks = []
            doc["tasks"] = tasks
        rid = str(task.get("id", "")).strip()
        for existing in tasks:
            if isinstance(existing, dict) and str(existing.get("id", "")).strip() == rid:
                _send_json(self, 409, {"ok": False, "error": "task_already_exists"})
                return
        title = str(task.get("title", ""))
        now = _now_iso()
        tasks.append(task)
        ev = {
            "id": _new_event_id(),
            "type": "task_restored",
            "taskId": rid,
            "text": title,
            "ts": now,
        }
        doc.setdefault("events", []).append(ev)
        try:
            _write_doc(doc)
        except OSError as e:
            _send_json(self, 500, {"ok": False, "error": str(e)})
            return
        try:
            tpath.unlink()
        except OSError as e:
            _send_json(self, 500, {"ok": False, "error": str(e)})
            return
        _send_json(self, 200, {"ok": True, "task": task})

    def _post_delete_permanent(self) -> None:
        body = self._read_json_body()
        if not isinstance(body, dict):
            _send_json(self, 400, {"ok": False, "error": "invalid_json"})
            return
        tid = _normalize_ws(body.get("id", ""))
        if not tid:
            _send_json(self, 400, {"ok": False, "error": "empty_id"})
            return
        tpath = _find_trash_json_for_task_id(tid)
        if tpath is None or not tpath.is_file():
            _send_json(self, 200, {"ok": True})
            return
        title = ""
        try:
            record = json.loads(tpath.read_text(encoding="utf-8"))
            if isinstance(record, dict):
                pl = record.get("payload")
                if isinstance(pl, dict):
                    title = str(pl.get("title") or record.get("title") or "")
                else:
                    title = str(record.get("title") or "")
        except Exception:
            pass
        try:
            tpath.unlink()
        except OSError as e:
            _send_json(self, 500, {"ok": False, "error": str(e)})
            return
        doc = _read_doc()
        now = _now_iso()
        ev = {
            "id": _new_event_id(),
            "type": "task_permanently_deleted",
            "taskId": tid,
            "text": title or tid,
            "ts": now,
        }
        doc.setdefault("events", []).append(ev)
        try:
            _write_doc(doc)
        except OSError as e:
            _send_json(self, 500, {"ok": False, "error": str(e)})
            return
        _send_json(self, 200, {"ok": True})


def main() -> None:
    port = int(os.environ.get("LUMOS_PANEL_TASKS_PORT", str(_DEFAULT_PORT)))
    host = os.environ.get("LUMOS_PANEL_TASKS_HOST", "127.0.0.1")
    httpd = HTTPServer((host, port), Handler)
    sys.stderr.write(
        "panel_tasks_server: http://%s:%s\n  Statik panel + API aynı port: http://%s:%s/index.html#chat | POST /lumos-consent | GET /lumos-read-state | tasks.json: %s\n"
        % (host, port, host, port, _tasks_file())
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
