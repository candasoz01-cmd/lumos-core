"""
Minimal direct patch executor.
- TARGET: <file>\n<body>
- TARGETS: <file1,file2>\n<body>
- INSERT_AT_TOP:
- INSERT_AT_BOTTOM:
- APPEND_AFTER:
- REPLACE:
- ROLLBACK
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


def lumos_base_dir() -> Path:
    lb = os.environ.get("LUMOS_BASE_DIR", ".lumos")
    p = Path(lb)
    return p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()


def _parse_command_json_loose(raw: str) -> dict[str, Any] | None:
    if '"instruction"' not in raw or '"execution_mode"' not in raw:
        return None
    try:
        start = raw.index('"instruction"')
        colon = raw.index(":", start)
        q0 = raw.index('"', colon + 1)
        key = '","execution_mode"'
        end = raw.index(key, q0 + 1)
        inner = raw[q0 + 1:end]
    except ValueError:
        return None

    instruction = inner.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not instruction:
        return None

    mode = "task"
    m = re.search(r'"execution_mode"\s*:\s*"([^"]*)"', raw[end:])
    if m:
        mode = m.group(1).strip() or "task"

    return {"instruction": instruction, "execution_mode": mode}


def read_command_json(path: Path | None = None) -> dict[str, Any] | None:
    if path is None:
        path = lumos_base_dir() / "cursor_bridge" / "command.json"
    if not path.is_file():
        return None

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    data: dict[str, Any] | None = None
    try:
        parsed = json.loads(text)
        data = parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        data = _parse_command_json_loose(text)

    if not isinstance(data, dict):
        return None

    instruction = str(data.get("instruction") or "").strip()
    if not instruction:
        return None

    mode = str(data.get("execution_mode") or "task").strip() or "task"
    return {"instruction": instruction, "execution_mode": mode}


def goal_for_bridge(argv: list[str], *, default: str = "genel analiz") -> str:
    cmd = read_command_json()
    if cmd:
        return str(cmd["instruction"])
    tail = argv[1:] if len(argv) > 1 else []
    g = " ".join(tail).strip()
    return g or default


def _normalize_instruction(instr: str) -> str:
    i = instr.strip()
    if "add a comment line" in i or "insert" in i:
        m = re.search(r"#\s*([A-Za-z0-9_]+)", i)
        if m and "runtime_state.py" in i:
            txt = m.group(0)
            return f"TARGET:src/core/runtime_state.py\n# {txt[1:].strip()}\n"
    return instr


def _backup_path(fp: Path) -> Path:
    return fp.with_name(fp.name + ".bak")


def _backup_file(fp: Path) -> Path:
    bak = _backup_path(fp)
    bak.write_text(fp.read_text(encoding="utf-8"), encoding="utf-8")
    return bak


def _rollback_file(fp: Path) -> dict[str, Any]:
    bak = _backup_path(fp)
    if not bak.exists():
        return {
            "execution_result": "rollback_failed",
            "error_type": "backup_missing",
            "detail": f"backup yok: {bak.name}",
        }
    fp.write_text(bak.read_text(encoding="utf-8"), encoding="utf-8")
    return {
        "execution_result": "rollback_applied",
        "error_type": "",
        "detail": f"rollback uygulandi: {fp.name}",
        "applied_path": str(fp),
    }


def _safe_write(fp: Path, old_text: str, new_text: str, rel: str) -> dict[str, Any]:
    if not isinstance(new_text, str):
        return {
            "execution_result": "patch_failed",
            "error_type": "invalid_new_text",
            "detail": "çıktı string değil",
        }

    if new_text == old_text:
        return {
            "execution_result": "no_change",
            "detail": "değişiklik yok",
            "applied_path": rel,
            "error_type": "",
            "retry_count": 0,
        }

    _backup_file(fp)
    fp.write_text(new_text, encoding="utf-8")
    return {
        "execution_result": "patch_applied",
        "detail": "direct executor applied",
        "applied_path": rel,
        "error_type": "",
        "retry_count": 0,
    }


def _parse_target_instruction(instruction: str) -> tuple[str, str] | None:
    m = re.match(r"(?s)^TARGET:\s*([^\n]+)\n(.*)$", instruction)
    if not m:
        return None
    rel = m.group(1).strip().replace("\\", "/")
    body = m.group(2)
    if not rel:
        return None
    return rel, body


def _apply_single(rel: str, body: str) -> dict[str, Any]:
    root = Path.cwd().resolve()
    fp = (root / rel).resolve()

    try:
        fp.relative_to(root)
    except Exception:
        return {
            "execution_result": "patch_failed",
            "error_type": "path_outside_repo",
            "detail": f"repo dışı yol: {rel}",
        }

    if not fp.exists():
        return {
            "execution_result": "patch_failed",
            "error_type": "file_not_found",
            "detail": f"dosya yok: {rel}",
        }

    if body.lstrip("\n").startswith("ROLLBACK"):
        return _rollback_file(fp)

    old_text = fp.read_text(encoding="utf-8")
    cmd = body.lstrip("\n")
    new_text: str

    if cmd.startswith("INSERT_AT_BOTTOM:"):
        content = cmd[len("INSERT_AT_BOTTOM:"):].lstrip("\n")
        if content.strip() and content.strip() in old_text:
            return {
                "execution_result": "no_change",
                "detail": "değişiklik yok",
                "applied_path": rel,
                "error_type": "",
                "retry_count": 0,
            }
        base = old_text.rstrip("\n")
        new_text = f"{base}\n{content}\n"

    elif cmd.startswith("INSERT_AT_TOP:"):
        content = cmd[len("INSERT_AT_TOP:"):].lstrip("\n")
        new_text = f"{content}\n{old_text.lstrip()}"

    elif cmd.startswith("APPEND_AFTER:"):
        rest = cmd[len("APPEND_AFTER:"):]
        parts = rest.split("\n", 1)
        marker = parts[0].strip()
        content = parts[1] if len(parts) > 1 else ""
        if not marker:
            return {
                "execution_result": "patch_failed",
                "error_type": "missing_marker",
                "detail": "APPEND_AFTER marker boş",
            }
        if marker not in old_text:
            return {
                "execution_result": "patch_failed",
                "error_type": "marker_not_found",
                "detail": f"marker yok: {marker}",
            }
        if content.strip() and content.strip() in old_text:
            return {
                "execution_result": "no_change",
                "detail": "zaten mevcut (append_after)",
                "applied_path": rel,
                "error_type": "",
                "retry_count": 0,
            }
        new_text = old_text.replace(marker, f"{marker}\n{content}", 1)

    elif cmd.startswith("REPLACE:"):
        rest = cmd[len("REPLACE:"):]
        if "\n" not in rest:
            return {
                "execution_result": "patch_failed",
                "error_type": "invalid_replace",
                "detail": "REPLACE için eski ve yeni metin gerekli",
            }
        old_part, new_part = rest.split("\n", 1)
        if old_part not in old_text:
            return {
                "execution_result": "patch_failed",
                "error_type": "replace_old_not_found",
                "detail": "REPLACE eski metni bulunamadı",
            }
        new_text = old_text.replace(old_part, new_part, 1)

    else:
        new_text = cmd

    return _safe_write(fp, old_text, new_text, rel)


def run(payload: dict[str, Any]) -> dict[str, Any]:
    instruction = _normalize_instruction(str(payload.get("instruction") or "")).strip()
    if not instruction:
        return {
            "execution_result": "parse_error",
            "error_type": "missing_instruction",
            "detail": "instruction boş",
        }

    multi = re.match(r"(?s)^TARGETS:\s*([^\n]+)\n(.*)$", instruction)
    if multi:
        rels = [x.strip().replace("\\", "/") for x in multi.group(1).split(",") if x.strip()]
        body = multi.group(2)

        backups: dict[str, str] = {}
        for r in rels:
            fp0 = (Path.cwd().resolve() / r).resolve()
            if fp0.exists():
                backups[r] = fp0.read_text(encoding="utf-8")

        results: list[dict[str, Any]] = []
        for r in rels:
            sub = _apply_single(r, body)
            results.append(sub)
            if sub.get("execution_result") not in ("patch_applied", "no_change"):
                for br, content in backups.items():
                    (Path.cwd().resolve() / br).write_text(content, encoding="utf-8")
                return {
                    "execution_result": "rolled_back",
                    "detail": f"multi rollback ({r} başarısız)",
                    "files": results,
                    "error_type": "atomic_failure",
                    "retry_count": 0,
                }

        return {
            "execution_result": "patch_applied",
            "detail": "multi_atomic_applied",
            "files": results,
            "error_type": "",
            "retry_count": 0,
        }

    parsed = _parse_target_instruction(instruction)
    if not parsed:
        return {
            "execution_result": "parse_error",
            "error_type": "missing_instruction",
            "detail": "TARGET parse edilemedi",
        }

    rel, body = parsed

    if "," in rel:
        rels = [x.strip().replace("\\", "/") for x in rel.split(",") if x.strip()]

        backups: dict[str, str] = {}
        for r in rels:
            fp0 = (Path.cwd().resolve() / r).resolve()
            if fp0.exists():
                backups[r] = fp0.read_text(encoding="utf-8")

        results: list[dict[str, Any]] = []
        for r in rels:
            sub = _apply_single(r, body)
            results.append(sub)
            if sub.get("execution_result") not in ("patch_applied", "no_change"):
                for br, content in backups.items():
                    (Path.cwd().resolve() / br).write_text(content, encoding="utf-8")
                return {
                    "execution_result": "rolled_back",
                    "detail": f"multi rollback ({r} başarısız)",
                    "files": results,
                    "error_type": "atomic_failure",
                    "retry_count": 0,
                }

        return {
            "execution_result": "patch_applied",
            "detail": "multi_atomic_applied",
            "files": results,
            "error_type": "",
            "retry_count": 0,
        }

    return _apply_single(rel, body)
