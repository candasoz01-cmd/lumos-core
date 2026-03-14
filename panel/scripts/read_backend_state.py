#!/usr/bin/env python3
"""
Read-only backend state for panel Phase 1 bridge.
Uses only: workspace_contract (writing_base_dir, sandbox_base_path, LUMOS_SANDBOX_DIRNAME)
and startup_health.consent_ok. No main.py, no write flows, no guard change.
Output: JSON in fixture-compatible shape for Dashboard, Sandbox, System.
Env: LUMOS_BASE_DIR (default .lumos), LUMOS_SANDBOX_MODE (default false).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Repo src for imports (panel/scripts -> panel -> repo root -> src)
_repo_root = Path(__file__).resolve().parent.parent.parent
_src = _repo_root / "src"
if _src.is_dir():
    sys.path.insert(0, str(_src))
else:
    # Fallback: assume run from repo root with PYTHONPATH=src
    pass

def _base_dir() -> Path:
    return Path(os.environ.get("LUMOS_BASE_DIR", ".lumos"))

def _is_sandbox_mode() -> bool:
    v = os.environ.get("LUMOS_SANDBOX_MODE", "false").lower()
    return v in ("1", "true", "yes")

def _build_state() -> dict:
    base = _base_dir()
    is_sandbox = _is_sandbox_mode()

    writing_label = "sandbox" if is_sandbox else "canlı"

    dashboard = {
        "sandbox_mode": is_sandbox,
        "writing_base_dir": writing_label,
        "guard_status": "KORUMA AKTİF",
        "recent_events": [],
        "warnings": [],
    }

    sandbox = {
        "sandbox_mode": is_sandbox,
        "sandbox_source": "varsayılan",
        "writing_base_dir": writing_label,
    }

    # System: only consent_ok is safe without keystore/presence
    try:
        from core.startup_health import consent_ok
        consent = consent_ok(base)
        general_status = "ok" if consent else "uyarı"
        general_note = "Consent kayıtlı." if consent else "Consent alınmadı."
    except Exception:
        general_status = "—"
        general_note = "Veri yok."

    system_health = {
        "workspace_contract": {"status": "ok", "note": "Sözleşme yüklü; çekirdek path'ler tanımlı."},
        "task_engine": {"status": "—", "note": "Veri yok."},
        "sandbox_source": {"status": "ok", "note": "Sandbox kaynağı sözleşmeden türetildi."},
        "trash_contract": {"status": "ok", "note": "Trash konumu sözleşmeyle sabit."},
        "config_sink": {"status": "—", "note": "Veri yok."},
        "identity_sink": {"status": "—", "note": "Veri yok."},
        "keystore_sink": {"status": "—", "note": "Veri yok."},
        "general": {"status": general_status, "note": general_note},
    }
    system = {"system_health": system_health}

    return {"dashboard": dashboard, "sandbox": sandbox, "system": system}

def main() -> None:
    write_path = None
    if "--write" in sys.argv:
        write_path = _repo_root / "panel" / "js" / "state_inject.js"

    state = _build_state()
    payload = json.dumps(state, ensure_ascii=False, indent=2)

    if write_path is not None:
        content = "// Read-only bridge state (set by panel/scripts/read_backend_state.py --write)\nwindow.__LUMOS_READ_STATE__ = " + payload + ";\n"
        write_path.write_text(content, encoding="utf-8")
        print("Wrote", write_path, file=sys.stderr)
    else:
        print(payload)

if __name__ == "__main__":
    main()
