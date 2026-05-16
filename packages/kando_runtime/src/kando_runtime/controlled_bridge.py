"""
Kontrollü köprü: dar komut yüzeyi, aşamalı izinler.

İlk yetki (file_rw): workspace/ altında güvenli dosya okuma/yazma.
Yasak: terminal/shell, silme, uygulama açma, posta/takvim ve benzeri yüzeyler.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BRIDGE_MODE_CONTROLLED = "controlled"
PERMISSION_FILE_RW = "file_rw"

COMMAND_READ = "read"
COMMAND_WRITE = "write"
COMMAND_PING = "ping"

ALLOWED_PERMISSIONS: frozenset[str] = frozenset({PERMISSION_FILE_RW})
ALLOWED_COMMANDS: frozenset[str] = frozenset(
    {COMMAND_READ, COMMAND_WRITE, COMMAND_PING}
)

MAX_READ_BYTES = 120_000
MAX_WRITE_BYTES = 64_000

# Terminal, silme, uygulama, posta/takvim — kontrollü modda reddedilir.
_BLOCKED_SURFACE_RE = re.compile(
    r"(?:"
    r"\b(?:terminal|shell|bash|zsh|cmd\.exe|powershell)\b|"
    r"\b(?:rm\s+-rf|sudo\s+rm|unlink|kalıcı\s+sil|kalici\s+sil|delete\s+permanently)\b|"
    r"(?:^|\s)rm\s+(?:-[^\s]+\s+)*|"
    r"\b(?:sil|delete|remove|trash|çöp|cop)\b|"
    r"\b(?:open\s+app|launch\s+app|uygulama\s+aç|uygulama\s+ac|open\s+-a)\b|"
    r"\b(?:mail|e-?posta|eposta|calendar|takvim|ical|outlook|gmail)\b"
    r")",
    re.I | re.M,
)

_DELETE_VERB_RE = re.compile(
    r"\b(?:sil|delete|remove|unlink|trash|kalıcı\s+sil|kalici\s+sil)\b",
    re.I,
)


@dataclass(frozen=True)
class ControlledRequest:
    permission: str
    command: str
    path: str
    content: str | None


def workspace_dir(repo_root: Path) -> Path:
    d = (repo_root / "workspace").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_workspace_path(repo_root: Path, rel: str) -> Path | None:
    rel = (rel or "").strip().replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        return None
    ws = workspace_dir(repo_root)
    target = (ws / rel).resolve()
    try:
        target.relative_to(ws)
    except ValueError:
        return None
    return target


def surface_blocked(text: str) -> bool:
    return bool(_BLOCKED_SURFACE_RE.search(text or ""))


def validate_controlled_body(body: dict[str, Any]) -> tuple[ControlledRequest | None, str | None]:
    if not isinstance(body, dict):
        return None, "invalid_body"
    permission = str(body.get("permission") or "").strip()
    if permission not in ALLOWED_PERMISSIONS:
        return None, "permission_denied"
    command = str(body.get("command") or "").strip().lower()
    if command not in ALLOWED_COMMANDS:
        return None, "command_not_allowed"
    path = str(body.get("path") or "").strip()
    content = body.get("content")
    content_str: str | None = None
    if content is not None:
        if not isinstance(content, str):
            return None, "invalid_content"
        content_str = content

    probe = " ".join(
        x
        for x in (
            permission,
            command,
            path,
            content_str or "",
            str(body.get("task") or ""),
            str(body.get("text") or ""),
        )
        if x
    )
    if surface_blocked(probe):
        return None, "surface_blocked"

    if command == COMMAND_PING:
        return (
            ControlledRequest(
                permission=permission,
                command=command,
                path="",
                content=None,
            ),
            None,
        )

    if not path:
        return None, "path_required"
    if _DELETE_VERB_RE.search(path):
        return None, "delete_not_allowed"

    if command == COMMAND_WRITE:
        if content_str is None:
            return None, "content_required"
        if len(content_str.encode("utf-8")) > MAX_WRITE_BYTES:
            return None, "content_too_large"

    return (
        ControlledRequest(
            permission=permission,
            command=command,
            path=path,
            content=content_str,
        ),
        None,
    )


def execute_controlled(repo_root: Path, body: dict[str, Any]) -> dict[str, Any]:
    req, err = validate_controlled_body(body)
    if req is None:
        return {
            "ok": False,
            "error": err or "rejected",
            "bridge_mode": BRIDGE_MODE_CONTROLLED,
        }

    if req.command == COMMAND_PING:
        return {
            "ok": True,
            "bridge_mode": BRIDGE_MODE_CONTROLLED,
            "permission": req.permission,
            "command": req.command,
            "allowed_commands": sorted(ALLOWED_COMMANDS),
            "sandbox": "workspace/",
        }

    target = resolve_workspace_path(repo_root, req.path)
    if target is None:
        return {
            "ok": False,
            "error": "path_outside_sandbox",
            "bridge_mode": BRIDGE_MODE_CONTROLLED,
        }

    if req.command == COMMAND_READ:
        if not target.is_file():
            return {
                "ok": False,
                "error": "file_not_found",
                "path": req.path,
                "bridge_mode": BRIDGE_MODE_CONTROLLED,
            }
        try:
            data = target.read_bytes()
        except OSError as e:
            return {
                "ok": False,
                "error": "read_failed",
                "detail": str(e),
                "bridge_mode": BRIDGE_MODE_CONTROLLED,
            }
        truncated = len(data) > MAX_READ_BYTES
        if truncated:
            data = data[:MAX_READ_BYTES]
        return {
            "ok": True,
            "bridge_mode": BRIDGE_MODE_CONTROLLED,
            "permission": req.permission,
            "command": COMMAND_READ,
            "path": req.path,
            "content": data.decode("utf-8", errors="replace"),
            "truncated": truncated,
            "bytes": len(data),
        }

    if req.command == COMMAND_WRITE:
        assert req.content is not None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(req.content, encoding="utf-8")
        except OSError as e:
            return {
                "ok": False,
                "error": "write_failed",
                "detail": str(e),
                "bridge_mode": BRIDGE_MODE_CONTROLLED,
            }
        return {
            "ok": True,
            "bridge_mode": BRIDGE_MODE_CONTROLLED,
            "permission": req.permission,
            "command": COMMAND_WRITE,
            "path": req.path,
            "bytes": len(req.content.encode("utf-8")),
        }

    return {"ok": False, "error": "command_not_allowed"}


def policy_allows_normalized(norm: dict[str, Any]) -> tuple[bool, str]:
    """
    Lumos gate policy_check için: kontrollü modda yalnızca workspace direct_patch.
    """
    if norm.get("bridge_mode") != BRIDGE_MODE_CONTROLLED:
        return True, ""
    perm = str(norm.get("controlled_permission") or PERMISSION_FILE_RW).strip()
    if perm not in ALLOWED_PERMISSIONS:
        return False, "permission_denied"

    mode = str(norm.get("mode") or "").strip().lower()
    if mode == "agent":
        return False, "agent_not_allowed_in_controlled_mode"

    task_type = str(norm.get("task_type") or "").strip().lower()
    if task_type in ("shell", "video", "image", "audio"):
        return False, f"task_type_{task_type}_not_allowed"

    combined = " ".join(
        str(norm.get(k) or "")
        for k in (
            "target_body",
            "agent_blob",
            "ingest_raw_text",
            "normalized_task",
        )
    )
    if surface_blocked(combined):
        return False, "surface_blocked"
    if _DELETE_VERB_RE.search(combined):
        return False, "delete_not_allowed"

    rel = str(norm.get("target_rel") or "").strip().replace("\\", "/")
    if rel:
        if ".." in rel.split("/"):
            return False, "path_traversal"
        if not rel.startswith("workspace/"):
            ws_rel = rel.lstrip("/")
            if ws_rel and not ws_rel.startswith("workspace/"):
                return False, "path_must_be_under_workspace"

    return True, ""
