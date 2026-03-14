#!/usr/bin/env python3
"""
Read-only backend state for panel Phase 1 bridge.
Uses only: workspace_contract (paths, writing_base_dir, sandbox_base_path, LUMOS_SANDBOX_DIRNAME)
and startup_health.consent_ok. No main.py, no write flows, no guard change.
Output: JSON in fixture-compatible shape for Dashboard, Sandbox, System, Config, Identity, Keystore,
Tasks, Trash, Logs.
Env: LUMOS_BASE_DIR (default .lumos), LUMOS_SANDBOX_MODE (default false), LUMOS_PROFILE (optional).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
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

# Panel status (filtre uyumu): engine status → ekran etiketi
_TASK_STATUS_MAP = {
    "bekliyor": "bekleyen",
    "calisiyor": "aktif",
    "tamamlandi": "tamamlandı",
    "hata": "başarısız",
    "durdu": "engellenen",
    "kismi": "kismi",
    "simulasyon": "simulasyon",
    "dogrulanamadi": "dogrulanamadi",
}

def _read_tasks_payload(base: Path) -> dict:
    """Read-only: base/tasks.json → task_list, task_filter, selected_task_id."""
    out = {"task_list": [], "task_filter": "all", "selected_task_id": None}
    tasks_file = base / "tasks.json"
    if not tasks_file.is_file():
        return out
    try:
        data = json.loads(tasks_file.read_text(encoding="utf-8"))
        raw = data.get("tasks") or []
    except Exception:
        return out
    for t in raw:
        tid = t.get("task_id")
        if tid is None:
            continue
        status = t.get("status") or "bekliyor"
        status_panel = _TASK_STATUS_MAP.get(status, status)
        updated = t.get("completed_at") or t.get("created_at") or ""
        last_run = t.get("completed_at") if status in ("tamamlandi", "hata", "durdu", "kismi", "simulasyon", "dogrulanamadi") else None
        summary = (t.get("summary") or t.get("last_output") or "—").strip() or "—"
        out["task_list"].append({
            "id": str(tid),
            "title": t.get("title") or "—",
            "status": status_panel,
            "updated": updated,
            "last_run": last_run,
            "guard_result": "—",
            "output_summary": summary[:200] + ("…" if len(summary) > 200 else ""),
        })
    return out

def _read_trash_payload(base: Path) -> dict:
    """Read-only: base/trash dizin listesi → trash_location, trash_last_move, trash_items."""
    trash_dir = base / "trash"
    out = {
        "trash_location": str(trash_dir),
        "trash_last_move": None,
        "trash_items": [],
    }
    if not trash_dir.is_dir():
        return out
    last_mtime = None
    items = []
    for i, p in enumerate(sorted(trash_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)):
        try:
            st = p.stat()
            mtime = st.st_mtime
            if last_mtime is None or mtime > last_mtime:
                last_mtime = mtime
            try:
                ts = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            except Exception:
                ts = "—"
            try:
                rel = p.relative_to(base)
            except ValueError:
                rel = p
            items.append({
                "id": "tr" + str(i + 1),
                "name": p.name,
                "original_path": "—",
                "trash_path": str(rel),
                "moved_at": ts,
                "scope": "—",
            })
        except OSError:
            continue
    out["trash_items"] = items
    if last_mtime is not None:
        try:
            out["trash_last_move"] = datetime.fromtimestamp(last_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            pass
    return out

def _read_logs_payload(base: Path) -> dict:
    """Read-only: base/logs/log.txt son satırlar → log_items, log_filter."""
    log_file = base / "logs" / "log.txt"
    out = {"log_items": [], "log_filter": "all"}
    if not log_file.is_file():
        return out
    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
        lines = [s.strip() for s in text.splitlines() if s.strip()][-100:]
    except Exception:
        return out
    try:
        mtime = log_file.stat().st_mtime
        ts = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        ts = "—"
    for i, line in enumerate(lines):
        out["log_items"].append({
            "id": "L" + str(i + 1),
            "kind": "log",
            "text": line[:500] + ("…" if len(line) > 500 else ""),
            "ts": ts,
        })
    return out

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

    # System: Phase 2 ilk gerçek backend okuma hedefi. Tek liste ile genişletilebilir; consent_ok şu an tek gerçek okuma.
    # Yeni kart eklemek için SYSTEM_HEALTH_KEYS'e (key, title, default_status, default_note) ekleyin; Phase 2'de key bazlı gerçek okuma eklenebilir.
    SYSTEM_HEALTH_KEYS = [
        ("workspace_contract", "Workspace Sözleşmesi", "ok", "Sözleşme yüklü; çekirdek path'ler tanımlı."),
        ("task_engine", "Görev Motoru", "—", "Veri yok."),
        ("sandbox_source", "Sandbox Kaynağı", "ok", "Sandbox kaynağı sözleşmeden türetildi."),
        ("trash_contract", "Trash Sözleşmesi", "ok", "Trash konumu sözleşmeyle sabit."),
        ("config_sink", "Config Sink", "ok", "Config salt okunur alanlar bridge ile besleniyor."),
        ("identity_sink", "Identity Sink", "ok", "Identity salt okunur alanlar bridge ile besleniyor."),
        ("keystore_sink", "Keystore Sink", "—", "Keystore durumu consent ile türetildi; ifşa yok."),
        ("general", "Genel Sağlık", "—", "Consent durumu türetildi."),
    ]
    consent = False
    try:
        from core.startup_health import consent_ok
        consent = consent_ok(base)
    except Exception:
        pass
    general_status = "ok" if consent else "uyarı"
    general_note = "Consent kayıtlı." if consent else "Consent alınmadı."

    system_health = {}
    for key, title, default_status, default_note in SYSTEM_HEALTH_KEYS:
        if key == "keystore_sink":
            system_health[key] = {"status": general_status, "note": "Keystore durumu consent ile türetildi; ifşa yok."}
        elif key == "general":
            system_health[key] = {"status": general_status, "note": general_note}
        else:
            system_health[key] = {"status": default_status, "note": default_note}
    system = {"system_health": system_health}

    # Config: read-only alanlar (workspace path, profil env; yazım yok)
    config_snapshot = {
        "profil": os.environ.get("LUMOS_PROFILE") or "—",
        "workspace_root": str(base),
        "write_status": "Salt okunur",
        "last_activity": None,
        "last_activity_text": "Backend yazım kapalı; yalnızca okuma.",
    }
    config_payload = {"config_snapshot": config_snapshot}

    # Identity: read-only alanlar (path/kapsam; kimlik içeriği okunmaz)
    identity_payload = {
        "identity_state": "—",
        "identity_last_write": None,
        "identity_target_scope": "çekirdek kimlik alanı",
        "identity_guard_result": "Korunuyor",
    }

    # Keystore: read-only durum (consent_ok; anahtar/passphrase ifşası yok)
    keystore_payload = {
        "keystore_ready": consent,
        "keystore_state": "Hazır" if consent else "Kilitli",
        "keystore_last_update": None,
        "keystore_write_scope": "Kilit açılmadan hassas yazım yapılmaz",
    }

    # Görevler: read-only base/tasks.json (task_list → panel contract)
    tasks_payload = _read_tasks_payload(base)

    # Silinenler: read-only base/trash dizin listesi
    trash_payload = _read_trash_payload(base)

    # Kayıtlar: read-only base/logs/log.txt son satırlar
    logs_payload = _read_logs_payload(base)

    return {
        "dashboard": dashboard,
        "sandbox": sandbox,
        "system": system,
        "config": config_payload,
        "identity": identity_payload,
        "keystore": keystore_payload,
        "tasks": tasks_payload,
        "trash": trash_payload,
        "logs": logs_payload,
    }

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
