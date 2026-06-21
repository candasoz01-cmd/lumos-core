"""
Panel read-only bridge payload (Phase 1).

`build_panel_read_state()` üretir: `window.__LUMOS_READ_STATE__` ile uyumlu tek dict
(dashboard, sandbox, system, config, identity, keystore, tasks, trash, logs, guidance, yanit).

Aynı ortam değişkenlerini kullanır: LUMOS_BASE_DIR, LUMOS_SANDBOX_MODE, LUMOS_PROFILE, LUMOS_MODE.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from core.lumos_base_dir import lumos_base_dir as _base_dir

from policy.action_policy import (  # noqa: E402
    CREATE_TASK,
    check_policy,
    log_policy_blocked,
    policy_user_message,
)
from task_engine.profiles import (  # noqa: E402
    ALL_PROFILES,
    PROFILE_RAPOR,
    get_profile_display_name,
    may_execute_step_at_runtime,
    panel_action_to_step_kind,
    requires_explicit_approval,
)

def _is_sandbox_mode() -> bool:
    v = os.environ.get("LUMOS_SANDBOX_MODE", "false").lower()
    return v in ("1", "true", "yes")


_CODEX_PANEL_WARNING = (
    "Demo panel — tam policy/profil zinciri CLI ile aynı değil; riskli işlemde dur."
)

_PANEL_POLICY_NOTE = "Panel görev mutasyonları check_policy ile sınırlandırılır (ADR-012 C6)."


def _panel_policy_context() -> dict:
    """CLI `cli_tasks_mutation` ile aynı policy snapshot — panel köprü ortamı."""
    mode = (os.environ.get("LUMOS_MODE") or "offline").strip().lower()
    online = mode == "online"
    base = _base_dir()
    consent = False
    try:
        from core.startup_health import consent_ok

        consent = consent_ok(base)
    except Exception:
        pass
    # Panel okuma yolu runtime LockState doğrulamaz — CLI fallback: kilitli say.
    session_unlocked_env = (os.environ.get("LUMOS_SESSION_UNLOCKED") or "").strip().lower()
    if session_unlocked_env in ("1", "true", "yes"):
        koruma_active = False
    else:
        koruma_active = True
    return {"online": online, "koruma_active": koruma_active, "consent": consent}


def _panel_gate_reason_parts() -> list[str]:
    mode = (os.environ.get("LUMOS_MODE") or "offline").strip().lower()
    mode_label = "çevrimiçi" if mode == "online" else "çevrimdışı"
    profile = (os.environ.get("LUMOS_PROFILE") or "rapor").strip().lower() or "rapor"
    parts = [
        _CODEX_PANEL_WARNING,
        f"Mod: {mode_label}; profil: {profile}.",
    ]
    if _is_sandbox_mode():
        parts.append("Yazım hedefi: sandbox.")
    parts.append(_PANEL_POLICY_NOTE)
    return parts


def _panel_general_approval() -> bool:
    v = (os.environ.get("LUMOS_GENERAL_APPROVAL") or "").strip().lower()
    return v in ("1", "true", "yes")


def _panel_profile() -> str:
    raw = (os.environ.get("LUMOS_PROFILE") or "rapor").strip().lower()
    return raw or PROFILE_RAPOR


def _profile_block_message(profile: str, step_kind: str) -> str:
    return f"[PROFILE_BLOCKED] profil={profile} step={step_kind}"


def task_action_gate(
    action: str,
    *,
    log_on_block: bool = False,
    full_doc_replace: bool = False,
    profile_guard: bool = True,
) -> dict:
    """
    Panel görev mutasyon gate — check_policy (ADR-012 C6) + profil matrisi ikinci kapı.

    ``enabled`` policy veya profil red verdiğinde False; reason codex uyarısı + mesaj.
    ``full_doc_replace``: PUT /tasks.json → write_local step_kind.
    ``profile_guard``: False yalnızca delete-permanent (policy-only) için.
    ``log_on_block``: yalnızca mutasyon handler'larında True (GET listeleme log spam yapmaz).

    PR-C2/C3: Üçüncü kapı — ``policy.confirmation_policy.check_confirmation`` (CU4).
    Şimdilik enforcement yok; entegrasyon ``INTEGRATION_MARKERS['panel_bridge_gate']``.
    """
    pr = check_policy(action, _panel_policy_context())
    parts = _panel_gate_reason_parts()
    if not pr.allowed:
        parts.append(policy_user_message(action, pr.reason))
        if log_on_block:
            try:
                log_policy_blocked(str(_base_dir()), action, pr.reason)
            except Exception:
                pass
        return {"enabled": False, "reason": " ".join(parts)}

    if profile_guard:
        profile = _panel_profile()
        general_approval = _panel_general_approval()
        step_kind = panel_action_to_step_kind(action, full_doc_replace=full_doc_replace)
        if profile not in ALL_PROFILES:
            parts.append(_profile_block_message(profile, step_kind))
            parts.append(
                f"Geçersiz profil; izinli: {', '.join(ALL_PROFILES)}."
            )
            return {"enabled": False, "reason": " ".join(parts)}
        if not may_execute_step_at_runtime(profile, step_kind, general_approval):
            parts.append(_profile_block_message(profile, step_kind))
            display = get_profile_display_name(profile)
            if requires_explicit_approval(profile, step_kind, general_approval) and not general_approval:
                parts.append("Genel onay (LUMOS_GENERAL_APPROVAL) gerekli.")
            elif step_kind == "write_local":
                parts.append(f"Profil '{display}' tam doküman yazımına (write_local) izin vermiyor.")
            else:
                parts.append(f"Profil '{display}' bu mutasyonu (step={step_kind}) izin vermiyor.")
            return {"enabled": False, "reason": " ".join(parts)}
        parts.append("Mutasyon izinli (policy + profil).")
    else:
        parts.append("Mutasyon izinli (policy).")
    return {"enabled": True, "reason": " ".join(parts)}


def task_actions_gate() -> dict:
    """
    Panel görev mutasyon gate — guidance için CREATE_TASK temsili (ADR-012 C6).

    Ayrıntılı complete/delete için ``task_action_gate(action)`` kullanın.
    """
    return task_action_gate(CREATE_TASK)

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

def _store_file_health(tasks_file: Path) -> tuple[str, str]:
    """Read-only JSON file health → (status, note)."""
    if not tasks_file.is_file():
        return ("—", "Dosya yok.")
    try:
        json.loads(tasks_file.read_text(encoding="utf-8"))
        return ("ok", f"Okunabiliyor: {tasks_file.name}")
    except Exception:
        return ("—", "Dosya okunamadı.")


def _panel_tasks_store_health(base: Path) -> tuple[str, str]:
    """Read-only: panel CRUD store `.lumos/tasks.json`."""
    return _store_file_health(base / "tasks.json")


def _task_engine_store_health(base: Path) -> tuple[str, str]:
    """Read-only: TaskEngine store `.lumos/tasks/tasks.json`."""
    return _store_file_health(base / "tasks" / "tasks.json")


def _task_engine_health(base: Path) -> tuple[str, str]:
    """System card: dual-store summary (panel + engine paths; EC2-05)."""
    panel_status, panel_note = _panel_tasks_store_health(base)
    engine_status, engine_note = _task_engine_store_health(base)
    if panel_status == "ok" and engine_status == "ok":
        return ("ok", "Panel ve engine depoları okunabiliyor (ayrı path).")
    if panel_status == "ok":
        return ("uyarı", f"Panel store ok; engine store: {engine_note}")
    if engine_status == "ok":
        return ("uyarı", f"Engine store ok; panel store: {panel_note}")
    return ("—", "Her iki görev deposu da yok veya okunamıyor.")


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
    """Read-only: base/trash/*.json → trash_items (UI: state.trash.trash_items; tek şema, eksik alan yok)."""
    base_resolved = base.resolve()
    trash_dir = base_resolved / "trash"
    print("TRASH READ DIR:", str(trash_dir), flush=True)
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

    def _mtime_iso(st) -> str:
        try:
            return datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            return "—"

    last_mtime = None
    items: list[dict] = []

    def _collect_json_files(d: Path) -> list[Path]:
        """Bir dizindeki *.json dosyaları (alt klasörler ve .tmp hariç)."""
        found: list[Path] = []
        try:
            for entry in d.iterdir():
                # Klasörler (örn. trash/tasks) liste öğesi olarak GÖSTERİLMEZ.
                if entry.is_dir() or not entry.is_file():
                    continue
                if entry.name.endswith(".tmp") or entry.suffix.lower() != ".json":
                    continue
                found.append(entry)
        except OSError:
            pass
        return found

    # Kaynaklar: üst düzey trash/*.json + trash/tasks/*.json (task_*.json dahil).
    collected = _collect_json_files(trash_dir)
    tasks_subdir = trash_dir / "tasks"
    if tasks_subdir.is_dir():
        collected.extend(_collect_json_files(tasks_subdir))
    try:
        paths = sorted(collected, key=lambda x: x.stat().st_mtime, reverse=True)
    except OSError:
        paths = collected
    for p in paths:
        try:
            if not p.is_file():
                continue
            if p.name.endswith(".tmp"):
                continue
            if p.suffix.lower() != ".json":
                continue
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            pl = raw.get("payload")
            payload = pl if isinstance(pl, dict) else None
            if payload is not None:
                tid = str(
                    payload.get("id")
                    or payload.get("taskId")
                    or raw.get("id")
                    or raw.get("taskId")
                    or p.stem
                ).strip() or p.stem
                name = str(
                    payload.get("title")
                    or payload.get("name")
                    or payload.get("text")
                    or raw.get("title")
                    or raw.get("text")
                    or ""
                ).strip()
                status = str(payload.get("status") or raw.get("status") or "").strip()
            else:
                tid = str(raw.get("id") or raw.get("taskId") or p.stem).strip() or p.stem
                name = str(raw.get("title") or raw.get("name") or raw.get("text") or "").strip()
                status = str(raw.get("status") or "").strip()
            if not name:
                name = p.stem
            st = p.stat()
            mtime_iso = _mtime_iso(st)
            if last_mtime is None or st.st_mtime > last_mtime:
                last_mtime = st.st_mtime
            top_del = str(raw.get("deleted_at", "") or raw.get("deletedAt", "")).strip()
            if not top_del and payload is not None:
                top_del = str(payload.get("deleted_at") or payload.get("deletedAt") or "").strip()
            deleted_at = top_del if top_del else mtime_iso
            moved_at = top_del if top_del else mtime_iso
            original_path = "—"
            if payload is not None:
                op = payload.get("original_path")
                if op is None:
                    op = payload.get("originalPath")
                if op is not None and str(op).strip():
                    original_path = str(op).strip()
            if not status:
                status = "—"
            item = {
                "id": tid,
                "task_id": tid,
                "name": name,
                "status": status,
                "deleted_at": deleted_at,
                "original_path": original_path,
                "trash_path": str(p.resolve()),
                "moved_at": moved_at,
                "scope": "tasks",
            }
            if payload is not None:
                item["payload"] = payload
            item["raw_record"] = raw
            print("TRASH ITEM:", json.dumps(item, ensure_ascii=False), flush=True)
            items.append(item)
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
        "Consent (kimlik/keystore rızası) kayıtlı."
        if consent
        else "Consent henüz kayıtlı değil; hassas yüzeyler kısıtlı kalır."
    )
    ga_active = bool(guidance.get("general_approval_active"))
    gen = system_health.get("general") if isinstance(system_health.get("general"), dict) else {}
    gen_note = (gen.get("note") or "").strip()
    summary = (
        f"Şu an mod {mode_tr}. Yazım hedefi {writing_tr}. {consent_tr}"
    )
    if ga_active:
        summary += " Genel onay (kisitli_otonom yazma kapısı) bu oturumda açık."
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

    consent_state = str(guidance.get("consent_state") or "").strip()
    if consent_state:
        consent_line = f"Consent: {consent_state}."
    else:
        consent_line = (
            "Consent: kayıtlı."
            if consent
            else "Consent: bekleniyor."
        )
    ga_line = (
        "Genel onay: bu oturumda açık (kisitli_otonom yazma kapısı)."
        if ga_active
        else "Genel onay: kapalı."
    )
    session_unlocked = guidance.get("session_unlocked")
    session_line = ""
    if session_unlocked is True:
        session_line = " Oturum kilidi: açık (runtime sinyali)."
    elif session_unlocked is False:
        session_line = " Oturum kilidi: kilitli (runtime sinyali)."

    iden = str(identity_payload.get("identity_state") or "—").strip()
    ks_init = str(keystore_payload.get("keystore_state") or "—").strip()
    ks = f"keystore dosyası {ks_init}"
    te = system_health.get("task_engine") if isinstance(system_health.get("task_engine"), dict) else {}
    te_note = str(te.get("note") or "—").strip()
    tc = int(tasks_payload.get("task_count") or 0)
    tfe = bool(tasks_payload.get("tasks_file_exists"))

    understood: list[str] = [
        f"Mod: {mode_tr}.",
        consent_line + session_line,
        ga_line,
        f"Kimlik dosyası: {iden}.",
        f"Anahtar kasası ({ks}).",
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


def _core_active() -> bool:
    try:
        import core.workspace_contract  # noqa: F401
        return True
    except Exception:
        return False


def _panel_keystore_initialized(base: Path, keystore_path: Path | None) -> bool:
    """ADR-011: keystore_ready — dosya/init sinyali (passphrase unlock değil)."""
    try:
        from security.keystore import FileKeyStore

        return FileKeyStore(base_dir=str(base)).is_initialized()
    except Exception:
        return bool(keystore_path and keystore_path.is_file())


_PANEL_SESSION_UNLOCKED_NOTE = (
    "Panel köprüsü runtime oturum kilidini (session_unlocked) bu okuma yolunda doğrulamaz."
)


def _build_lumos_status(
    *,
    is_sandbox: bool,
    writing_label: str,
    bridge_built_at: str,
) -> dict:
    """Tek panel durum kaynağı: çekirdek + ENV + kando runtime (bellek)."""
    from core.runtime_state import get_kando_runtime

    snap = get_kando_runtime()
    mode = (os.environ.get("LUMOS_MODE") or "offline").strip().lower()
    mode = "online" if mode == "online" else "offline"
    pending_s = "Yok"
    if snap and snap.get("pending"):
        pend = snap["pending"]
        if isinstance(pend, dict) and pend:
            pending_s = "; ".join(f"{k}={v}" for k, v in pend.items())
        else:
            pending_s = str(pend)
    last_repo = "—"
    if snap:
        lr = (snap.get("last_repo_query") or "").strip()
        if lr:
            last_repo = lr
    preview = "—"
    if snap and (snap.get("last_output_preview") or "").strip():
        preview = str(snap["last_output_preview"]).strip()
        if len(preview) > 220:
            preview = preview[:220] + "…"
    ctx_s = "Boş"
    if snap and (snap.get("context_summary") or "").strip():
        ctx_s = str(snap["context_summary"]).strip()
        if len(ctx_s) > 280:
            ctx_s = ctx_s[:280] + "…"
    nav = snap.get("repo_nav") if snap and isinstance(snap.get("repo_nav"), dict) else {}
    rc = int(nav.get("results_count", 0) or 0)
    ci = int(nav.get("cursor_index", 0) or 0)
    if rc > 0:
        repo_nav_s = f"{rc} blok, imleç {ci + 1}/{rc}"
    else:
        repo_nav_s = "Sonuç listesi yok"
    snap_ts = (snap.get("updated_at") if snap else None) or "—"
    snap_note = (
        "Kando bu süreçte henüz güncellenmedi (runtime boş)."
        if snap_ts == "—"
        else f"Kando runtime: {snap_ts}"
    )
    return {
        "core_active": _core_active(),
        "online_mode": mode,
        "sandbox_mode": is_sandbox,
        "writing_base_dir": writing_label,
        "panel_bridge_built_at": bridge_built_at,
        "state_inject_note": "Canlı: GET /lumos-read-state (panel_tasks_server). İlk yükleme: state_inject.js.",
        "last_repo_query": last_repo,
        "pending_flow": pending_s,
        "last_output_preview": preview,
        "context_summary": ctx_s,
        "repo_navigation": repo_nav_s,
        "kando_snapshot_at": snap_ts,
        "kando_snapshot_note": snap_note,
    }


def build_panel_read_state(*, repo_root: Path | None = None) -> dict:
    """Depo kökü (lumos_decision_history.jsonl yolu için); verilmezse bu dosyanın repo kökü."""
    repo = repo_root if repo_root is not None else Path(__file__).resolve().parent.parent.parent
    base = _base_dir()
    is_sandbox = _is_sandbox_mode()
    bridge_built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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

    gate = task_actions_gate()
    dashboard = {
        "sandbox_mode": is_sandbox,
        "writing_base_dir": writing_label,
        "guard_status": "KORUMA AKTİF",
        "recent_events": [],
        "warnings": [gate["reason"]] if gate.get("reason") else [],
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
            system_health[key] = {
                "status": general_status,
                "note": "consent_ok dosya tabanlı; keystore init ve oturum kilidi ayrı sinyaller.",
            }
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
    engine_tasks_path = base / "tasks" / "tasks.json"
    system_paths["tasks"] = _safe_resolve_path(tasks_path) if tasks_path else None
    system_paths["panel_tasks"] = system_paths["tasks"]
    system_paths["task_engine_tasks"] = _safe_resolve_path(engine_tasks_path) if engine_tasks_path else None

    panel_store_status, _ = _panel_tasks_store_health(base)
    engine_store_status, _ = _task_engine_store_health(base)

    # Çekirdek dosya özeti (zaten okunan tasks/trash/logs/config sinyallerinin dar yansıması)
    system_summary = {
        "config_exists": config_path.is_file() if config_path else False,
        "tasks_file_exists": tasks_payload.get("tasks_file_exists", False),
        "task_count": tasks_payload.get("task_count", 0),
        "panel_tasks_store_ok": panel_store_status == "ok",
        "task_engine_store_ok": engine_store_status == "ok",
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

    # Keystore: read-only — keystore init dosyası + consent vekili ayrı; passphrase/ifşa yok
    keystore_last = _file_mtime_iso(keystore_path) if keystore_path else None
    ks_initialized = _panel_keystore_initialized(base, keystore_path)
    general_approval_active = _panel_general_approval()
    consent_state = "kayıtlı" if consent else "bekleniyor"
    keystore_payload = {
        "keystore_ready": ks_initialized,
        "keystore_state": "hazır" if ks_initialized else "eksik",
        "consent_ok": consent,
        "consent_state": consent_state,
        "general_approval_active": general_approval_active,
        "session_unlocked": None,
        "session_unlocked_note": _PANEL_SESSION_UNLOCKED_NOTE,
        "keystore_last_update": keystore_last,
        "keystore_write_scope": "Kilit açılmadan hassas yazım yapılmaz",
        "display_note": (
            "consent_ok = consent.json; general_approval_active = LUMOS_GENERAL_APPROVAL env; "
            "session_unlocked bu köprüde doğrulanmaz (ADR-010)."
        ),
    }

    # Guidance: consent (dosya) ve genel onay (env) ayrı; runtime session_unlocked yok
    mode = (os.environ.get("LUMOS_MODE") or "offline").strip().lower()
    mode = "online" if mode == "online" else "offline"
    guidance = {
        "mode": mode,
        "consent": consent,
        "consent_ok": consent,
        "consent_state": consent_state,
        "general_approval_active": general_approval_active,
        "session_unlocked": None,
        "session_unlocked_note": _PANEL_SESSION_UNLOCKED_NOTE,
        "blocked_reason": None,
        "next_step": None,
        "codex_warning": _CODEX_PANEL_WARNING,
        "task_actions_gate": gate,
    }

    yanit_payload = _build_yanit_card_payload(
        repo_root=repo,
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
        "lumos_status": _build_lumos_status(
            is_sandbox=is_sandbox,
            writing_label=writing_label,
            bridge_built_at=bridge_built_at,
        ),
    }

# lumos:instruction-pipeline safe touch

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)
