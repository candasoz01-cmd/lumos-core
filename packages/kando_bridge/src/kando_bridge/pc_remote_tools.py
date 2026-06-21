"""
Lumos PC remote-control bridge — demo-safe tool schemas and stub executor.

Gerçek OS otomasyonu yok; yalnızca structured stub yanıtları ve onay kapısı.
Private katman: execute_tool_stub → gerçek executor swap noktası.
"""
from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from kando_bridge.pending_approvals import (
    approve_pending_record,
    build_pc_remote_pending_record,
    find_pending_by_token,
    mark_expired_if_needed,
    reject_pending_record,
    try_consume_approval_token,
    validate_approval_token,
    write_pending_approval,
)

SCHEMA_VERSION = "lumos.pc_remote_tools.v1"

# --- Komut kimlikleri (OpenAI function name = bridge command) ---

CMD_OPEN_APP = "pc_open_app"
CMD_OPEN_URL = "pc_open_url"
CMD_READ_SCREEN = "pc_read_screen_state"
CMD_TYPE_TEXT = "pc_type_text"
CMD_SUGGEST_CLICK = "pc_suggest_click"
CMD_REQUEST_FILE_PICKER = "pc_request_file_picker"
CMD_REQUEST_USER_APPROVAL = "pc_request_user_approval"

ALL_COMMANDS: frozenset[str] = frozenset({
    CMD_OPEN_APP,
    CMD_OPEN_URL,
    CMD_READ_SCREEN,
    CMD_TYPE_TEXT,
    CMD_SUGGEST_CLICK,
    CMD_REQUEST_FILE_PICKER,
    CMD_REQUEST_USER_APPROVAL,
})

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_META = "meta"

# confirmation_policy action_key hedefleri (stub fazında kayıt amaçlı)
_REQUIRED_USER_ACTION: dict[str, str] = {
    CMD_OPEN_APP: "Uygulamayı açmayı onaylayın / Approve opening the application",
    CMD_OPEN_URL: "URL açmayı onaylayın / Approve opening the URL",
    CMD_TYPE_TEXT: "Metin yazmayı onaylayın / Approve typing text",
    CMD_SUGGEST_CLICK: "Tıklama önerisini onaylayın / Approve click suggestion",
    CMD_REQUEST_FILE_PICKER: (
        "Dosya seçiciyi onaylayın / Approve file picker request"
    ),
}

_ACTION_KEY_BY_COMMAND: dict[str, str | None] = {
    CMD_OPEN_APP: "bridge_high_risk_execute",
    CMD_OPEN_URL: "bridge_medium_dispatch",
    CMD_READ_SCREEN: None,
    CMD_TYPE_TEXT: "cu_act_type",
    CMD_SUGGEST_CLICK: "cu_act_click",
    CMD_REQUEST_FILE_PICKER: "cu_act_file_send",
    CMD_REQUEST_USER_APPROVAL: None,
}


class CommandSpec(TypedDict):
    command: str
    description_tr: str
    risk_tier: str
    approval_required: bool
    stub_only: bool


COMMAND_SPECS: dict[str, CommandSpec] = {
    CMD_OPEN_APP: {
        "command": CMD_OPEN_APP,
        "description_tr": "Uygulama aç",
        "risk_tier": RISK_HIGH,
        "approval_required": True,
        "stub_only": True,
    },
    CMD_OPEN_URL: {
        "command": CMD_OPEN_URL,
        "description_tr": "URL aç",
        "risk_tier": RISK_MEDIUM,
        "approval_required": True,
        "stub_only": True,
    },
    CMD_READ_SCREEN: {
        "command": CMD_READ_SCREEN,
        "description_tr": "Ekrandaki durumu oku",
        "risk_tier": RISK_LOW,
        "approval_required": False,
        "stub_only": True,
    },
    CMD_TYPE_TEXT: {
        "command": CMD_TYPE_TEXT,
        "description_tr": "Metin yaz",
        "risk_tier": RISK_HIGH,
        "approval_required": True,
        "stub_only": True,
    },
    CMD_SUGGEST_CLICK: {
        "command": CMD_SUGGEST_CLICK,
        "description_tr": "Tıklama öner (otomatik tıklama yok)",
        "risk_tier": RISK_MEDIUM,
        "approval_required": True,
        "stub_only": True,
    },
    CMD_REQUEST_FILE_PICKER: {
        "command": CMD_REQUEST_FILE_PICKER,
        "description_tr": "Dosya seçme isteği oluştur",
        "risk_tier": RISK_MEDIUM,
        "approval_required": True,
        "stub_only": True,
    },
    CMD_REQUEST_USER_APPROVAL: {
        "command": CMD_REQUEST_USER_APPROVAL,
        "description_tr": "Kullanıcı onayı iste",
        "risk_tier": RISK_META,
        "approval_required": False,
        "stub_only": True,
    },
}

# Destructive / never-auto yüzey — controlled_bridge ile uyumlu
_BLOCKED_SURFACE_RE = re.compile(
    r"(?:"
    r"\b(?:terminal|shell|bash|zsh|cmd\.exe|powershell)\b|"
    r"\b(?:rm\s+-rf|sudo\s+rm|unlink|kalıcı\s+sil|kalici\s+sil|delete\s+permanently)\b|"
    r"\b(?:sil|delete|remove|trash|çöp|cop)\b"
    r")",
    re.I | re.M,
)

_URL_RE = re.compile(r"^https?://", re.I)


@dataclass(frozen=True)
class ApprovalGateResult:
    allowed: bool
    approval_required: bool
    reason: str = ""
    pending_token: str = ""


def openai_tool_definitions() -> list[dict[str, Any]]:
    """OpenAI Responses API `tools` dizisi için function tanımları."""
    return [
        {
            "type": "function",
            "name": CMD_OPEN_APP,
            "description": (
                "Belirtilen uygulamayı açmayı köprüye iletir. "
                "Stub fazında yalnızca simülasyon; gerçek açma onay sonrası private katmanda."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Uygulama adı veya bundle id",
                    },
                },
                "required": ["app_name"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": CMD_OPEN_URL,
            "description": "URL açmayı köprüye iletir (onay gerekli, stub simülasyon).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "https:// ile başlayan URL"},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": CMD_READ_SCREEN,
            "description": "Ekran durumunu okur (stub: demo snapshot, onay gerekmez).",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["active_window", "full_screen"],
                        "description": "Okuma kapsamı",
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": CMD_TYPE_TEXT,
            "description": "Metin yazmayı köprüye iletir (onay gerekli, stub yankı).",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Yazılacak metin"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": CMD_SUGGEST_CLICK,
            "description": (
                "Tıklama koordinatı önerir; otomatik tıklama yapmaz. "
                "Onay sonrası bile stub fazında yalnızca öneri döner."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target_description": {
                        "type": "string",
                        "description": "Tıklanacak UI öğesinin açıklaması",
                    },
                    "x": {"type": "number", "description": "Önerilen X (piksel)"},
                    "y": {"type": "number", "description": "Önerilen Y (piksel)"},
                },
                "required": ["target_description"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": CMD_REQUEST_FILE_PICKER,
            "description": "Dosya seçici isteği oluşturur (onay gerekli, stub token).",
            "parameters": {
                "type": "object",
                "properties": {
                    "purpose": {
                        "type": "string",
                        "description": "Dosya seçim amacı (ör. ekle, yükle)",
                    },
                    "accept": {
                        "type": "string",
                        "description": "MIME veya uzantı filtresi",
                    },
                },
                "required": ["purpose"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": CMD_REQUEST_USER_APPROVAL,
            "description": "Genel kullanıcı onayı kaydı oluşturur (meta kapı).",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Onay istenen işlemin özeti",
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
                "required": ["summary"],
                "additionalProperties": False,
            },
        },
    ]


def tools_schema_payload() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "commands": list(COMMAND_SPECS.values()),
        "openai_tools": openai_tool_definitions(),
        "stub_only": True,
        "note": "Gerçek OS otomasyonu private katmanda; OSS yalnızca stub.",
    }


def _probe_blocked(arguments: dict[str, Any]) -> bool:
    blob = " ".join(str(v) for v in arguments.values())
    return bool(_BLOCKED_SURFACE_RE.search(blob))


def validate_command_arguments(command: str, arguments: dict[str, Any]) -> str | None:
    if command not in ALL_COMMANDS:
        return "unknown_command"
    if not isinstance(arguments, dict):
        return "invalid_arguments"
    if _probe_blocked(arguments):
        return "surface_blocked"
    if command == CMD_OPEN_URL:
        url = str(arguments.get("url") or "").strip()
        if not url or not _URL_RE.match(url):
            return "invalid_url"
    if command == CMD_OPEN_APP:
        if not str(arguments.get("app_name") or "").strip():
            return "app_name_required"
    if command == CMD_TYPE_TEXT:
        if not str(arguments.get("text") or "").strip():
            return "text_required"
    if command == CMD_SUGGEST_CLICK:
        if not str(arguments.get("target_description") or "").strip():
            return "target_description_required"
    if command == CMD_REQUEST_FILE_PICKER:
        if not str(arguments.get("purpose") or "").strip():
            return "purpose_required"
    if command == CMD_REQUEST_USER_APPROVAL:
        if not str(arguments.get("summary") or "").strip():
            return "summary_required"
    return None


def check_approval_gate(
    command: str,
    *,
    approval_token: str | None = None,
    approval_id: str | None = None,
    repo_root: Path | None = None,
) -> ApprovalGateResult:
    spec = COMMAND_SPECS.get(command)
    if spec is None:
        return ApprovalGateResult(False, False, reason="unknown_command")
    if not spec["approval_required"]:
        return ApprovalGateResult(True, False)
    if command == CMD_REQUEST_USER_APPROVAL:
        return ApprovalGateResult(True, False)
    tok = (approval_token or "").strip()
    if tok and repo_root is not None:
        aid = (approval_id or "").strip()
        if not aid:
            found = find_pending_by_token(repo_root, tok)
            if found is not None:
                aid = str(found[1].get("approval_id") or found[0].stem)
        if aid:
            ok, reason, _ = validate_approval_token(repo_root, aid, tok)
            if ok:
                return ApprovalGateResult(True, True)
            return ApprovalGateResult(False, True, reason=reason or "invalid_approval_token")
    return ApprovalGateResult(
        False,
        True,
        reason="approval_required",
        pending_token="",
    )


def _attach_pc_remote_confirmation(record: dict[str, Any], repo_root: Path) -> None:
    try:
        from policy.confirmation_policy import attach_bridge_pending_confirmation

        lumos_base = (repo_root / ".lumos").resolve()
        risk = str(record.get("risk_level") or "high")
        attach_bridge_pending_confirmation(
            record,
            base_dir=lumos_base,
            risk=risk,
            source="pc_remote",
        )
    except ImportError:
        return


def _persist_pending_approval(
    command: str,
    arguments: dict[str, Any],
    *,
    repo_root: Path,
    requested_by: str,
    target_device: str,
) -> dict[str, Any]:
    spec = COMMAND_SPECS[command]
    preview = _safe_preview(arguments)
    record = build_pc_remote_pending_record(
        command=command,
        arguments=arguments,
        arguments_preview=preview,
        risk_level=str(spec["risk_tier"]),
        required_user_action=_REQUIRED_USER_ACTION.get(command, "Onay gerekli / Approval required"),
        action_key=_ACTION_KEY_BY_COMMAND.get(command),
        requested_by=requested_by,
        target_device=target_device,
    )
    _attach_pc_remote_confirmation(record, repo_root)
    write_pending_approval(record, repo_root)
    return record


def execute_tool_stub(
    command: str,
    arguments: dict[str, Any],
    *,
    approval_token: str | None = None,
    approval_id: str | None = None,
    repo_root: Path | None = None,
    requested_by: str = "pc_remote_bridge",
    target_device: str = "local",
) -> dict[str, Any]:
    """
    Demo-safe stub yürütme. Gerçek OS API çağrısı yok.
    Private katman: bu fonksiyonun yerine executor swap.
    Onay gerektiren komutlar: diskte `status=approved` + eşleşen token olmadan yürütülmez.
    """
    err = validate_command_arguments(command, arguments)
    if err:
        return {
            "ok": False,
            "status": "rejected",
            "command": command,
            "error": err,
            "schema_version": SCHEMA_VERSION,
        }

    spec = COMMAND_SPECS.get(command)
    if spec is None:
        return {
            "ok": False,
            "status": "rejected",
            "command": command,
            "error": "unknown_command",
            "schema_version": SCHEMA_VERSION,
        }

    if spec["approval_required"] and command != CMD_REQUEST_USER_APPROVAL:
        if repo_root is None:
            return {
                "ok": False,
                "status": "rejected",
                "command": command,
                "error": "repo_root_required",
                "schema_version": SCHEMA_VERSION,
            }
        gate = check_approval_gate(
            command,
            approval_token=approval_token,
            approval_id=approval_id,
            repo_root=repo_root,
        )
        if not gate.allowed:
            if gate.reason == "approval_required":
                record = _persist_pending_approval(
                    command,
                    arguments,
                    repo_root=repo_root,
                    requested_by=requested_by,
                    target_device=target_device,
                )
                return {
                    "ok": False,
                    "status": "pending_approval",
                    "command": command,
                    "approval_required": True,
                    "approval_id": record["approval_id"],
                    "approval_file": record["approval_file"],
                    "approval_token": record["approval_token"],
                    "action_key": record.get("action_key") or _ACTION_KEY_BY_COMMAND.get(command),
                    "risk_tier": spec["risk_tier"],
                    "risk_level": record["risk_level"],
                    "required_user_action": record["required_user_action"],
                    "expires_at": record["expires_at"],
                    "pending_status": record["status"],
                    "message": "Kullanıcı onayı gerekli (stub — gerçek yürütme yok)",
                    "arguments_preview": record["arguments_preview"],
                    "schema_version": SCHEMA_VERSION,
                }
            return {
                "ok": False,
                "status": "rejected",
                "command": command,
                "approval_required": True,
                "error": gate.reason or "approval_denied",
                "schema_version": SCHEMA_VERSION,
            }
        tok = (approval_token or "").strip()
        aid = (approval_id or "").strip()
        if not aid:
            found = find_pending_by_token(repo_root, tok)
            if found is not None:
                aid = str(found[1].get("approval_id") or found[0].stem)
        ok, reason, approved_rec = try_consume_approval_token(repo_root, aid, tok)
        if not ok or approved_rec is None:
            return {
                "ok": False,
                "status": "rejected",
                "command": command,
                "approval_required": True,
                "error": reason or "invalid_approval_token",
                "schema_version": SCHEMA_VERSION,
            }

    ts = int(time.time() * 1000)
    base: dict[str, Any] = {
        "ok": True,
        "status": "stub",
        "command": command,
        "stub_only": True,
        "simulated_at_ms": ts,
        "schema_version": SCHEMA_VERSION,
        "note": "not_implemented — private layer executor",
    }

    if command == CMD_OPEN_APP:
        base["simulated"] = {
            "action": "open_app",
            "app_name": str(arguments.get("app_name") or ""),
        }
    elif command == CMD_OPEN_URL:
        base["simulated"] = {"action": "open_url", "url": str(arguments.get("url") or "")}
    elif command == CMD_READ_SCREEN:
        base["simulated"] = {
            "action": "read_screen_state",
            "scope": str(arguments.get("scope") or "active_window"),
            "snapshot": {
                "active_window_title": "[demo] Lumos Panel",
                "focused_element": "chat_input",
                "stub": True,
            },
        }
    elif command == CMD_TYPE_TEXT:
        base["simulated"] = {
            "action": "type_text",
            "text_echo": str(arguments.get("text") or "")[:500],
            "chars": len(str(arguments.get("text") or "")),
        }
    elif command == CMD_SUGGEST_CLICK:
        x = arguments.get("x")
        y = arguments.get("y")
        base["simulated"] = {
            "action": "suggest_click",
            "target_description": str(arguments.get("target_description") or ""),
            "suggested_coordinates": {"x": x, "y": y},
            "auto_click": False,
        }
    elif command == CMD_REQUEST_FILE_PICKER:
        base["simulated"] = {
            "action": "request_file_picker",
            "purpose": str(arguments.get("purpose") or ""),
            "accept": str(arguments.get("accept") or "*"),
            "picker_token": f"stub-picker-{secrets.token_hex(8)}",
        }
    elif command == CMD_REQUEST_USER_APPROVAL:
        base["status"] = "approval_recorded"
        base["simulated"] = {
            "action": "request_user_approval",
            "summary": str(arguments.get("summary") or ""),
            "risk_level": str(arguments.get("risk_level") or "medium"),
            "approval_token": secrets.token_hex(16),
        }

    return base


def _safe_preview(arguments: dict[str, Any], max_len: int = 400) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in arguments.items():
        s = str(v)
        out[k] = s[:max_len] + ("…" if len(s) > max_len else "")
    return out


def handle_tools_execute_body(
    body: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    """POST /tools/execute gövdesini işler."""
    if not isinstance(body, dict):
        return 400, {"ok": False, "error": "invalid_body"}
    command = str(body.get("command") or "").strip()
    arguments = body.get("arguments")
    if not isinstance(arguments, dict):
        arguments = {}
    approval_token = body.get("approval_token")
    approval_id = body.get("approval_id")
    requested_by = str(body.get("requested_by") or "pc_remote_bridge").strip() or "pc_remote_bridge"
    target_device = str(body.get("target_device") or "local").strip() or "local"

    out = execute_tool_stub(
        command,
        arguments,
        approval_token=str(approval_token) if approval_token else None,
        approval_id=str(approval_id) if approval_id else None,
        repo_root=repo_root,
        requested_by=requested_by,
        target_device=target_device,
    )
    status = 200 if out.get("ok") or out.get("status") == "pending_approval" else 403
    if out.get("status") == "rejected":
        status = 400
    return status, out


def approve_pc_remote_pending(
    path: Path,
    record: dict[str, Any],
    *,
    approved: bool,
    repo_root: Path,
) -> tuple[bool, str, dict[str, Any] | None]:
    """POST /approve için PC remote pending kaydı — token zaten doğrulandı."""
    mark_expired_if_needed(path, record)
    if str(record.get("status") or "") == "expired":
        return False, "approval_expired", None
    if bool(record.get("used")):
        return False, "zaten kullanıldı", None
    if not approved:
        reject_pending_record(path, record)
        return True, "", {"status": "rejected", "approval_id": record.get("approval_id")}
    try:
        from policy.confirmation_policy import (
            is_confirmation_enabled,
            validate_bridge_confirmation,
        )

        lumos_base = (repo_root / ".lumos").resolve()
        if is_confirmation_enabled():
            bridge_result = validate_bridge_confirmation(record, base_dir=lumos_base)
            if not bridge_result.allowed:
                return False, bridge_result.reason or "confirmation validation failed", None
    except ImportError:
        pass
    updated = approve_pending_record(path, record)
    return True, "", {
        "status": "approved",
        "approval_id": updated.get("approval_id"),
        "command": updated.get("command"),
        "approval_token": updated.get("approval_token"),
        "approval_file": updated.get("approval_file"),
        "message": "Onaylandı — POST /tools/execute ile approval_token gönderin",
    }
