#!/usr/bin/env python3
"""
Lokal orkestratör: POST /task → doğrudan direct patch (TARGET:) veya agent job.
request.txt / kando_watch kuyruğu yok.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
_SRC = str(ROOT / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_agent = importlib.import_module("kando.agent_runner")
_patch = importlib.import_module("kando.patch_scope")
get_job_status = _agent.get_job_status
start_agent_job = _agent.start_agent_job
extract_file_task = _patch.extract_file_task
OUTBOX_DIR = ROOT / ".lumos" / "outbox"
CURSOR_BRIDGE_DIR = ROOT / ".lumos" / "cursor_bridge"
AGENT_LAST_FILE = OUTBOX_DIR / "agent_last.json"
LAST_RESULT_FILE = OUTBOX_DIR / "last_result.json"
LAST_EXECUTION_FILE = OUTBOX_DIR / "last_execution.json"
DIRECT_PATCH_META_FILE = ROOT / ".lumos" / "inbox" / "direct_patch_meta.json"
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


def _build_target_instruction(rel_path: str | None, task_body: str | None) -> str:
    r = (rel_path or "").strip().replace("\\", "/")
    t = (task_body or "").strip()
    if not r or not t:
        raise ValueError("file/task boş geldi")
    return f"TARGET: {r}\n{t}\n"


_RE_PIPE_FILE_TASK = re.compile(
    r"file:\s*(?P<file>[^|]+?)\s*\|\s*task:\s*(?P<task>.+)",
    re.IGNORECASE | re.DOTALL,
)


def _parse_pipe_file_task(text: str) -> tuple[str, str] | None:
    m = _RE_PIPE_FILE_TASK.search(text.strip())
    if not m:
        return None
    f = m.group("file").strip()
    t = m.group("task").strip()
    if f and t:
        return f, t
    return None


def _cursor_bridge_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC
    env.setdefault("LUMOS_BASE_DIR", str((ROOT / ".lumos").resolve()))
    env.setdefault("LUMOS_REPO_ROOT", str(ROOT.resolve()))
    return env


def _copy_bridge_outputs_to_outbox() -> None:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("last_result.json", "last_execution.json"):
        src = CURSOR_BRIDGE_DIR / name
        dst = OUTBOX_DIR / name
        if src.is_file():
            shutil.copy2(src, dst)


def _summarize_execution_from_outbox() -> str:
    try:
        raw = LAST_EXECUTION_FILE.read_text(encoding="utf-8")
        d = json.loads(raw)
        ex = (d.get("constraints") or {}).get("execution") or {}
        if isinstance(ex, dict):
            er = ex.get("execution_result")
            det = ex.get("detail")
            if er:
                return str(er) + (f" — {det[:200]}" if det else "")
        return "ok"
    except (OSError, json.JSONDecodeError, TypeError):
        return "unknown"


def _run_cursor_bridge(instruction: str) -> tuple[int, str]:
    """cursor_bridge subprocess; sonuçları .lumos/cursor_bridge → outbox kopyalanır."""
    CURSOR_BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

    command_file = CURSOR_BRIDGE_DIR / "command.json"
    command_file.write_text(
        json.dumps(
            {
                "instruction": instruction,
                "execution_mode": "task",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    for name in ("last_result.json", "last_execution.json"):
        try:
            (CURSOR_BRIDGE_DIR / name).unlink()
        except FileNotFoundError:
            pass

    cmd = [sys.executable, "-m", "kando.cursor_bridge"]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=_cursor_bridge_env(),
        capture_output=True,
        text=True,
        timeout=600,
    )
    _copy_bridge_outputs_to_outbox()
    summary = _summarize_execution_from_outbox()
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[:500]
        summary = f"exit={proc.returncode} {summary} {tail}".strip()
    return proc.returncode, summary


def _maybe_agent_auto_patch(blob: str) -> None:
    """Basit yerel agent aksiyonlari: print ekle, yorum ekle, safe touch."""
    try:
        s = (blob or "").strip().lower()
        fp = ROOT / "src" / "core" / "lumos_runtime.py"
        txt = fp.read_text(encoding="utf-8")

        if "print ekle" in s:
            line = 'print("agent auto")'
            if line not in txt:
                txt += f"\n\n{line}\n"
                fp.write_text(txt, encoding="utf-8")
            return

        if "yorum ekle" in s:
            line = "# agent auto comment"
            if line not in txt:
                txt += f"\n\n{line}\n"
                fp.write_text(txt, encoding="utf-8")
            return

        if "safe touch" in s or "dokun" in s:
            line = "# lumos:agent-auto safe touch"
            if line not in txt:
                txt += f"\n\n{line}\n"
                fp.write_text(txt, encoding="utf-8")
            return

    except OSError:
        pass


def _resolve_task_routing(
    content_type: str | None,
    raw: bytes,
) -> tuple[str | None, str | None, str | None]:
    """
    (error, mode, payload)
    mode: 'direct_patch' → TARGET gövdesi; 'agent' → serbest goal metni.
    """
    ct = (content_type or "").split(";")[0].strip().lower()
    try:
        dec = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "body utf-8 değil", None, None

    # --- JSON ---
    if ct == "application/json" or dec.strip().startswith("{"):
        try:
            obj = json.loads(dec)
        except json.JSONDecodeError as e:
            return f"json: {e}", None, None
        if not isinstance(obj, dict):
            return "json gövdesi nesne olmalı", None, None

        fv = obj.get("file")
        tv = obj.get("task") or obj.get("goal")
        if isinstance(tv, str):
            tv = tv.replace("TARGET:", "").strip()
        if isinstance(fv, str):
            fv = fv.strip()
        else:
            fv = ""
        if isinstance(tv, str):
            tv = tv.strip()
        else:
            tv = ""
        if fv and tv:
            if obj.get("auto_approve_safe") is not None:
                _persist_direct_patch_meta(obj)
            inst = _build_target_instruction(fv, tv)
            return None, "direct_patch", inst

        blob = None
        if isinstance(obj.get("text"), str):
            blob = obj["text"].strip()
        elif isinstance(obj.get("goal"), str):
            blob = obj["goal"].strip()
        if blob:
            pipe = _parse_pipe_file_task(blob)
            if pipe:
                inst = _build_target_instruction(pipe[0], pipe[1])
                return None, "direct_patch", inst
            _maybe_agent_auto_patch(blob)
            return None, "agent", blob

        return "json: file+task veya text/goal gerekli", None, None

    # --- form ---
    if ct == "application/x-www-form-urlencoded":
        qs = parse_qs(dec, keep_blank_values=True)
        vals = qs.get("text") or qs.get("goal") or []
        if not vals:
            return "form: text veya goal yok", None, None
        blob = (vals[0] or "").strip()
        pipe = _parse_pipe_file_task(blob)
        if pipe:
            return None, "direct_patch", _build_target_instruction(pipe[0], pipe[1])
        ef, et = extract_file_task(blob)
        if ef and et:
            return None, "direct_patch", _build_target_instruction(ef, et)
        _maybe_agent_auto_patch(blob)
        return None, "agent", blob

    # --- düz metin ---
    blob = dec.strip()
    if not blob:
        return "boş gövde", None, None
    pipe = _parse_pipe_file_task(blob)
    if pipe:
        return None, "direct_patch", _build_target_instruction(pipe[0], pipe[1])
    ef, et = extract_file_task(blob)
    if ef and et:
        return None, "direct_patch", _build_target_instruction(ef, et)
    _maybe_agent_auto_patch(blob)
    return None, "agent", blob


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
        self._send_json(
            status,
            {
                "accepted": False,
                "error": msg,
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
        try:
            Path("logs").mkdir(exist_ok=True)
            with open("logs/bridge.log", "ab") as f:
                f.write(b"\n--- RAW ---\n")
                f.write(self.rfile.peek(4096))
                f.write(b"\n")
        except Exception:
            pass
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
                    "post_task": "POST /task (direct_patch | agent)",
                    "post_agent_run": "POST /agent-run",
                    "get_agent_status": "GET /agent-status?id=<job_id>",
                    "get_agent_last": "GET /agent-last",
                    "get_last_result": "GET /last-result",
                    "get_last_execution": "GET /last-execution",
                },
            )
            return
        self.send_error(404)

    def _handle_agent_run(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            Path("logs").mkdir(exist_ok=True)
            with open("logs/bridge.log", "ab") as f:
                f.write(b"\n--- RAW ---\n")
                f.write(raw)
                f.write(b"\n")
        except Exception:
            pass
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
        try:
            Path("logs").mkdir(exist_ok=True)
            with open("logs/bridge.log", "ab") as f:
                f.write(b"\n--- RAW ---\n")
                f.write(raw)
                f.write(b"\n")
        except Exception:
            pass
        _clear_direct_patch_meta()

        err, mode, payload = _resolve_task_routing(self.headers.get("Content-Type"), raw)
        if err:
            self._reject(400, err)
            return
        assert mode is not None and payload is not None

        if mode == "direct_patch":
            from kando.file_patch_executor import run as direct_run
            ex = direct_run({"instruction": payload, "execution_mode": "task"})
            LAST_EXECUTION_FILE.write_text(json.dumps(ex, ensure_ascii=False, indent=2), encoding="utf-8")
            LAST_RESULT_FILE.write_text(json.dumps({
                "schema_version": "kando.cursor.result.v1",
                "goal_preview": payload[:500],
                "outcome": "applied" if str(ex.get("execution_result") or "") in ("patch_applied", "no_change") else "failed",
                "reason": str(ex.get("detail") or ""),
                "verification_summary": "",
                "task_id": 0,
                "task_status": "",
                "brain_success": True,
                "verified_count": 0,
                "unverified_count": 0,
                "simulation_count": 0,
                "execution": ex,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            self._send_json(
                200,
                {
                    "accepted": True,
                    "mode": "direct_patch",
                    "execution": str(ex.get("execution_result") or ""),
                    "result_path": str(LAST_RESULT_FILE.resolve()),
                    "cursor_bridge_exit": 0,
                },
            )
            return

        # agent
        job_id = start_agent_job(
            payload,
            True,
            repo_root=ROOT,
            outbox_dir=OUTBOX_DIR,
        )
        self._send_json(
            200,
            {
                "accepted": True,
                "mode": "agent",
                "job_id": job_id,
            },
        )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Kando köprü orkestratörü: POST /task (direct_patch | agent), GET outbox",
    )
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
    print(f"kando_bridge_server: http://{args.host}:{args.port}/task (POST)", flush=True)
    print(f"  → outbox: {OUTBOX_DIR.resolve()}", flush=True)
    sec = _read_secret()
    print(f"  token: {'ayarlı (KANDO_BRIDGE_SECRET)' if sec else 'kapalı'}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nkapanıyor.", flush=True)
        httpd.shutdown()


if __name__ == "__main__":
    main()
