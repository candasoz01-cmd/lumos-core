"""
Minimal: .lumos/cursor_bridge/command.json → bridge hedef metni.
execution_mode şimdilik yalnızca okunur (gelecekte kısıtlama için).
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
    """
    zsh echo bazen instruction içinde gerçek satır sonu üretir (geçersiz JSON).
    "instruction":"... ile ","execution_mode" arasını ham metin olarak alır.
    """
    if '"instruction"' not in raw or '"execution_mode"' not in raw:
        return None
    try:
        start = raw.index('"instruction"')
        colon = raw.index(":", start)
        q0 = raw.index('"', colon + 1)
        key = '","execution_mode"'
        end = raw.index(key, q0 + 1)
        inner = raw[q0 + 1 : end]
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
    """
    {lumos}/cursor_bridge/command.json okur.
    Dönüş: {"instruction": str, "execution_mode": str} veya geçersiz/eksikte None.
    """
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
    """Önce command.json içindeki instruction; yoksa argv; o da yoksa default."""
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




# FORCE_LOW_RISK
def _force_low_risk(meta: dict) -> dict:
    if not meta:
        return meta
    meta["risk_level"] = "low"
    meta["requires_approval"] = False
    return meta


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """
    instruction ile bridge TARGET: yama akışını çalıştırır (brain yok; doğrudan try_instruction_patch_apply).
    execution_mode şimdilik yalnızca okunur.
    """
    instruction = _normalize_instruction(str(payload.get("instruction") or "")).strip()
    if not instruction:
        return {"execution_result": "parse_error", "error_type": "missing_instruction", "detail": "instruction boş"}

    _ = str(payload.get("execution_mode") or "task").strip() or "task"

    from kando.cursor_bridge import build_execution_packet, try_instruction_patch_apply
    from task_engine import PROFILE_GUVENLI_YURUT
    from task_engine.engine import TaskRecord

    task = TaskRecord(
        task_id=0,
        title="file_patch_executor",
        description=instruction,
        created_at="1970-01-01T00:00:00Z",
        permission_profile=PROFILE_GUVENLI_YURUT,
        steps=[],
    )
    exe = build_execution_packet(
        instruction,
        task,
        permission_profile=PROFILE_GUVENLI_YURUT,
        general_approval=True,
    )
    try_instruction_patch_apply(instruction, exe)
    ex = exe.constraints.get("execution")
    if isinstance(ex, dict):
        return dict(ex)
    return {"execution_result": "ok", "detail": "execution dict yok", "execution": ex}
