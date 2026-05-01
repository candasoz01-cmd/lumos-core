#!/usr/bin/env python3
# ruff: noqa: E402 — sys.path bootstrap before remaining imports
"""
Lokal orkestratör: POST /task → doğrudan direct patch (TARGET:) veya agent job.
request.txt / kando_watch kuyruğu yok.
"""
from __future__ import annotations

import os
import sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "packages/kando_runtime/src"))
sys.path.insert(0, os.path.join(BASE, "kando-ai/packages/kando_runtime/src"))

import difflib
import importlib
import json
import secrets
import time
import re
import shutil
import subprocess
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
PENDING_APPROVALS_DIR = ROOT / ".lumos" / "pending_approvals"
_bridge_public_bind = False


def _safe_pending_approval_path(repo_root: Path, rel: str) -> Path | None:
    r = (rel or "").strip().replace("\\", "/")
    if not r or ".." in r.split("/"):
        return None
    if os.path.isabs(r):
        return None
    pending_root = (repo_root / ".lumos" / "pending_approvals").resolve()
    cand = (repo_root / r).resolve()
    try:
        cand.relative_to(pending_root)
    except ValueError:
        return None
    return cand if cand.is_file() else None


def _stderr_write(line: str) -> None:
    try:
        b = line.encode("utf-8", errors="replace")
        if not b.endswith(b"\n"):
            b += b"\n"
        os.write(2, b)
    except OSError:
        pass


try:
    from core.chat_memory_prompt import format_chat_prompt_prefix
except ImportError:

    def format_chat_prompt_prefix(_repo_root: Path) -> str:
        return (
            "Sen Lumos'sun; kendini Lumos olarak tanıt; kısa ve doğal Türkçe konuş.\n"
            "İstek belirsizse varsayım yapma; tek cümlelik netleştirme sorusu sor. "
            "Yanıtı «Tamam.» veya «Anladım.» ile başlatma.\n"
            "Video görevinde kullanıcı YouTube, yerel dosya veya URL/API kaynağı belirtmediyse: "
            "«video gönderiyorum», «hemen izleyebilirsin», «öneriyorum» gibi ifadeler kullanma.\n\n"
            "---\n\n"
        )


try:
    from kando_runtime.bridge_intent import classify_bridge_message_intent
except ImportError:

    def classify_bridge_message_intent(text: str) -> str:
        return "task"


try:
    from kando_runtime.task_dispatch import (
        DISPATCH_PENDING_APPROVAL_SCHEMA,
        attach_execution_dispatch_to_out,
    )
except ImportError:
    DISPATCH_PENDING_APPROVAL_SCHEMA = "lumos.dispatch_pending_approval.v1"

    def attach_execution_dispatch_to_out(out: dict, *, repo_root: Path | None = None) -> None:
        return


try:
    from kando_runtime.dangerous_command import (
        destructive_command_user_message_tr,
        destructive_surface_blocks_task,
    )
except ImportError:

    def destructive_surface_blocks_task(text: str) -> tuple[bool, str | None]:
        return False, None

    def destructive_command_user_message_tr() -> str:
        return "Yıkıcı komut reddedildi"


try:
    from kando_runtime.lumos_gate import (
        HIGH_RISK_KEYWORDS,
        is_high_risk_keyword_text as is_high_risk,
    )
except ImportError:
    HIGH_RISK_KEYWORDS = ("sil", "delete", "remove", "unlink")

    def is_high_risk(text: str) -> bool:
        t = (text or "").lower()
        if any(k in t for k in HIGH_RISK_KEYWORDS):
            return True
        return bool(re.search(r"(?<![a-z0-9_])rm(?![a-z0-9_])", t))


def _normalize_request_path(path: str) -> str:
    p = path or "/"
    if len(p) > 1 and p.endswith("/"):
        p = p.rstrip("/")
    return p


def _is_loopback(host: str) -> bool:
    h = (host or "").strip()
    if h in ("0.0.0.0", "::1", "localhost"):
        return True
    if h.startswith("::ffff:") and h.rsplit(":", 1)[-1] == "0.0.0.0":
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


def _normalize_json_task_file_field(fv: str) -> str:
    """Panel/etiket hataları: file alanında yalnızca repo içi relatif yol olmalı."""
    t = (fv or "").strip()
    if not t:
        return ""
    t = re.sub(r"(?i)^dosya yolu:\s*", "", t).strip()
    t = re.sub(r"(?i)^dosya:\s*", "", t).strip()
    t = re.sub(r"(?i)^target:\s*", "", t).strip()
    if re.fullmatch(r"(?i)görev\s*\(sistemde işlem\)", t):
        return ""
    if t.casefold() == "görev":
        return ""
    return t


def _extract_first_repo_path_fragment(text: str) -> str:
    if not (text or "").strip():
        return ""
    m = re.search(r"\b[\w./\\-]+\.\w{2,16}\b", text)
    if not m:
        return ""
    return m.group(0).replace("\\", "/")


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


INTENT_SYNONYMS = {
    "print": ["print", "yazdır", "log", "debug"],
    "comment": ["yorum", "aciklama", "not"],
    "safe_touch": ["safe touch", "dokun", "guvenli dokun"],
}

AGENT_AUTO_ACTIONS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("print ekle", "print"), 'print("agent auto")'),
    (("yorum ekle", "comment"), "# handles logging"),
    (("safe touch", "dokun", "safe_touch"), "# lumos:agent-auto safe touch"),
)


def _extract_target_files(blob: str) -> list[Path]:
    s = (blob or "").lower()

    mapping = {
        "lumos_runtime.py": ROOT / "src/core/lumos_runtime.py",
        "logfmt.py": ROOT / "src/core/logfmt.py",
        "memory.py": ROOT / "src/memory/memory.py",
    }

    found: list[Path] = []
    for name, path in mapping.items():
        if name in s:
            found.append(path)

    return found


def detect_context(txt: str) -> str:
    if "class " in txt:
        return "class"
    if "def " in txt:
        return "function"
    return "top"


def generate_comment_from_code(txt: str) -> str:
    low = txt.lower()
    if "log" in low:
        return "# handles logging"
    if "memory" in low or "sessionmemory" in low:
        return "# manages memory state"
    if "context" in low:
        return "# holds execution context"

    m = re.search(r"def\s+(\w+)", txt)
    if m:
        return f"# function {m.group(1)}"

    m = re.search(r"class\s+(\w+)", txt)
    if m:
        return f"# class {m.group(1)}"

    return "# handles logging"


def insert_above_definition(lines: list[str], line: str) -> list[str]:
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("def ") or s.startswith("class "):
            if not (s.startswith("class SessionMemory") or s.startswith("def logfmt")):
                continue
            if i > 0 and lines[i - 1].strip() == line.strip():
                return lines
            lines.insert(i, line)
            return lines
    return lines


def smart_insert(txt: str, line: str) -> str:
    s = line.strip()
    if s.startswith("class ") or s.startswith("def "):
        return txt
    lines = txt.splitlines()
    if any(line.strip() == ln.strip() for ln in lines):
        return txt

    n0 = len(lines)
    lines = insert_above_definition(list(lines), line)
    if len(lines) != n0:
        return "\n".join(lines)

    ctx = detect_context(txt)

    last_import = -1
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("import ") or s.startswith("from "):
            last_import = i

    if last_import != -1:
        lines.insert(last_import + 1, line)
        return "\n".join(lines)

    for i, ln in enumerate(lines):
        if ln.strip().startswith("class "):
            base_indent = len(ln) - len(ln.lstrip())
            indent = " " * (base_indent + 4)
            lines.insert(i + 1, indent + line)
            return "\n".join(lines)

    if ctx == "function":
        for i, ln in enumerate(lines):
            st = ln.strip()
            if st.startswith("def ") or st.startswith("class "):
                base_indent = len(ln) - len(ln.lstrip())
                indent = " " * (base_indent + 4)
                lines.insert(i + 1, indent + line)
                return "\n".join(lines)

    return txt + "\n\n" + line + "\n"


def _expand_intent_blob(blob: str) -> str:
    """Metne kanonik intent anahtarlarını ekler (INTENT_SYNONYMS eşleşmeleri)."""
    low = (blob or "").strip().lower()
    expanded = low
    tokens = re.findall(r"[a-zA-Z0-9_çğıöşüÇĞİÖŞÜ]+", low)

    for canon, words in INTENT_SYNONYMS.items():
        for word in words:
            w = word.lower()
            if " " in w:
                if w in low:
                    expanded += f" {canon}"
                    break
            else:
                if w in tokens:
                    expanded += f" {canon}"
                    break
    return expanded


def _parse_agent_file_action(blob: str) -> tuple[Path, str] | None:
    """Tek hedef dosya + tek satır (ilk eşleşme veya eş anlamlı fallback)."""
    targets = _extract_target_files(blob)
    fp = targets[0] if targets else (ROOT / "src" / "core" / "lumos_runtime.py")
    expanded = _expand_intent_blob(blob)
    try:
        file_txt = fp.read_text(encoding="utf-8")
    except OSError:
        file_txt = ""

    for triggers, line in AGENT_AUTO_ACTIONS:
        if any(trigger in expanded for trigger in triggers):
            out = (
                generate_comment_from_code(file_txt)
                if line == "# handles logging"
                else line
            )
            return fp, out

    if "print" in expanded:
        return fp, 'print("agent auto debug")'
    if "comment" in expanded:
        return fp, generate_comment_from_code(file_txt)
    if "safe_touch" in expanded:
        return fp, "# lumos:agent-auto safe touch"

    return None


def _maybe_agent_auto_patch(blob: str) -> None:
    """Multi-action: aynı istekte birden fazla aksiyon; INTENT_SYNONYMS ile genişletilmiş eşleşme."""
    try:
        expanded = _expand_intent_blob(blob)
        targets = _extract_target_files(blob)
        if not targets:
            targets = [ROOT / "src" / "core" / "lumos_runtime.py"]

        for fp in targets:
            txt = fp.read_text(encoding="utf-8")
            updated = False
            for triggers, line in AGENT_AUTO_ACTIONS:
                if not any(trigger in expanded for trigger in triggers):
                    continue
                insert_line = (
                    generate_comment_from_code(txt)
                    if line == "# handles logging"
                    else line
                )
                new_txt = smart_insert(txt, insert_line)
                if new_txt != txt:
                    updated = True
                    txt = new_txt
            if updated:
                fp.write_text(txt, encoding="utf-8")

    except OSError:
        pass


def _inject_task_obj_title_fields(
    content_type: str | None,
    raw: bytes,
) -> bytes:
    """POST /task JSON gövdesine task_obj.title ve raw_text ekle (onay payload ile uyumlu)."""
    ct = (content_type or "").split(";")[0].strip().lower()
    try:
        dec = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw
    if ct != "application/json" and not dec.lstrip().startswith("{"):
        return raw
    try:
        obj = json.loads(dec)
    except json.JSONDecodeError:
        return raw
    if not isinstance(obj, dict):
        return raw
    tv = obj.get("task") or obj.get("goal")
    if isinstance(tv, str):
        tv = tv.replace("TARGET:", "").strip()
    else:
        tv = ""
    if tv:
        obj["title"] = tv
        obj["raw_text"] = tv
    try:
        return json.dumps(obj, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError):
        return raw


def _raw_json_requires_clarification(raw: bytes) -> bool:
    """POST /task JSON: requires_clarification True → gate pending (yürütme yok)."""
    try:
        dec = raw.decode("utf-8")
        obj = json.loads(dec)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return isinstance(obj, dict) and obj.get("requires_clarification") is True


def _task_surface_for_destructive_scan(
    mode: str, payload: str, umsg: str | None
) -> str:
    parts: list[str] = []
    s = (umsg or "").strip()
    if s:
        parts.append(s)
    p = (payload or "").strip()
    if p:
        parts.append(p)
    return "\n".join(parts)


def _raw_json_task_type(raw: bytes) -> str | None:
    """POST /task JSON: task_type → lumos execution_dispatch için (video|image|file|shell|generic|media|system)."""
    try:
        dec = raw.decode("utf-8")
        obj = json.loads(dec)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    tt = obj.get("task_type")
    if tt is None:
        return None
    if isinstance(tt, str) and not tt.strip():
        return None
    return str(tt).strip()


def _video_task_prompt_fields_for_clarity(raw: bytes) -> tuple[str, bool] | None:
    """Video JSON görevinde (prompt, medya_ref_var) veya video değilse None."""
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    if str(obj.get("task_type") or "").strip().lower() != "video":
        return None
    prompt = str(obj.get("prompt") or "").strip()
    task_blob = "\n".join(
        str(x or "") for x in (obj.get("task"), obj.get("goal"), obj.get("raw_text"))
    )
    from core.video_prompt_clarity import video_prompt_has_media_ref_in_task_blob

    has_ref = video_prompt_has_media_ref_in_task_blob(task_blob)
    return (prompt, has_ref)


def _approval_payload_display_text(rec: dict) -> str:
    """Disk + API onay kaydında title/raw_text için görünen görev metni."""
    if not isinstance(rec, dict):
        return ""
    for k in ("raw_text", "title", "goal"):
        v = str(rec.get(k) or "").strip()
        if v:
            return v
    nt = rec.get("normalized_task")
    if isinstance(nt, dict):
        for k in (
            "ingest_raw_text",
            "ingest_title",
            "target_body",
            "agent_blob",
        ):
            v = str(nt.get(k) or "").strip()
            if v:
                return v
    op = str(rec.get("original_payload") or "").strip()
    if not op:
        return ""
    lines = [ln.strip() for ln in op.splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        if ln.upper().startswith("TARGET:") and i + 1 < len(lines):
            return lines[i + 1]
    return op


def _resolve_task_routing(
    content_type: str | None,
    raw: bytes,
) -> tuple[str | None, str | None, str | None, str]:
    """
    (error, mode, payload, user_message)
    user_message: onay kartı / UI için ham görev metni (boş olabilir).
    mode: 'direct_patch' → TARGET gövdesi; 'agent' → serbest goal metni.
    """
    ct = (content_type or "").split(";")[0].strip().lower()
    try:
        dec = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "body utf-8 değil", None, None, ""

    # --- JSON ---
    if ct == "application/json" or dec.strip().startswith("{"):
        try:
            obj = json.loads(dec)
        except json.JSONDecodeError as e:
            return f"json: {e}", None, None, ""
        if not isinstance(obj, dict):
            return "json gövdesi nesne olmalı", None, None, ""

        fv = obj.get("file")
        tv = obj.get("task") or obj.get("goal")
        if isinstance(tv, str):
            tv = tv.replace("TARGET:", "").strip()
        else:
            tv = ""
        if isinstance(fv, str):
            fv = _normalize_json_task_file_field(fv)
        else:
            fv = ""
        if isinstance(tv, str):
            tv = tv.strip()
        else:
            tv = ""
        # raw_text genelde her zaman dolu; bazı istemci yollarında task/goal eksik kalabiliyor.
        if not tv and isinstance(obj.get("raw_text"), str):
            rt = (obj.get("raw_text") or "").strip()
            lines = [ln.strip() for ln in rt.splitlines() if ln.strip()]
            for i, ln in enumerate(lines):
                if ln.upper().startswith("TARGET:") and i + 1 < len(lines):
                    tv = lines[i + 1].strip()
                    break
            if not tv and lines:
                tv = lines[-1]
        if not fv and tv:
            fv = _extract_first_repo_path_fragment(tv)
        if fv and tv:
            if obj.get("auto_approve_safe") is not None:
                _persist_direct_patch_meta(obj)
            inst = _build_target_instruction(fv, tv)
            return None, "direct_patch", inst, tv

        if isinstance(obj.get("text"), str) and isinstance(obj.get("goal"), str):
            tt = obj["text"].strip()
            gg = obj["goal"].strip()
            if tt and gg:
                pipe = _parse_pipe_file_task(tt)
                if pipe:
                    inst = _build_target_instruction(pipe[0], pipe[1])
                    return None, "direct_patch", inst, pipe[1].strip()
                return None, "agent", f"{tt}\n\n[Görev: {gg}]", gg

        blob = None
        if isinstance(obj.get("text"), str):
            blob = obj["text"].strip()
        elif isinstance(obj.get("goal"), str):
            blob = obj["goal"].strip()
        if blob:
            pipe = _parse_pipe_file_task(blob)
            if pipe:
                inst = _build_target_instruction(pipe[0], pipe[1])
                return None, "direct_patch", inst, pipe[1].strip()
            return None, "agent", blob, blob

        # task/goal alanı dolu ama yukarıda file+task eşleşmesi yoksa: serbest agent gövdesi
        if tv:
            pipe = _parse_pipe_file_task(tv)
            if pipe:
                inst = _build_target_instruction(pipe[0], pipe[1])
                return None, "direct_patch", inst, pipe[1].strip()
            ef, et = extract_file_task(tv)
            if ef and et:
                return None, "direct_patch", _build_target_instruction(ef, et), et.strip()
            return None, "agent", tv, tv

        return "json: file+task veya text/goal gerekli", None, None, ""

    # --- form ---
    if ct == "application/x-www-form-urlencoded":
        qs = parse_qs(dec, keep_blank_values=True)
        vals = qs.get("text") or qs.get("goal") or []
        if not vals:
            return "form: text veya goal yok", None, None, ""
        blob = (vals[0] or "").strip()
        pipe = _parse_pipe_file_task(blob)
        if pipe:
            return None, "direct_patch", _build_target_instruction(pipe[0], pipe[1]), pipe[
                1
            ].strip()
        ef, et = extract_file_task(blob)
        if ef and et:
            return None, "direct_patch", _build_target_instruction(ef, et), et.strip()
        return None, "agent", blob, blob

    # --- düz metin ---
    blob = dec.strip()
    if not blob:
        return "boş gövde", None, None, ""
    pipe = _parse_pipe_file_task(blob)
    if pipe:
        return None, "direct_patch", _build_target_instruction(pipe[0], pipe[1]), pipe[
            1
        ].strip()
    ef, et = extract_file_task(blob)
    if ef and et:
        return None, "direct_patch", _build_target_instruction(ef, et), et.strip()
    return None, "agent", blob, blob


def _coerce_chat_history(raw: object) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        out.append({"role": role, "content": content})
    return out


def _turns_including_current_message(
    message: str, turns: list[dict[str, str]]
) -> list[dict[str, str]]:
    """`message` her zaman güncel kullanıcı cümlesi; history'de yoksa transcript sonuna eklenir."""
    msg = (message or "").strip()
    if not turns:
        return [{"role": "user", "content": msg}] if msg else []
    last = turns[-1]
    if last["role"] == "user" and last["content"] == msg:
        return turns
    return turns + [{"role": "user", "content": msg}]


def _chat_input_for_llm(
    message: str,
    turns: list[dict[str, str]],
    *,
    prefix: str = "",
) -> str:
    msg = (message or "").strip()
    full = _turns_including_current_message(msg, turns)
    if not full:
        body = f"Kısa ve doğal cevap ver: {msg}"
    elif len(full) == 1 and full[0]["role"] == "user":
        body = f"Kısa ve doğal cevap ver: {full[0]['content']}"
    else:
        lines: list[str] = [
            "Aşağıdaki konuşmaya göre son kullanıcı mesajına kısa ve doğal Türkçe cevap ver.",
            "",
        ]
        for t in full:
            lab = "Kullanıcı" if t["role"] == "user" else "Asistan"
            lines.append(f"{lab}: {t['content']}")
        body = "\n".join(lines)
    return (prefix + body) if prefix else body


def _augment_chat_input_for_user_clarity(message: str, input_text: str) -> str:
    """Belirsiz isteklerde LLM'e netleştirme önceliği ve 'Tamam.' giriş yasağı hatırlatması."""
    try:
        from core.user_intent_classifier import classify_user_message_intent

        ui = classify_user_message_intent((message or "").strip())
        if ui.label != "UNCERTAIN" and not ui.clarification_needed:
            return input_text
    except Exception:
        return input_text
    return (
        input_text
        + "\n\n[Görev — öncelik] Bu kullanıcı mesajı belirsiz sayıldı. Ana nesne, sahne veya amaç net değilse varsayım yapma; "
        "tek cümlelik kısa bir netleştirme sorusu sor. Yanıtı «Tamam.», «Anladım.» veya benzeri onay dolgusuyla başlatma."
    )


_CHAT_INTENT_ONLY_SUFFIX = """
[Adım 1 — yalnızca iç karar]
Son kullanıcı ihtiyacını tek cümleyle özetle. Çıktın tam olarak tek satır olsun ve tam biçim:
INTENT: <buraya tek cümle>

Açıklama ekleme, kullanıcıya cevap yazma, ikinci satır kullanma.
""".strip()

_CHAT_REPLY_WITH_LOCKED_INTENT_SUFFIX = """
[Adım 2 — kilit INTENT]
Yukarıdaki sohbet bağlamı geçerlidir. Aşağıdaki iç karar bu turda sabittir; yeniden yazma, genişletme veya değiştirme.

Kilit INTENT:
INTENT: __INTENT_PLACEHOLDER__

Görev: Bu INTENT’e uygun olarak yalnızca kullanıcıya göstereceğin doğal Türkçe cevabı yaz.
INTENT satırı veya başlık kullanma; doğrudan cevap metni.
""".strip()

_INTENT_FALLBACK = "Kullanıcıya mesajına uygun kısa ve yardımcı cevap vermek."


def _parse_intent_only(raw: str) -> str:
    """İlk çağrı çıktısından INTENT tek satırını alır."""
    t = (raw or "").strip()
    if not t:
        return ""
    first = t.split("\n", 1)[0].strip()
    if first.upper().startswith("INTENT:"):
        return first.split(":", 1)[1].strip()
    return first


def build_chat_reply(message: str, history: list | None = None) -> dict:
    """POST /chat: önce tek satır INTENT, sonra bu INTENT'e bağlı cevap (iki ayrı LLM çağrısı)."""
    from openai import OpenAI

    turns = _coerce_chat_history(history)
    mem_prefix = format_chat_prompt_prefix(ROOT)
    input_base = _chat_input_for_llm(message, turns, prefix=mem_prefix)
    input_base = _augment_chat_input_for_user_clarity(message, input_base)

    step1_input = input_base.rstrip() + "\n\n" + _CHAT_INTENT_ONLY_SUFFIX + "\n"
    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

    r1 = client.responses.create(model=model, input=step1_input)
    intent = _parse_intent_only(getattr(r1, "output_text", None) or "")
    if not intent:
        intent = _INTENT_FALLBACK

    step2_input = (
        input_base.rstrip()
        + "\n\n"
        + _CHAT_REPLY_WITH_LOCKED_INTENT_SUFFIX.replace("__INTENT_PLACEHOLDER__", intent, 1)
        + "\n"
    )
    r2 = client.responses.create(model=model, input=step2_input)
    reply = (getattr(r2, "output_text", None) or "").strip()

    return {
        "reply": reply,
        "blocked": False,
        "mode": "chat",
        "intent": intent,
    }


def extract_chat_task_file_ref(message: str) -> str | None:
    """Mesajdaki ilk dosya.adı eşlemesi (örn. README.md, src/foo.py)."""
    hit = re.search(r"\b[\w./\\-]+\.\w{2,16}\b", message or "")
    if not hit:
        return None
    return hit.group(0).replace("\\", "/")


_PENDING_VERB_LABELS: tuple[tuple[str, str], ...] = (
    ("düzelt", "güncellenecek"),
    ("değiştir", "güncellenecek"),
    ("güncelle", "güncellenecek"),
    ("ekle", "eklenecek"),
    ("sil", "silinecek"),
    ("oluştur", "oluşturulacak"),
    ("yaz", "yazılacak"),
)


def pending_summary_from_payload(payload: str, norm: dict | None) -> str:
    """Kısa onay özeti: hedef dosya + eylem (örn. README.md güncellenecek)."""
    rel = ""
    if isinstance(norm, dict):
        rel = str(norm.get("target_rel") or "").strip().replace("\\", "/")
    if not rel:
        hit = re.search(r"\b[\w./\\-]+\.\w{2,16}\b", payload or "")
        if hit:
            rel = hit.group(0).replace("\\", "/")
    pl = (payload or "").lower()
    action = "işlem uygulanacak"
    for key, label in _PENDING_VERB_LABELS:
        if key in pl:
            action = label
            break
    if rel:
        return f"{rel} {action}"
    return action


def _line_diff_stats(old: str, new: str) -> dict[str, int]:
    a = old.splitlines()
    b = new.splitlines()
    sm = difflib.SequenceMatcher(a=a, b=b)
    added = removed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace":
            removed += i2 - i1
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "insert":
            added += j2 - j1
    return {"added": added, "removed": removed}


def _collect_applied_paths(obj: object, seen: list[str]) -> None:
    if isinstance(obj, dict):
        ap = obj.get("applied_path")
        if isinstance(ap, str) and ap.strip():
            s = ap.strip().replace("\\", "/")
            if s not in seen:
                seen.append(s)
        for v in obj.values():
            _collect_applied_paths(v, seen)
    elif isinstance(obj, list):
        for x in obj:
            _collect_applied_paths(x, seen)


def _diff_stats_for_repo_file(rel: str, repo_root: Path) -> dict[str, int] | None:
    root = repo_root.resolve()
    fp = (root / rel).resolve()
    try:
        fp.relative_to(root)
    except Exception:
        return None
    bak = fp.with_name(fp.name + ".bak")
    if not fp.is_file() or not bak.is_file():
        return None
    try:
        old = bak.read_text(encoding="utf-8", errors="replace")
        new = fp.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return _line_diff_stats(old, new)


def _primary_executor_dict(out: dict) -> dict | None:
    lr = out.get("last_result")
    if isinstance(lr, dict):
        ex = lr.get("execution")
        if isinstance(ex, dict):
            return ex
    le = out.get("last_execution")
    return le if isinstance(le, dict) else None


def _compute_execution_enrichment_bundle(out: dict, repo_root: Path) -> dict[str, object]:
    files: list[str] = []
    _collect_applied_paths(out.get("last_result"), files)
    _collect_applied_paths(out.get("last_execution"), files)
    hb = out.get("http_body")
    if isinstance(hb, dict):
        _collect_applied_paths(hb, files)

    ex = _primary_executor_dict(out) or {}
    diff_stats: dict[str, int] = {"added": 0, "removed": 0}
    if files:
        ds = _diff_stats_for_repo_file(files[0], repo_root)
        if ds is not None:
            diff_stats = ds

    hb_dict = hb if isinstance(hb, dict) else {}
    er = str(ex.get("execution_result") or "")
    if len(files) == 1 and er == "no_change":
        summary = f"{files[0]} — değişiklik yok"
    elif len(files) == 1:
        summary = f"{files[0]} güncellendi"
    elif len(files) > 1:
        summary = f"{len(files)} dosya güncellendi"
    else:
        lg = hb_dict.get("lumos_gate") if isinstance(hb_dict.get("lumos_gate"), dict) else {}
        rs = str(lg.get("reasoning_summary") or "").strip()
        if rs:
            summary = rs[:160] + ("..." if len(rs) > 160 else "")
        elif str(hb_dict.get("mode") or "") == "agent":
            summary = "Arka plan işi başlatıldı"
        else:
            summary = "İşlem tamamlandı"

    return {
        "summary": summary,
        "files_changed": files,
        "diff_stats": diff_stats,
    }


def merge_execution_enrichment_into_out(out: dict, repo_root: Path) -> None:
    """Başarılı yürütme yanıtına summary / files_changed / diff_stats ekler."""
    if out.get("execution_mode") == "pending_approval":
        return
    body = out.get("http_body")
    if not isinstance(body, dict):
        return
    if body.get("requires_approval") is True:
        return
    bundle = _compute_execution_enrichment_bundle(out, repo_root)
    body["summary"] = bundle["summary"]
    body["files_changed"] = bundle["files_changed"]
    body["diff_stats"] = bundle["diff_stats"]


def persist_last_result_from_out(out: dict) -> None:
    """Başarılı gate çıktısında last_execution / last_result dosyalarını yazar."""
    if int(out.get("http_status") or 200) != 200:
        return
    last_ex = out.get("last_execution")
    last_res = out.get("last_result")
    if not isinstance(last_ex, dict) or not isinstance(last_res, dict):
        return
    try:
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        LAST_EXECUTION_FILE.write_text(
            json.dumps(last_ex, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        LAST_RESULT_FILE.write_text(
            json.dumps(last_res, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def task_pipeline_result_for_chat(out: dict) -> dict:
    """Gate+execute çıktısını JSON-safe task_result sözlüğüne çevirir."""

    def conv(x: object) -> object:
        if isinstance(x, dict):
            return {str(k): conv(v) for k, v in x.items()}
        if isinstance(x, list):
            return [conv(i) for i in x]
        if isinstance(x, (str, int, float, bool)) or x is None:
            return x
        return str(x)

    keys = (
        "policy_ok",
        "http_status",
        "execution_mode",
        "final_decision",
        "http_body",
        "pending_approval_record",
        "last_execution",
        "last_result",
        "gate_complete",
        "approval_file",
        "approval_token",
    )
    d: dict = {}
    for k in keys:
        if k in out:
            d[k] = conv(out[k])
    hb = d.get("http_body")
    if isinstance(hb, dict):
        for k in (
            "summary",
            "files_changed",
            "diff_stats",
            "task_type",
            "dispatch_execution_plan",
            "execution_dispatch",
            "system_execution",
        ):
            if k in hb:
                d[k] = conv(hb[k])
    if d.get("execution_mode") == "pending_approval":
        d["requires_approval"] = True
        rec = out.get("pending_approval_record")
        if isinstance(rec, dict):
            d["pending_summary"] = pending_summary_from_payload(
                str(rec.get("original_payload") or ""),
                rec.get("normalized_task") if isinstance(rec.get("normalized_task"), dict) else None,
            )
            if rec.get("schema_version") == DISPATCH_PENDING_APPROVAL_SCHEMA:
                d["approval_kind"] = "dispatch_medium"
    return d


def _is_dispatch_medium_pending(out: dict) -> bool:
    pr = out.get("pending_approval_record")
    if not isinstance(pr, dict):
        return False
    return pr.get("schema_version") == DISPATCH_PENDING_APPROVAL_SCHEMA


def build_pending_approvals_list() -> list[dict]:
    """`.lumos/pending_approvals/*.json` → panel / GET /pending_approvals için kayıt listesi."""
    items: list[dict] = []
    try:
        PENDING_APPROVALS_DIR.mkdir(parents=True, exist_ok=True)
        for p in sorted(PENDING_APPROVALS_DIR.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            rel = data.get("approval_file") or f".lumos/pending_approvals/{p.name}"
            rs = data.get("reasoning_snapshot") if isinstance(data.get("reasoning_snapshot"), dict) else {}
            summ = str(data.get("reasoning_summary") or "").strip()
            if not summ:
                summ = str(rs.get("summary") or "").strip()
            ps = str(data.get("pending_summary") or "").strip()
            if not ps:
                ps = pending_summary_from_payload(
                    str(data.get("original_payload") or ""),
                    data.get("normalized_task") if isinstance(data.get("normalized_task"), dict) else None,
                )
            title_g = str(
                data.get("title")
                or data.get("raw_text")
                or data.get("goal")
                or ""
            ).strip()
            if not title_g:
                op = str(data.get("original_payload") or "").strip()
                title_g = op[:800] if op else ps[:800] if ps else ""
            raw_g = str(data.get("raw_text") or title_g or "").strip()
            items.append(
                {
                    "approval_file": str(rel).replace("\\", "/"),
                    "approval_token": str(data.get("approval_token") or ""),
                    "risk_level": str(data.get("risk_level") or "high"),
                    "reasoning_summary": summ[:2000],
                    "pending_summary": ps,
                    "title": title_g,
                    "goal": title_g,
                    "raw_text": raw_g,
                    "original_payload": str(data.get("original_payload") or "")[:4000],
                    "created_at": str(data.get("created_at") or ""),
                    "used": bool(data.get("used")),
                }
            )
    except OSError:
        pass
    return items


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "KandoBridge/1.0"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, X-Kando-Token, Authorization",
        )
        super().end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        _stderr_write("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), fmt % args))

    def do_OPTIONS(self) -> None:
        if not self._check_loopback():
            return
        self.send_response(204)
        self.end_headers()

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
        if _bridge_public_bind:
            return True
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

    def _attach_pending_approval_to_out(self, out: dict) -> None:
        """Yüksek risk pending: onay dosyası oluşturur (/task ile aynı)."""
        if out.get("execution_mode") != "pending_approval":
            return
        rec = out.get("pending_approval_record")
        approval_rel = ""
        approval_token = ""
        if isinstance(rec, dict):
            PENDING_APPROVALS_DIR.mkdir(parents=True, exist_ok=True)
            fname = f"approval_{int(time.time() * 1000)}.json"
            p = PENDING_APPROVALS_DIR / fname
            approval_rel = f".lumos/pending_approvals/{fname}"
            rec_out = dict(rec)
            rec_out["approval_file"] = approval_rel
            rec_out["approval_token"] = secrets.token_hex(16)
            display_msg = _approval_payload_display_text(rec_out)
            if display_msg:
                rec_out["title"] = display_msg
                rec_out["raw_text"] = display_msg
            rec_out["pending_summary"] = pending_summary_from_payload(
                str(rec_out.get("original_payload") or ""),
                rec_out.get("normalized_task") if isinstance(rec_out.get("normalized_task"), dict) else None,
            )
            approval_token = rec_out["approval_token"]
            try:
                p.write_text(
                    json.dumps(rec_out, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                out["pending_approval_record"] = rec_out
            except OSError:
                approval_rel = ""
                approval_token = ""
        out["approval_file"] = approval_rel
        out["approval_token"] = approval_token

    def _send_medium_dispatch_pending_http_response(self, out: dict) -> None:
        """Orta risk dispatch: /task yanıtı gate pending ile aynı yapı, farklı mesaj."""
        ps = ""
        pr = out.get("pending_approval_record")
        if isinstance(pr, dict):
            ps = str(pr.get("pending_summary") or "")
        hb = out.get("http_body") if isinstance(out.get("http_body"), dict) else {}
        dk = str(hb.get("decision_kind") or "").strip().lower()
        if dk not in ("blocked", "unclear", "proceed", "conflict"):
            dk = "proceed"
        self._send_json(
            200,
            {
                "accepted": True,
                "requires_approval": True,
                "error": "",
                "message": "Lumos: orta riskli sistem yürütmesi, kullanıcı onayı bekleniyor",
                "decision_kind": dk,
                "lumos_gate": out,
                "approval_file": out.get("approval_file") or "",
                "approval_token": out.get("approval_token") or "",
                "pending_summary": ps,
                "task_type": hb.get("task_type"),
                "dispatch_execution_plan": hb.get("dispatch_execution_plan"),
                "execution_dispatch": hb.get("execution_dispatch"),
            },
        )

    def _send_pending_approvals_json(self) -> None:
        raw = build_pending_approvals_list()
        wrapped = [
            {**x, "detail": (x.get("reasoning_summary") or "")[:800]} for x in raw
        ]
        self._send_json(200, {"pending": wrapped})

    def _send_pending_approvals_array_response(self) -> None:
        arr = build_pending_approvals_list()
        body = json.dumps(arr, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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
                f.write(b"\n--- GET ")
                f.write((parsed.path or "").encode("utf-8", errors="replace"))
                f.write(b"\n")
        except OSError:
            pass
        req_path = _normalize_request_path(parsed.path)
        if req_path in ("/last-result", "/last-execution", "/outbox"):
            if not self._check_secret():
                return
            if req_path == "/last-execution":
                fp = LAST_EXECUTION_FILE
            else:
                fp = LAST_RESULT_FILE
            self._send_outbox_json_file(fp)
            return
        if req_path == "/pending_approvals":
            if not self._check_secret():
                return
            self._send_pending_approvals_array_response()
            return
        if req_path == "/pending-approvals":
            if not self._check_secret():
                return
            self._send_pending_approvals_json()
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
        if req_path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "gate": True,
                    "llm": True,
                    "mode": "secure",
                },
            )
            return
        if req_path == "/":
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "kando_bridge_server",
                    "post_task": "POST /task (direct_patch | agent)",
                    "post_chat": "POST /chat {message} → gate + execute",
                    "post_replay": "POST /replay (dry_run audit)",
                    "post_approve": "POST /approve (pending high-risk)",
                    "post_agent_run": "POST /agent-run (lumos_gate zorunlu)",
                    "get_health": "GET /health",
                    "get_agent_status": "GET /agent-status?id=<job_id>",
                    "get_agent_last": "GET /agent-last",
                    "get_last_result": "GET /last-result",
                    "get_last_execution": "GET /last-execution",
                    "get_outbox": "GET /outbox (last_result.json)",
                    "get_pending_approvals": "GET /pending-approvals",
                    "get_pending_approvals_array": "GET /pending_approvals (JSON array)",
                },
            )
            return
        self.send_error(404)

    def _complete_through_gate(
        self,
        mode: str,
        payload: str,
        *,
        approval_granted: bool = False,
        replay_mode: bool = False,
        chat_user_text: str | None = None,
        ingest_user_message: str | None = None,
        client_requires_clarification: bool = False,
    ) -> dict:
        """Önce run_lumos_gate; yürütme yalnızca lumos_gate_execute ile (tek kapı)."""
        from kando.file_patch_executor import run as direct_run
        from kando_runtime.lumos_audit import LumosAuditCollector
        from kando_runtime.lumos_gate import lumos_gate_execute, run_lumos_gate

        audit = LumosAuditCollector()
        gate_result = run_lumos_gate(
            mode,
            payload,
            repo_root=ROOT,
            maybe_agent_auto=_maybe_agent_auto_patch,
            parse_agent_file_action=_parse_agent_file_action,
            approval_granted=approval_granted,
            audit=audit,
            replay_mode=replay_mode,
            chat_user_text=chat_user_text,
            ingest_user_message=ingest_user_message,
            client_requires_clarification=client_requires_clarification,
        )
        if gate_result.get("_kind") != "run":
            return gate_result

        def _run_direct(instr: str) -> dict:
            return direct_run({"instruction": instr, "execution_mode": "task"})

        def _start_agent(goal: str, auto: bool) -> str:
            return start_agent_job(goal, auto, repo_root=ROOT, outbox_dir=OUTBOX_DIR)

        return lumos_gate_execute(
            gate_result,
            run_direct=_run_direct,
            start_agent=_start_agent,
            run_agent_auto=_maybe_agent_auto_patch,
        )

    def _send_lumos_pipeline_out(self, out: dict, *, approval_path: Path | None = None) -> None:
        """Gate çıktısı: policy → pending → blocked → deny → outbox (onay dosyası isteğe bağlı silinir)."""
        try:
            from kando_runtime.lumos_audit import append_audit_log

            ent = out.get("lumos_audit_log")
            if isinstance(ent, dict):
                append_audit_log(ROOT, ent)
        except Exception:
            pass
        if out.get("policy_ok") is False:
            self._send_json(
                int(out.get("http_status") or 403),
                {"accepted": False, "error": "blocked by lumos"},
            )
            return

        if out.get("execution_mode") == "pending_approval":
            self._attach_pending_approval_to_out(out)
            attach_execution_dispatch_to_out(out, repo_root=ROOT)
            ps = ""
            pr = out.get("pending_approval_record")
            if isinstance(pr, dict):
                ps = str(pr.get("pending_summary") or "")
            hb = out.get("http_body")
            clar = (
                isinstance(pr, dict) and pr.get("requires_clarification") is True
            ) or (isinstance(hb, dict) and hb.get("requires_clarification") is True)
            dispatch_med = _is_dispatch_medium_pending(out)
            msg = (
                "Lumos: görev net değil; onay veya netleştirme bekleniyor"
                if clar
                else (
                    "Lumos: orta riskli sistem yürütmesi, kullanıcı onayı bekleniyor"
                    if dispatch_med
                    else "Lumos: yüksek riskli işlem, kullanıcı onayı bekleniyor"
                )
            )
            hb_pending = out.get("http_body") if isinstance(out.get("http_body"), dict) else {}
            dk_pending = str(hb_pending.get("decision_kind") or "").strip().lower()
            if dk_pending not in ("blocked", "unclear", "proceed", "conflict"):
                dk_pending = "unclear" if clar else "blocked"
            resp_body: dict = {
                "accepted": True,
                "requires_approval": True,
                "error": "",
                "message": msg,
                "decision_kind": dk_pending,
                "lumos_gate": out,
                "approval_file": out.get("approval_file") or "",
                "approval_token": out.get("approval_token") or "",
                "pending_summary": ps,
                "task_type": hb_pending.get("task_type"),
                "dispatch_execution_plan": hb_pending.get("dispatch_execution_plan"),
                "execution_dispatch": hb_pending.get("execution_dispatch"),
                "system_execution": hb_pending.get("system_execution"),
            }
            if clar:
                resp_body["requires_clarification"] = True
            self._send_json(200, resp_body)
            return
        if out.get("execution_mode") == "blocked":
            self._send_json(
                200,
                {
                    "accepted": False,
                    "error": "Lumos: işlem güvenlik nedeniyle engellendi",
                    "lumos_gate": out,
                },
            )
            return
        if out.get("final_decision") == "deny":
            self._send_json(
                200,
                {
                    "accepted": False,
                    "error": "Lumos: işlem güvenlik nedeniyle engellendi",
                    "lumos_gate": out,
                },
            )
            return

        st = int(out.get("http_status") or 200)
        if approval_path is not None and st == 200:
            try:
                approval_path.unlink()
            except OSError:
                pass

        self._finish_out_after_gate(out)

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
        if obj.get("auto_approve_safe") is not None:
            _persist_direct_patch_meta(obj)
        out = self._complete_through_gate(
            "agent",
            goal.strip(),
            approval_granted=False,
            ingest_user_message=goal.strip(),
        )
        self._send_lumos_pipeline_out(out, approval_path=None)

    def _handle_chat(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            Path("logs").mkdir(exist_ok=True)
            with open("logs/bridge.log", "ab") as f:
                f.write(b"\n--- CHAT ---\n")
                f.write(raw)
                f.write(b"\n")
        except OSError:
            pass
        try:
            dec = raw.decode("utf-8")
            body = json.loads(dec)
        except UnicodeDecodeError:
            self._reject(400, "body utf-8 değil")
            return
        except json.JSONDecodeError as e:
            self._reject(400, f"json: {e}")
            return
        if not isinstance(body, dict):
            self._reject(400, "json nesne olmalı")
            return
        message = str(body.get("message", "")).strip()
        if not message:
            self._send_json(
                200,
                {"accepted": False, "error": "message string gerekli"},
            )
            return
        hist = body.get("history")
        if hist is not None and not isinstance(hist, list):
            hist = None

        if classify_bridge_message_intent(message) == "task":
            try:
                from core.user_intent_classifier import classify_user_message_intent
                # run_task / extract_task: src/core/simple_chat_task.py (repo köküne göre)
                from core.simple_chat_task import extract_task, run_task

                _ui = classify_user_message_intent(message)
                if _ui.label == "TASK":
                    _ext = extract_task(message)
                    if _ext:
                        try:
                            _result = run_task(_ext, repo_root=ROOT)
                        except (ValueError, OSError) as _e:
                            self._send_json(
                                200,
                                {
                                    "reply": f"Görev başarısız: {_e}",
                                    "mode": "task",
                                    "blocked": True,
                                },
                            )
                            return
                        self._send_json(
                            200,
                            {"reply": _result, "mode": "task"},
                        )
                        return
            except ImportError:
                pass

            _clear_direct_patch_meta()
            file_ref = extract_chat_task_file_ref(message)
            if file_ref:
                task_obj: dict = {
                    "file": file_ref,
                    "task": message,
                    "title": message,
                    "raw_text": message,
                    "goal": message,
                    "source": "chat_auto",
                }
            else:
                task_obj = {
                    "goal": message,
                    "title": message,
                    "raw_text": message,
                    "source": "chat_auto",
                }
            if is_high_risk(message):
                task_obj["risk"] = "high"
                task_obj["requires_approval"] = True
            raw_task = json.dumps(task_obj, ensure_ascii=False).encode("utf-8")
            err, mode, payload, _um = _resolve_task_routing("application/json", raw_task)
            if err or mode is None or payload is None:
                self._send_json(
                    200,
                    {
                        "reply": "Task olarak işlenemedi",
                        "mode": "task_routed",
                        "blocked": False,
                        "task_result": {"routing_error": err or "bilinmeyen yönlendirme"},
                    },
                )
                return
            surf_chat = _task_surface_for_destructive_scan(
                mode, payload, message.strip()
            )
            d_block, d_code = destructive_surface_blocks_task(surf_chat)
            if d_block:
                self._send_json(
                    200,
                    {
                        "reply": destructive_command_user_message_tr(),
                        "mode": "task_routed",
                        "blocked": True,
                        "task_result": {
                            "accepted": False,
                            "destructive_command": True,
                            "destructive_code": d_code or "",
                        },
                    },
                )
                return
            out = self._complete_through_gate(
                mode,
                payload,
                approval_granted=False,
                chat_user_text=message,
                ingest_user_message=message.strip(),
            )
            try:
                from kando_runtime.lumos_audit import append_audit_log

                ent = out.get("lumos_audit_log")
                if isinstance(ent, dict):
                    append_audit_log(ROOT, ent)
            except Exception:
                pass
            self._attach_pending_approval_to_out(out)
            attach_execution_dispatch_to_out(out, repo_root=ROOT)
            if _is_dispatch_medium_pending(out):
                persist_last_result_from_out(out)
                merge_execution_enrichment_into_out(out, ROOT)
                self._send_json(
                    200,
                    {
                        "reply": "Orta riskli dosya veya komut onayı bekleniyor",
                        "mode": "task_routed",
                        "blocked": False,
                        "requires_approval": True,
                        "approval_file": out.get("approval_file"),
                        "approval_token": out.get("approval_token"),
                        "task_result": task_pipeline_result_for_chat(out),
                    },
                )
                return
            persist_last_result_from_out(out)
            merge_execution_enrichment_into_out(out, ROOT)
            self._send_json(
                200,
                {
                    "reply": "Task olarak işlendi",
                    "mode": "task_routed",
                    "blocked": False,
                    "task_result": task_pipeline_result_for_chat(out),
                },
            )
            return

        try:
            chat_out = build_chat_reply(message, hist)
            try:
                from kando_runtime.lumos_audit import append_chat_turn_telemetry

                append_chat_turn_telemetry(
                    ROOT,
                    user_message=message,
                    intent=str(chat_out.get("intent") or ""),
                    reply=str(chat_out.get("reply") or ""),
                    model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
                    blocked=bool(chat_out.get("blocked")),
                )
            except Exception:
                pass
            pub = {k: v for k, v in chat_out.items() if k != "intent"}
            self._send_json(200, pub)
        except Exception as e:
            self._send_json(
                200,
                {"accepted": False, "error": f"chat llm error: {e}"},
            )

    def _finish_out_after_gate(self, out: dict) -> None:
        body = out.get("http_body") or {}
        st = int(out.get("http_status") or 200)
        if st != 200:
            self._send_json(
                st,
                body if isinstance(body, dict) else {"error": str(body)},
            )
            return

        attach_execution_dispatch_to_out(out, repo_root=ROOT)
        if _is_dispatch_medium_pending(out):
            persist_last_result_from_out(out)
            merge_execution_enrichment_into_out(out, ROOT)
            self._send_medium_dispatch_pending_http_response(out)
            return

        persist_last_result_from_out(out)
        merge_execution_enrichment_into_out(out, ROOT)

        resp = dict(body) if isinstance(body, dict) else {}
        aud = out.get("lumos_audit_log")
        if isinstance(aud, dict) and aud.get("log_id"):
            resp["log_id"] = aud["log_id"]
        if resp.get("mode") == "direct_patch" and "result_path" not in resp:
            resp["result_path"] = str(LAST_RESULT_FILE.resolve())
        if resp.get("mode") == "lumos_plan" and "result_path" not in resp:
            if any(
                s.get("type") == "patch"
                for s in (resp.get("step_results") or [])
                if isinstance(s, dict)
            ):
                resp["result_path"] = str(LAST_RESULT_FILE.resolve())
        self._send_json(200, resp)

    def _handle_replay(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            dec = raw.decode("utf-8")
            obj = json.loads(dec)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._reject(400, "json gerekli")
            return
        if not isinstance(obj, dict):
            self._reject(400, "json nesne olmalı")
            return
        log_id = obj.get("log_id")
        if not isinstance(log_id, str) or not log_id.strip():
            self._reject(400, "log_id string gerekli")
            return
        mode = str(obj.get("mode") or "dry_run")
        if mode != "dry_run":
            self._reject(400, "mode yalnızca dry_run desteklenir")
            return
        from kando_runtime.lumos_audit import find_audit_entry
        from kando_runtime.lumos_gate import replay_lumos_task

        entry = find_audit_entry(ROOT, log_id.strip())
        if entry is None:
            self._send_json(404, {"error": "log_id bulunamadı", "log_id": log_id.strip()})
            return
        res = replay_lumos_task(
            entry,
            repo_root=ROOT,
            maybe_agent_auto=_maybe_agent_auto_patch,
            parse_agent_file_action=_parse_agent_file_action,
        )
        self._send_json(200, res)

    def _handle_approve(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            Path("logs").mkdir(parents=True, exist_ok=True)
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
        rel = obj.get("approval_file")
        if not isinstance(rel, str) or not rel.strip():
            self._reject(400, "approval_file string gerekli")
            return
        if not isinstance(obj.get("approved"), bool):
            self._reject(400, "approved boolean gerekli")
            return
        approved = bool(obj["approved"])

        path = _safe_pending_approval_path(ROOT, rel.strip())
        if path is None:
            self._reject(400, "geçersiz veya bulunamayan approval_file")
            return

        token_in = obj.get("approval_token")
        if not isinstance(token_in, str) or not token_in.strip():
            self._send_json(200, {"accepted": False, "error": "token gerekli"})
            return

        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self._reject(400, "onay dosyası okunamadı")
            return

        loaded.pop("approval_granted", None)
        nt = loaded.get("normalized_task")
        if isinstance(nt, dict):
            nt.pop("approval_granted", None)

        if token_in.strip() != str(loaded.get("approval_token") or ""):
            self._send_json(200, {"accepted": False, "error": "geçersiz token"})
            return
        if loaded.get("used"):
            self._send_json(200, {"accepted": False, "error": "zaten kullanıldı"})
            return

        if not approved:
            try:
                path.unlink()
            except OSError:
                pass
            self._send_json(
                200,
                {"accepted": True, "closed": True, "applied": False},
            )
            return

        if str(loaded.get("schema_version") or "") == DISPATCH_PENDING_APPROVAL_SCHEMA:
            from kando_runtime.task_dispatch import (
                execute_approved_dispatch_pending,
                validate_dispatch_pending_for_approval,
            )

            try:
                validate_dispatch_pending_for_approval(loaded)
            except ValueError as e:
                self._send_json(200, {"accepted": False, "error": str(e)})
                return

            try:
                path.unlink()
            except OSError:
                self._send_json(
                    200,
                    {"accepted": False, "error": "onay dosyası silinemedi"},
                )
                return

            try:
                disp = execute_approved_dispatch_pending(loaded, repo_root=ROOT)
            except Exception as e:
                self._send_json(200, {"accepted": False, "error": str(e)})
                return

            snap = loaded.get("gate_http_body_snapshot")
            hb_resp = dict(snap) if isinstance(snap, dict) else {}
            hb_resp["task_type"] = disp["task_type"]
            hb_resp["dispatch_execution_plan"] = disp["dispatch_execution_plan"]
            hb_resp["execution_dispatch"] = disp["execution_dispatch"]
            if "system_execution" in disp:
                hb_resp["system_execution"] = disp["system_execution"]

            resp = dict(hb_resp)
            resp["accepted"] = True
            resp["applied"] = True
            self._send_json(200, resp)
            return

        from kando_runtime.lumos_gate import validate_pending_for_approval

        try:
            validate_pending_for_approval(loaded)
        except ValueError as e:
            self._send_json(200, {"accepted": False, "error": str(e)})
            return

        try:
            path.unlink()
        except OSError:
            self._send_json(
                200,
                {"accepted": False, "error": "onay dosyası silinemedi"},
            )
            return

        from kando.file_patch_executor import run as direct_run
        from kando_runtime.lumos_audit import LumosAuditCollector
        from kando_runtime.lumos_gate import execute_approved_pending_record

        mode = str(loaded.get("mode") or "")
        payload = str(loaded.get("original_payload") or "")
        plan_dbg = loaded.get("execution_plan")
        try:
            _stderr_write(
                "APPROVE FLOW: "
                + json.dumps(
                    {"mode": mode, "payload_len": len(payload), "execution_plan": plan_dbg},
                    ensure_ascii=False,
                )[:4000]
            )
        except Exception:
            _stderr_write("APPROVE FLOW: (log failed)")

        _stderr_write("APPROVED → EXECUTION STARTED\n")

        def _run_direct(instr: str) -> dict:
            return direct_run({"instruction": instr, "execution_mode": "task"})

        def _start_agent(goal: str, auto: bool) -> str:
            return start_agent_job(goal, auto, repo_root=ROOT, outbox_dir=OUTBOX_DIR)

        audit = LumosAuditCollector()
        try:
            out = execute_approved_pending_record(
                loaded,
                run_direct=_run_direct,
                start_agent=_start_agent,
                run_agent_auto=_maybe_agent_auto_patch,
                repo_root=ROOT,
                audit=audit,
            )
        except ValueError as e:
            self._send_json(200, {"accepted": False, "error": str(e)})
            return

        self._send_lumos_pipeline_out(out, approval_path=None)

    def _cors(self):
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Headers", "*")
    self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

def do_OPTIONS(self):
    self.send_response(200)
    self._cors()
    self.end_headers()

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
        if req_path == "/approve":
            self._handle_approve()
            return
        if req_path == "/replay":
            self._handle_replay()
            return
        if req_path == "/chat":
            self._handle_chat()
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

        raw = _inject_task_obj_title_fields(self.headers.get("Content-Type"), raw)
        req_clar = _raw_json_requires_clarification(raw)
        err, mode, payload, umsg = _resolve_task_routing(
            self.headers.get("Content-Type"), raw
        )
        if err:
            self._reject(400, err)
            return
        assert mode is not None and payload is not None

        ingest = (umsg or "").strip() or None
        surf = _task_surface_for_destructive_scan(mode, payload, ingest)
        d_block, d_code = destructive_surface_blocks_task(surf)
        if d_block:
            self._send_json(
                200,
                {
                    "accepted": False,
                    "error": destructive_command_user_message_tr(),
                    "destructive_command": True,
                    "destructive_code": d_code or "",
                },
            )
            return
        try:
            from core.video_prompt_clarity import (
                is_video_task_prompt_ambiguous,
                video_prompt_clarification_question_tr,
            )

            vf = _video_task_prompt_fields_for_clarity(raw)
            if vf is not None:
                vprompt, vref = vf
                if vprompt and is_video_task_prompt_ambiguous(
                    vprompt, has_media_ref=vref
                ):
                    self._send_json(
                        200,
                        {
                            "accepted": False,
                            "video_prompt_clarification": True,
                            "reply": video_prompt_clarification_question_tr(vprompt),
                            "mode": "clarify_video_prompt",
                        },
                    )
                    return
        except Exception:
            pass
        client_tt = _raw_json_task_type(raw)
        out = self._complete_through_gate(
            mode,
            payload,
            approval_granted=False,
            ingest_user_message=ingest,
            client_requires_clarification=req_clar,
        )
        if client_tt:
            out["_client_task_type"] = client_tt
        self._send_lumos_pipeline_out(out, approval_path=None)


def main() -> None:
    global _bridge_public_bind
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", os.environ.get("KANDO_BRIDGE_PORT", "8765")))
    _bridge_public_bind = True
    httpd = ThreadingHTTPServer((host, port), BridgeHandler)
    print(
        f"kando_bridge_server: http://{host}:{port}/task | /chat | /approve (POST)",
        flush=True,
    )
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
