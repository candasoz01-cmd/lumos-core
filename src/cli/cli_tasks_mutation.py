"""Task mutation CLI handlers for Lumos core.

Extracted from main.py for stabilization. Handles task creation, update/cancel,
archive, and delete flows only. No lock/presence, security-sensitive, or
workspace_contract logic; main.py remains the single entry router.
"""
from __future__ import annotations

from typing import Any, Callable

from core.brain import run as brain_run
from core.startup_health import effective_consent
from policy.action_policy import (
    CANCEL_TASK,
    CREATE_TASK,
    DELETE_TASK,
    check_policy,
    log_policy_blocked,
    policy_user_message,
)
from policy.confirmation_policy import (
    REASON_CONFIRMATION_EXPIRED,
    REASON_CONFIRMATION_REQUIRED,
    REASON_SCOPE_MISMATCH,
    cli_mutation_confirmation_spec,
    ensure_cli_mutation_confirmation,
    format_cli_confirmation_message,
    is_confirmation_enabled,
    request_confirmation,
    requires_confirmation_for_action,
)
from task_engine import TaskEngine, find_recent_similar_task


class TaskMutationContext:
    """Context for task mutation handlers. Main builds this; handlers mutate task state and update tracking refs."""

    base_dir: str
    task_store: Any
    current_permission_profile: list
    general_approval: list
    session_consent: list
    current_task: list
    last_action: list
    today_date: list
    today_actions: list
    last_task_create_fingerprint: list
    record_today_action: Callable[[str], None]
    event_recording_engine: Any = None  # ObservationEngine | None: record execution/verification events
    pending_intent: list = None  # [dict | None]: clarification flow — intent + missing_param
    pending_action: list = None  # [dict | None]: consent flow — blocked task_id + goal
    pending_confirmation: list[dict[str, Any]] | None = None  # CU4 confirmation resume entries
    # Policy snapshot (set by lumos_runtime.create_runtime)
    policy_runtime_mode: str = "offline"
    policy_is_locked: Any = None  # Callable[[], bool] | None


def _session_consent_from_mut_ctx(ctx: TaskMutationContext) -> bool:
    sc = getattr(ctx, "session_consent", None)
    return bool(sc and len(sc) > 0 and sc[0])


def _task_mutation_policy_context(ctx: TaskMutationContext):
    online = getattr(ctx, "policy_runtime_mode", "offline") == "online"
    locked = True
    fn = getattr(ctx, "policy_is_locked", None)
    if callable(fn):
        try:
            locked = bool(fn())
        except Exception:
            locked = True
    consent = effective_consent(ctx.base_dir, _session_consent_from_mut_ctx(ctx))
    general_approval = bool(ctx.general_approval[0])
    return {
        "online": online,
        "koruma_active": locked,
        "consent": consent,
        "general_approval": general_approval,
    }


def _enforce_task_policy(ctx: TaskMutationContext, action: str) -> bool:
    """Returns True if allowed; False if blocked (already printed + logged)."""
    pr = check_policy(action, _task_mutation_policy_context(ctx))
    if pr.allowed:
        return True
    print(policy_user_message(action, pr.reason))
    log_policy_blocked(ctx.base_dir, action, pr.reason)
    return False


def _pending_confirmation_list(ctx: TaskMutationContext) -> list[dict[str, Any]]:
    if ctx.pending_confirmation is None:
        ctx.pending_confirmation = []
    return ctx.pending_confirmation


def _confirmation_block_message(reason: str) -> str:
    if reason == REASON_CONFIRMATION_EXPIRED:
        return "Onay süresi doldu. İşlemi tekrar başlat."
    if reason == REASON_SCOPE_MISMATCH:
        return "Onay kapsamı eşleşmiyor."
    return "Onay gerekli."


def _store_pending_confirmation(
    ctx: TaskMutationContext,
    *,
    confirmation_id: str,
    action_key: str,
    scope: dict[str, Any],
    route: str,
    args: list[str],
) -> None:
    _pending_confirmation_list(ctx).append(
        {
            "confirmation_id": confirmation_id,
            "action_key": action_key,
            "scope": dict(scope),
            "route": route,
            "args": list(args),
        }
    )


def _remove_pending_confirmation(ctx: TaskMutationContext, confirmation_id: str) -> None:
    pending = _pending_confirmation_list(ctx)
    ctx.pending_confirmation = [
        p for p in pending if str(p.get("confirmation_id") or "") != confirmation_id
    ]


def _find_pending_confirmation(ctx: TaskMutationContext, confirmation_id: str) -> dict[str, Any] | None:
    for entry in _pending_confirmation_list(ctx):
        if str(entry.get("confirmation_id") or "") == confirmation_id:
            return entry
    return None


def _request_cli_mutation_confirmation(
    ctx: TaskMutationContext,
    route: str,
    args: list[str],
) -> bool:
    """Confirmation aktifken grant oluşturur; True = persist ertelendi."""
    if not is_confirmation_enabled():
        return False
    spec = cli_mutation_confirmation_spec(route, args)
    if spec is None:
        return False
    action_key, scope, preview = spec
    if not requires_confirmation_for_action(action_key):
        return False
    pending = request_confirmation(
        action_key,
        scope,
        preview,
        base_dir=ctx.base_dir,
    )
    _store_pending_confirmation(
        ctx,
        confirmation_id=pending.confirmation_id,
        action_key=action_key,
        scope=scope,
        route=route,
        args=args,
    )
    print(format_cli_confirmation_message(pending.preview, pending.confirmation_id))
    return True


def _execute_gorev_olustur(desc: str, ctx: TaskMutationContext) -> None:
    profile = ctx.current_permission_profile[0]
    fingerprint = (profile, desc)
    similar = find_recent_similar_task(ctx.task_store.list_all(), desc, profile)
    if similar and ctx.last_task_create_fingerprint[0] != fingerprint:
        ctx.last_task_create_fingerprint[0] = fingerprint
        print(
            f"Benzer bir görev zaten var: {similar.task_id}. "
            "İstersen önce onu inceleyebilirsin (görev durumu/özeti/adımları). "
            "Aynı komutu tekrar yazarsan yeni görev oluştururum."
        )
        return
    ctx.last_task_create_fingerprint[0] = None
    ctx.current_task[0] = "görev yürütülüyor."
    try:
        result = brain_run(
            desc,
            ctx.task_store,
            ctx.base_dir,
            profile,
            ctx.general_approval[0],
            observation_engine=getattr(ctx, "event_recording_engine", None),
        )
        print(result.human_readable_summary)
        pl = getattr(result, "pipeline", None)
        if pl:
            from core.patch_pipeline_lifecycle import format_pipeline_summary_line

            print(format_pipeline_summary_line(pl))
        ctx.last_action[0] = f"Görev {result.task_id} oluşturulup yürütüldü: {result.goal[:80]}"
        ctx.record_today_action(ctx.last_action[0])
    finally:
        ctx.current_task[0] = None


def _execute_gorev_sil(tid: int, ctx: TaskMutationContext) -> None:
    if ctx.task_store.move_to_trash(tid):
        print(f"Görev {tid} çöpe taşındı (geri alınabilir).")
    else:
        print("Silinecek görev bulunamadı.")


def handle_confirmation_approve(confirmation_id: str, ctx: TaskMutationContext) -> bool:
    """onayla <id> — grant tüket ve bekleyen mutasyonu yürüt."""
    cid = (confirmation_id or "").strip()
    if not cid:
        print("Kullanım: onayla <confirmation_id>")
        return True
    if not is_confirmation_enabled():
        print("Confirmation devre dışı.")
        return True
    pending = _find_pending_confirmation(ctx, cid)
    if pending is None:
        print("Bekleyen onay bulunamadı veya süresi dolmuş.")
        return True
    action_key = str(pending.get("action_key") or "")
    scope = pending.get("scope")
    if not isinstance(scope, dict):
        print("Bekleyen onay kaydı geçersiz.")
        return True
    conf = ensure_cli_mutation_confirmation(
        action_key,
        scope,
        cid,
        base_dir=ctx.base_dir,
    )
    if not conf.allowed:
        print(_confirmation_block_message(conf.reason or REASON_CONFIRMATION_REQUIRED))
        return True
    route = str(pending.get("route") or "")
    args = pending.get("args")
    if not isinstance(args, list):
        args = []
    _remove_pending_confirmation(ctx, cid)
    if route == "gorev_olustur":
        desc = (args[0] if args else "").strip()
        if not desc:
            print("Onaylanan görev oluşturma kaydı eksik.")
            return True
        if not _enforce_task_policy(ctx, CREATE_TASK):
            return True
        _execute_gorev_olustur(desc, ctx)
        return True
    if route == "gorev_sil":
        id_str = (args[0] if args else "").strip()
        try:
            tid = int(id_str)
        except ValueError:
            print("Onaylanan görev silme kaydı geçersiz.")
            return True
        if not _enforce_task_policy(ctx, DELETE_TASK):
            return True
        _execute_gorev_sil(tid, ctx)
        return True
    print("Bekleyen onay için bilinmeyen rota.")
    return True


def handle_confirmation_cancel(args: list[str], ctx: TaskMutationContext) -> bool:
    """onay iptal [confirmation_id] — bekleyen CU4 onayını iptal et."""
    pending = _pending_confirmation_list(ctx)
    if not pending:
        print("Bekleyen onay yok.")
        return True
    if args:
        cid = (args[0] or "").strip()
        before = len(pending)
        ctx.pending_confirmation = [
            p for p in pending if str(p.get("confirmation_id") or "") != cid
        ]
        if len(ctx.pending_confirmation) == before:
            print("Bekleyen onay bulunamadı.")
        else:
            print(f"Onay iptal edildi: {cid}")
        return True
    ctx.pending_confirmation = []
    print("Tüm bekleyen onaylar iptal edildi.")
    return True


def handle_task_mutation(route: str, args: list[str], ctx: TaskMutationContext) -> bool:
    """Handle task mutation routes. Returns True if the route was handled, False otherwise."""
    if route == "gorev_olustur":
        desc = (args[0] if args else "").strip()
        if not desc:
            print("Kullanım: görev oluştur <açıklama>")
            return True
        if not _enforce_task_policy(ctx, CREATE_TASK):
            return True
        if _request_cli_mutation_confirmation(ctx, route, args):
            return True
        _execute_gorev_olustur(desc, ctx)
        return True

    if route == "gorev_iptal":
        id_str = (args[0] if args else "").strip()
        if not id_str:
            print("Kullanım: görev iptal <id>")
            return True
        if not _enforce_task_policy(ctx, CANCEL_TASK):
            return True
        try:
            tid = int(id_str)
        except ValueError:
            print("Geçerli bir görev id yaz.")
            return True
        task_engine = TaskEngine(
            ctx.task_store,
            ctx.current_permission_profile[0],
            ctx.general_approval[0],
            base_dir=ctx.base_dir,
            observation_engine=getattr(ctx, "event_recording_engine", None),
        )
        ok, msg = task_engine.cancel_task(tid)
        print(msg)
        return True

    if route == "gorev_temizle_tamamlananlar":
        count = ctx.task_store.archive_completed()
        if count == 0:
            print("Arşivlenecek tamamlanmış görev yok.")
        else:
            print(f"{count} tamamlanmış görevi arşive taşıdım.")
        return True

    if route == "gorev_temizle_simulasyonlar":
        count = ctx.task_store.archive_simulations()
        if count == 0:
            print("Arşivlenecek simülasyon görevi yok.")
        else:
            print(f"{count} simülasyon görevi arşive taşıdım.")
        return True

    if route == "gorev_arsivle":
        id_str = (args[0] if args else "").strip()
        if not id_str:
            print("Kullanım: görev arşivle <id>")
            return True
        try:
            tid = int(id_str)
        except ValueError:
            print("Geçerli bir görev id yaz.")
            return True
        if ctx.task_store.archive(tid):
            print(f"Görev {tid} arşive taşındı (silinmedi).")
        else:
            print("Görev bulunamadı veya zaten arşivde.")
        return True

    if route == "gorev_sil":
        id_str = (args[0] if args else "").strip()
        if not id_str:
            print("Kullanım: görev sil <id>")
            return True
        if not _enforce_task_policy(ctx, DELETE_TASK):
            return True
        try:
            tid = int(id_str)
        except ValueError:
            print("Geçerli bir görev id yaz.")
            return True
        if _request_cli_mutation_confirmation(ctx, route, args):
            return True
        _execute_gorev_sil(tid, ctx)
        return True

    return False
