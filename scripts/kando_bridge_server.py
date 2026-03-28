#!/usr/bin/env python3
"""
Lokal HTTP köprüsü: dış istemci (ChatGPT eklentisi, curl, relay vb.) metni alır,
`.lumos/inbox/request.txt` dosyasına yazar; `kando_watch` aynı dosyayı izleyerek Kando zincirini çalıştırır.

Kütüphane yolu: köprü `PYTHONPATH=src` (veya eşdeğer) ile çalıştırılmalı; ağda varsayılan yalnızca 127.0.0.1.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from kando.agent_runner import get_job_status, start_agent_job
from kando.patch_scope import extract_file_task

ROOT = Path(__file__).resolve().parents[1]

REQUEST_FILE = ROOT / ".lumos" / "inbox" / "request.txt"
DIRECT_PATCH_META_FILE = REQUEST_FILE.parent / "direct_patch_meta.json"
OUTBOX_DIR = ROOT / ".lumos" / "outbox"
AGENT_LAST_FILE = OUTBOX_DIR / "agent_last.json"
LAST_RESULT_FILE = OUTBOX_DIR / "last_result.json"
LAST_EXECUTION_FILE = OUTBOX_DIR / "last_execution.json"
_ALLOWED_BIND_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _stderr_write(line: str) -> None:
    try:
        b = line.encode("utf-8", errors="replace")
        if not b.endswith(b"\n"):
            b += b"\n"
        os.write(2, b)
    except OSError:
        pass


def _normalize_request_path(path: str) -> str:
    """GET /foo/ ve /foo aynı rotaya düşsün (curl/tarayıcı farkı)."""
    p = path or "/"
    if len(p) > 1 and p.endswith("/"):
        p = p.rstrip("/")
    return p


def _is_loopback(host: str) -> bool:
    h = (host or "").strip()
    if h in ("127.0.0.1", "::1", "localhost"):
        return True
    if h.startswith("::ffff:") and h.rsplit(":", 1)[-1] == "127.0.0.1":
        return True
    return False


def _read_secret() -> str:
    return (os.environ.get("KANDO_BRIDGE_SECRET") or "").strip()


def _clear_direct_patch_meta() -> None:
    try:
        if DIRECT_PATCH_META_FILE.is_file():
            DIRECT_PATCH_META_FILE.unlink()
    except OSError:
        pass


def _persist_direct_patch_meta(obj: dict) -> None:
    try:
        DIRECT_PATCH_META_FILE.parent.mkdir(parents=True, exist_ok=True)
        DIRECT_PATCH_META_FILE.write_text(
            json.dumps(
                {"auto_approve_safe": bool(obj.get("auto_approve_safe"))},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError:
        pass


def _extract_task_text(content_type: str | None, raw: bytes) -> tuple[str | None, str | None]:
    """(text, error_message) — text None ise hata."""
    ct = (content_type or "").split(";")[0].strip().lower()
    try:
        dec = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "body utf-8 değil"

    if ct == "application/json" or dec.strip().startswith("{"):
        try:
            obj = json.loads(dec)
        except json.JSONDecodeError as e:
            return None, f"json: {e}"
        if isinstance(obj, dict):
            if obj.get("mode") == "direct_patch":
                fv = obj.get("file")
                tv = obj.get("task")
                if not isinstance(fv, str) or not isinstance(tv, str):
                    return None, "direct_patch: file ve task string olmalı"
                fv, tv = fv.strip(), tv.strip()
                if not fv or not tv:
                    return None, "direct_patch: file ve task boş olamaz"
                _persist_direct_patch_meta(obj)
                return f"file: {fv}\ntask: {tv}\n", None
            t = None
            if "text" in obj:
                t = obj.get("text")
            elif "goal" in obj:
                t = obj.get("goal")
            if t is not None:
                if isinstance(t, str):
                    return t.strip(), None
                return None, "json içinde 'text' veya 'goal' string olmalı"
            return None, "json gövdesinde 'text' veya 'goal' alanı gerekli"
        return None, "json gövdesi nesne olmalı"

    if ct == "application/x-www-form-urlencoded":
        qs = parse_qs(dec, keep_blank_values=True)
        vals = qs.get("text") or qs.get("goal") or qs.get("task") or []
        if vals:
            return (vals[0] or "").strip(), None
        return None, "form: text veya task alanı yok"

    if not ct or ct == "text/plain":
        return dec.strip(), None

    # Bilinmeyen content-type: düz metin kabul et
    return dec.strip(), None


def _structured_goal_incomplete(goal: str) -> bool:
    """file: veya task: satırı var ama ikisi de dolu değil."""
    file_p, task_p = extract_file_task(goal)
    if file_p is None and task_p is None:
        return False
    return not (file_p and task_p)


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "KandoBridge/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        _stderr_write("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), fmt % args))

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _reject(self, status: int, msg: str) -> None:
        path = str(REQUEST_FILE.resolve())
        self._send_json(
            status,
            {
                "accepted": False,
                "request_path": path,
                "queued_text": None,
                "error": msg,
            },
        )

    def _reject_no_target_structured(self) -> None:
        path = str(REQUEST_FILE.resolve())
        detail = "instruction içinde hedef dosya yolu çıkarılamadı"
        self._send_json(
            400,
            {
                "accepted": False,
                "request_path": path,
                "queued_text": None,
                "error": detail,
                "status": "partial",
                "execution": "no_target_detected",
                "detail": detail,
            },
        )

    def _check_loopback(self) -> bool:
        host = self.client_address[0]
        if not _is_loopback(host):
            self._reject(403, "yalnızca localhost")
            return False
        return True

    def _check_secret(self) -> bool:
        secret = _read_secret()
        if not secret:
            return True
        token = (self.headers.get("X-Kando-Token") or "").strip()
        auth = (self.headers.get("Authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip() or token
        if token != secret:
            self._reject(401, "geçersiz veya eksik token (X-Kando-Token veya Authorization: Bearer)")
            return False
        return True

    def _send_outbox_json_file(self, file_path: Path) -> None:
        if not file_path.is_file():
            self._send_json(404, {"error": "not found"})
            return
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._check_loopback():
            return
        parsed = urlparse(self.path)
        req_path = _normalize_request_path(parsed.path)
        if req_path in ("/last-result", "/last-execution"):
            if not self._check_secret():
                return
            fp = LAST_RESULT_FILE if req_path == "/last-result" else LAST_EXECUTION_FILE
            self._send_outbox_json_file(fp)
            return
        if req_path == "/agent-last":
            if not self._check_secret():
                return
            self._send_outbox_json_file(AGENT_LAST_FILE)
            return
        if req_path == "/agent-status":
            if not self._check_secret():
                return
            q = parse_qs(parsed.query or "")
            jid = (q.get("id") or [""])[0].strip()
            if not jid:
                self._send_json(400, {"error": "query id gerekli"})
                return
            st = get_job_status(jid, OUTBOX_DIR)
            if st is None:
                self._send_json(404, {"error": "job bulunamadı", "job_id": jid})
                return
            self._send_json(200, st)
            return
        if req_path in ("/", "/health"):
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "kando_bridge_server",
                    "post_task": "POST /task",
                    "post_agent_run": "POST /agent-run",
                    "get_agent_status": "GET /agent-status?id=<job_id>",
                    "get_agent_last": "GET /agent-last",
                },
            )
            return
        self.send_error(404)

    def _handle_agent_run(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            dec = raw.decode("utf-8")
            obj = json.loads(dec)
        except UnicodeDecodeError:
            self._reject(400, "body utf-8 değil")
            return
        except json.JSONDecodeError as e:
            self._reject(400, f"json: {e}")
            return
        if not isinstance(obj, dict):
            self._reject(400, "json nesne olmalı")
            return
        goal = obj.get("goal")
        if not isinstance(goal, str) or not goal.strip():
            self._reject(400, "goal string gerekli")
            return
        auto = bool(obj.get("auto_approve_safe", True))
        job_id = start_agent_job(
            goal.strip(),
            auto,
            repo_root=ROOT,
            outbox_dir=OUTBOX_DIR,
        )
        self._send_json(
            200,
            {
                "accepted": True,
                "job_id": job_id,
                "outbox": str(OUTBOX_DIR.resolve()),
            },
        )

    def do_POST(self) -> None:
        if not self._check_loopback():
            return
        if not self._check_secret():
            return

        parsed = urlparse(self.path)
        req_path = _normalize_request_path(parsed.path)
        if req_path == "/agent-run":
            self._handle_agent_run()
            return
        if req_path != "/task":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b""
        _clear_direct_patch_meta()

        text, err = _extract_task_text(self.headers.get("Content-Type"), raw)
        if err:
            self._reject(400, err)
            return
        if text is None or not text.strip():
            self._reject(400, "boş gövde veya metin yok")
            return

        if _structured_goal_incomplete(text):
            self._reject_no_target_structured()
            return

        try:
            REQUEST_FILE.parent.mkdir(parents=True, exist_ok=True)
            REQUEST_FILE.write_text(text.strip(), encoding="utf-8")
        except OSError as e:
            self._reject(500, f"yazılamadı: {e}")
            return

        path = str(REQUEST_FILE.resolve())
        self._send_json(
            200,
            {
                "accepted": True,
                "request_path": path,
                "queued_text": text.strip(),
            },
        )


def main() -> None:
    ap = argparse.ArgumentParser(description="Kando inbox HTTP bridge (POST /task → request.txt)")
    ap.add_argument(
        "--host",
        default="127.0.0.1",
        help="yalnızca 127.0.0.1 | ::1 | localhost (0.0.0.0 vb. yasak)",
    )
    ap.add_argument("--port", type=int, default=int(os.environ.get("KANDO_BRIDGE_PORT", "8765")))
    args = ap.parse_args()

    if args.host not in _ALLOWED_BIND_HOSTS:
        _stderr_write(
            "Hata: bind adresi yalnızca 127.0.0.1, ::1 veya localhost olabilir.",
        )
        raise SystemExit(2)

    httpd = ThreadingHTTPServer((args.host, args.port), BridgeHandler)
    print(f"kando_bridge_server: http://{args.host}:{args.port}/task | /agent-run (POST)", flush=True)
    print(f"  → {REQUEST_FILE.resolve()}", flush=True)
    print(f"  → agent outbox: {OUTBOX_DIR.resolve()}", flush=True)
    sec = _read_secret()
    print(f"  token: {'ayarlı (KANDO_BRIDGE_SECRET)' if sec else 'kapalı'}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nkapanıyor.", flush=True)
        httpd.shutdown()


if __name__ == "__main__":
    main()
