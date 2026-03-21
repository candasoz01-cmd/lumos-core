#!/usr/bin/env python3
"""
Read-only backend state for panel Phase 1 bridge.
Uses only: workspace_contract (paths, writing_base_dir, sandbox_base_path, LUMOS_SANDBOX_DIRNAME)
and startup_health.consent_ok. No main.py, no write flows, no guard change.
Output: JSON in fixture-compatible shape for Dashboard, Sandbox, System, Config (config.json mtime only),
Identity, Keystore, Tasks, Trash, Logs, Guidance, Kartlı sonuç (yanit).
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

def _task_engine_health(base: Path) -> tuple[str, str]:
    """Read-only: tasks.json varlığı ve okunabilirliği → (status, note). System ekranı task_engine kartı."""
    tasks_file = base / "tasks.json"
    if not tasks_file.is_file():
        return ("—", "Görev listesi yok.")
    try:
        json.loads(tasks_file.read_text(encoding="utf-8"))
        return ("ok", "Görev listesi okunabiliyor.")
    except Exception:
        return ("—", "Görev listesi okunamadı.")


def _read_tasks_payload(base: Path) -> dict:
    """Read-only: base/tasks.json → task_list, task_filter, selected_task_id, list_updated, list_updated_text, tasks_file_path, tasks_file_exists, task_count.
    Güvenli sinyaller: tasks.json var/yok, mtime (list_updated), çözülmüş dosya yolu, görev sayısı (task_count)."""
    tasks_file = base / "tasks.json"
    tasks_file_exists = tasks_file.is_file()
    out = {
        "task_list": [],
        "task_filter": "all",
        "selected_task_id": None,
        "list_updated": None,
        "list_updated_text": None,
        "tasks_file_path": None,
        "tasks_file_exists": tasks_file_exists,
        "task_count": 0,
    }
    if not tasks_file_exists:
        return out
    try:
        out["tasks_file_path"] = str(tasks_file.resolve())
    except Exception:
        pass
    try:
        st_mtime = tasks_file.stat().st_mtime
        out["list_updated"] = datetime.fromtimestamp(st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        out["list_updated_text"] = _iso_to_display_text(out["list_updated"])
    except Exception:
        pass
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
    out["task_count"] = len(out["task_list"])
    return out

def _read_trash_payload(base: Path) -> dict:
    """Read-only: base/trash dizin listesi → trash_location, trash_last_move, trash_items, trash_dir_exists, trash_item_count, trash_scope_fallback_note.
    Güvenli sinyaller: trash konumu (çözülmüş), dizin var/yok, öğe sayısı. original_path/scope dosya sisteminden türetilmediği için —; fallback notu eklenir."""
    base_resolved = base.resolve()
    trash_dir = base_resolved / "trash"
    trash_dir_exists = trash_dir.is_dir()
    out = {
        "trash_location": str(trash_dir),
        "trash_last_move": None,
        "trash_items": [],
        "trash_dir_exists": trash_dir_exists,
        "trash_item_count": 0,
        "trash_scope_fallback_note": "original_path ve scope dosya sisteminden okunamadı; meta yoksa — gösterilir.",
    }
    if not trash_dir_exists:
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
                rel = p.relative_to(base_resolved)
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
    out["trash_item_count"] = len(items)
    if last_mtime is not None:
        try:
            out["trash_last_move"] = datetime.fromtimestamp(last_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            pass
    return out

def _read_logs_payload(base: Path) -> dict:
    """Read-only: base/logs/log.txt son satırlar → log_items, log_filter, log_file_updated, log_updated_text, log_location, log_file_exists, log_line_count.
    Güvenli sinyaller: log dosyası konumu (çözülmüş), var/yok, son güncelleme (mtime + metin), satır sayısı (görüntülenen)."""
    base_resolved = base.resolve()
    log_file = base_resolved / "logs" / "log.txt"
    log_file_exists = log_file.is_file()
    out = {
        "log_items": [],
        "log_filter": "all",
        "log_file_updated": None,
        "log_updated_text": None,
        "log_location": str(log_file),
        "log_file_exists": log_file_exists,
        "log_line_count": 0,
    }
    if not log_file_exists:
        return out
    try:
        mtime = log_file.stat().st_mtime
        out["log_file_updated"] = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        out["log_updated_text"] = _iso_to_display_text(out["log_file_updated"])
    except Exception:
        pass
    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
        lines = [s.strip() for s in text.splitlines() if s.strip()][-100:]
    except Exception:
        return out
    try:
        ts = datetime.fromtimestamp(log_file.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        ts = "—"
    for i, line in enumerate(lines):
        out["log_items"].append({
            "id": "L" + str(i + 1),
            "kind": "log",
            "text": line[:500] + ("…" if len(line) > 500 else ""),
            "ts": ts,
        })
    out["log_line_count"] = len(out["log_items"])
    return out

def _file_mtime_iso(path: Path) -> str | None:
    """Dosya varsa mtime ISO; yoksa veya hata ise None."""
    if not path.is_file():
        return None
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None


def _iso_to_display_text(iso: str | None) -> str | None:
    """ISO tarih → panelde gösterim metni (Son güncelleme: DD.MM.YYYY HH:MM). Okunamazsa None."""
    if not iso or iso == "—":
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return "Son güncelleme: " + dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return None


def _last_jsonl_record(path: Path) -> dict | None:
    """JSONL dosyasının son geçerli satırını dict olarak döndür; yoksa None."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            return rec if isinstance(rec, dict) else None
        except json.JSONDecodeError:
            continue
    return None


def _build_yanit_card_payload(
    *,
    repo_root: Path,
    guidance: dict,
    system_health: dict,
    tasks_payload: dict,
    identity_payload: dict,
    keystore_payload: dict,
    config_payload: dict,
    sandbox: dict,
) -> dict:
    """
    Kartlı sonuç ekranı (#yanit): workspace + guidance + isteğe bağlı son karar kaydı.
    Okuma: salt-okunur; karar motoruna yazmaz.
    """
    mode = (guidance.get("mode") or "offline").strip().lower()
    mode_tr = "çevrimiçi" if mode == "online" else "çevrimdışı"
    writing = (sandbox.get("writing_base_dir") or "canlı") or "canlı"
    writing_tr = "korunmuş alan (sandbox)" if str(writing).lower() == "sandbox" else "canlı çalışma alanı"
    consent = bool(guidance.get("consent"))
    consent_tr = (
        "Genel onay (consent) kayıtlı; keystore görünümü buna göre."
        if consent
        else "Genel onay henüz kayıtlı değil; hassas yazım ve keystore akışı kısıtlı kalır."
    )
    gen = system_health.get("general") if isinstance(system_health.get("general"), dict) else {}
    gen_note = (gen.get("note") or "").strip()
    summary = (
        f"Şu an mod {mode_tr}. Yazım hedefi {writing_tr}. {consent_tr}"
    )
    if gen_note:
        summary += f" Sistem özeti: {gen_note}"

    context_line: str | None = None
    hist = _last_jsonl_record(repo_root / "logs" / "lumos_decision_history.jsonl")
    if hist:
        g_goal = str(hist.get("goal") or "").strip()
        g_opt = str(hist.get("option_description") or "").strip()
        if g_goal or g_opt:
            g_goal = g_goal[:160] + ("…" if len(g_goal) > 160 else "")
            g_opt = g_opt[:160] + ("…" if len(g_opt) > 160 else "")
            context_line = "Son karar kaydı: " + g_goal + (" — " + g_opt if g_opt else "") + "."
    if not context_line and tasks_payload.get("list_updated_text"):
        tc = tasks_payload.get("task_count") or 0
        context_line = str(tasks_payload.get("list_updated_text")) + f" Görev sayısı: {tc}."
    if not context_line:
        snap = config_payload.get("config_snapshot") if isinstance(config_payload.get("config_snapshot"), dict) else {}
        lat = snap.get("last_activity_text") or ""
        if str(lat).strip():
            context_line = str(lat).strip()

    lock = str(guidance.get("lock") or "LOCKED").upper()
    lock_tr = "Kilit açık (onay akışına göre)." if lock == "UNLOCKED" else "Kilit kapalı; koruma aktif."

    iden = str(identity_payload.get("identity_state") or "—").strip()
    ks = str(keystore_payload.get("keystore_state") or "—").strip()
    te = system_health.get("task_engine") if isinstance(system_health.get("task_engine"), dict) else {}
    te_note = str(te.get("note") or "—").strip()
    tc = int(tasks_payload.get("task_count") or 0)
    tfe = bool(tasks_payload.get("tasks_file_exists"))

    understood: list[str] = [
        f"Mod: {mode_tr}.",
        lock_tr,
        f"Genel onay: {'açık' if consent else 'kapalı'}.",
        f"Kimlik dosyası: {iden}.",
        f"Anahtar kasası: {ks}.",
        f"Görev motoru: {te_note}",
    ]
    if tfe:
        understood.append(f"tasks.json içinde {tc} görev kaydı var.")
    else:
        understood.append("tasks.json bulunamadı veya okunamadı; görev listesi boş sayılır.")

    recommendation: list[str] = []
    br = guidance.get("blocked_reason")
    if br and str(br).strip():
        recommendation.append(f"Engel: {str(br).strip()} — bağlı işlemler bunun giderilmesini bekleyebilir.")
    ns = guidance.get("next_step")
    if ns and str(ns).strip():
        recommendation.append(f"Önerilen sonraki adım: {str(ns).strip()}")
    if not consent:
        recommendation.append("Çalışmaya devam için consent kaydını tamamlayın (startup_health; hassas yüzeyler kapalı kalır).")
    te_st = str(te.get("status") or "").strip()
    if te_st and te_st not in ("ok", "—"):
        recommendation.append(f"Görev listesini doğrulayın: {te_note}")
    wc = system_health.get("workspace_contract") if isinstance(system_health.get("workspace_contract"), dict) else {}
    if str(wc.get("status") or "").strip() not in ("", "ok"):
        wn = str(wc.get("note") or "Workspace sözleşmesini doğrulayın.").strip()
        recommendation.append(wn)
    if not recommendation:
        recommendation.append(
            "Görevler, Kayıtlar ve Sistem Durumu ekranlarını düzenli kontrol edin; veri salt-okunur köprüden gelir."
        )

    questions: list[str] = []
    if tfe and tc == 0:
        questions.append("Görev kuyruğu boş; ilk görevi hangi kanaldan oluşturacaksınız?")
    if iden == "mevcut değil":
        questions.append("Kimlik dosyası yok; bu ortamda kimlik kurulumu gerekiyor mu?")

    snap2 = config_payload.get("config_snapshot") if isinstance(config_payload.get("config_snapshot"), dict) else {}
    updated_at = tasks_payload.get("list_updated") or snap2.get("last_activity")

    return {
        "summary": summary,
        "context_line": context_line,
        "understood": understood,
        "recommendation": recommendation,
        "questions": questions,
        "updated_at": updated_at,
    }


def _safe_resolve_path(path: Path | None) -> str | None:
    """Path çözümle; hata veya yoksa None (panel fallback '—' kullanır)."""
    if path is None:
        return None
    try:
        return str(path.resolve())
    except Exception:
        return None


def _build_state() -> dict:
    base = _base_dir()
    is_sandbox = _is_sandbox_mode()

    writing_label = "sandbox" if is_sandbox else "canlı"

    # Identity / Keystore / Config path'leri (sadece path + mtime; içerik okunmaz)
    identity_path = keystore_path = config_path = None
    try:
        from core.workspace_contract import identity_file_path, keystore_file_path, config_file_path
        identity_path = identity_file_path(base)
        keystore_path = keystore_file_path(base)
        config_path = config_file_path(base)
    except Exception:
        pass

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

    # Config / Tasks / Trash / Logs önce üretilir; System özeti bunlardan türetilir
    config_last = _file_mtime_iso(config_path) if config_path else None
    config_activity_text = "Config dosyası son güncelleme (mtime)." if config_last else "Config dosyası yok veya okunamadı; yalnızca okuma."
    config_payload = {
        "config_snapshot": {
            "profil": os.environ.get("LUMOS_PROFILE") or "—",
            "workspace_root": str(base),
            "write_status": "Salt okunur",
            "last_activity": config_last,
            "last_activity_text": config_activity_text,
        }
    }
    tasks_payload = _read_tasks_payload(base)
    trash_payload = _read_trash_payload(base)
    logs_payload = _read_logs_payload(base)

    # System: Phase 2 genişletilmiş okuma — workspace_contract path'leri, task_engine, consent, özet
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
    general_note = "Consent kayıtlı. Lock/presence bu hatta doğrulanmaz." if consent else "Consent alınmadı."

    # workspace_contract: gerçek okuma — modül yüklenip path'ler dönebiliyor mu
    _wc_status, _wc_note = "ok", "Sözleşme yüklü; çekirdek path'ler tanımlı."
    try:
        from core.workspace_contract import trash_path, sandbox_base_path
        trash_path(base)
        sandbox_base_path(base)
    except Exception:
        _wc_status, _wc_note = "uyarı", "Sözleşme yüklenemedi."
    _te_status, _te_note = _task_engine_health(base)

    system_health = {}
    for key, title, default_status, default_note in SYSTEM_HEALTH_KEYS:
        if key == "workspace_contract":
            system_health[key] = {"status": _wc_status, "note": _wc_note}
        elif key == "task_engine":
            system_health[key] = {"status": _te_status, "note": _te_note}
        elif key == "keystore_sink":
            system_health[key] = {"status": general_status, "note": "Keystore durumu consent ile türetildi; ifşa yok."}
        elif key == "general":
            system_health[key] = {"status": general_status, "note": general_note}
        else:
            system_health[key] = {"status": default_status, "note": default_note}

    # Çözümlü path'ler (workspace_contract; okunamazsa None → panel "—" gösterir)
    system_paths = {}
    try:
        from core.workspace_contract import writing_base_dir, trash_path as _trash_path, sandbox_base_path as _sandbox_base, config_file_path as _config_path, logs_dir_path
        system_paths["writing_base"] = _safe_resolve_path(writing_base_dir(base, is_sandbox))
        system_paths["trash"] = _safe_resolve_path(_trash_path(base))
        system_paths["sandbox_base"] = _safe_resolve_path(_sandbox_base(base))
        system_paths["config"] = _safe_resolve_path(_config_path(base))
        system_paths["logs"] = _safe_resolve_path(logs_dir_path(base))
    except Exception:
        pass
    tasks_path = base / "tasks.json"
    system_paths["tasks"] = _safe_resolve_path(tasks_path) if tasks_path else None

    # Çekirdek dosya özeti (zaten okunan tasks/trash/logs/config sinyallerinin dar yansıması)
    system_summary = {
        "config_exists": config_path.is_file() if config_path else False,
        "tasks_file_exists": tasks_payload.get("tasks_file_exists", False),
        "task_count": tasks_payload.get("task_count", 0),
        "trash_dir_exists": trash_payload.get("trash_dir_exists", False),
        "trash_item_count": trash_payload.get("trash_item_count", 0),
        "log_file_exists": logs_payload.get("log_file_exists", False),
        "log_line_count": logs_payload.get("log_line_count", 0),
    }

    system = {
        "system_health": system_health,
        "system_paths": system_paths,
        "system_summary": system_summary,
    }

    # Identity: read-only — identity.json varlık + mtime; kimlik içeriği okunmaz
    identity_exists = identity_path.is_file() if identity_path else False
    identity_last = _file_mtime_iso(identity_path) if identity_path else None
    identity_payload = {
        "identity_state": "mevcut" if identity_exists else "mevcut değil",
        "identity_last_write": identity_last,
        "identity_target_scope": "çekirdek kimlik alanı",
        "identity_guard_result": "Korunuyor",
    }

    # Keystore: read-only — consent_ok + keystore.json mtime; anahtar/passphrase ifşası yok
    keystore_last = _file_mtime_iso(keystore_path) if keystore_path else None
    keystore_payload = {
        "keystore_ready": consent,
        "keystore_state": "Hazır" if consent else "Kilitli",
        "keystore_last_update": keystore_last,
        "keystore_write_scope": "Kilit açılmadan hassas yazım yapılmaz",
    }

    # Guidance: next-step planner surface (mode, lock, consent; blocked_reason/next_step when set by CLI)
    mode = (os.environ.get("LUMOS_MODE") or "offline").strip().lower()
    mode = "online" if mode == "online" else "offline"
    lock = "UNLOCKED" if consent else "LOCKED"  # read_backend_state has no Lumos lock; proxy from consent
    guidance = {
        "mode": mode,
        "lock": lock,
        "consent": consent,
        "blocked_reason": None,
        "next_step": None,
    }

    yanit_payload = _build_yanit_card_payload(
        repo_root=_repo_root,
        guidance=guidance,
        system_health=system_health,
        tasks_payload=tasks_payload,
        identity_payload=identity_payload,
        keystore_payload=keystore_payload,
        config_payload=config_payload,
        sandbox=sandbox,
    )

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
        "guidance": guidance,
        "yanit": yanit_payload,
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
