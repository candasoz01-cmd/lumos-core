"""Ortak gate kontrolü: onay / netleştirme beklerken fiziksel yürütme yok."""
from __future__ import annotations

from typing import Any


def gate_blocks_execution(out: dict[str, Any]) -> bool:
    if str(out.get("execution_mode") or "").lower() == "pending_approval":
        return True
    hb = out.get("http_body") if isinstance(out.get("http_body"), dict) else {}
    lg = hb.get("lumos_gate") if isinstance(hb.get("lumos_gate"), dict) else {}
    if str(lg.get("execution_mode") or "").lower() == "pending_approval":
        return True
    return hb.get("requires_clarification") is True
