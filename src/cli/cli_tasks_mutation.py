"""Task mutation CLI handlers for Lumos core.

Extracted from main.py for stabilization. Handles task creation, update/cancel,
archive, and delete flows only. No lock/presence, security-sensitive, or
workspace_contract logic; main.py remains the single entry router.
"""
from __future__ import annotations

from typing import Any, Callable

from core.brain import run as brain_run
from policy.action_policy import (
    CANCEL_TASK,
    CREATE_TASK,
    DELETE_TASK,
    check_policy,
    log_policy_blocked,
    policy_user_message,
)
from task_engine import TaskEngine, find_recent_similar_task


class TaskMutationContext:
    """Context for task mutation handlers. Main builds this; handlers mutate task state and update tracking refs."""

    base_dir: str
    task_store: Any
    current_permission_profile: list
    general_approval: list
    current_task: list
    last_action: list
    today_date: list
    today_actions: list
    last_task_create_fingerprint: list
    record_today_action: Callable[[str], None]
    event_recording_engine: Any = None  # ObservationEngine | None: record execution/verification events
    pending_intent: list = None  # [dict | None]: clarification flow — intent + missing_param
    pending_action: list = None  # [dict | None]: consent flow — blocked task_id + goal
    # Policy snapshot (set by lumos_runtime.create_runtime)
    policy_runtime_mode: str = "offline"
    policy_is_locked: Any = None  # Callable[[], bool] | None


def _task_mutation_policy_context(ctx: TaskMutationContext):
    online = getattr(ctx, "policy_runtime_mode", "offline") == "online"
    locked = True
    fn = getattr(ctx, "policy_is_locked", None)
    if callable(fn):
        try:
            locked = bool(fn())
        except Exception:
            locked = True
    consent = bool(ctx.general_approval[0])
    return {"online": online, "koruma_active": locked, "consent": consent}


def _enforce_task_policy(ctx: TaskMutationContext, action: str) -> bool:
    """Returns True if allowed; False if blocked (already printed + logged)."""
    pr = check_policy(action, _task_mutation_policy_context(ctx))
    if pr.allowed:
        return True
    print(policy_user_message(action, pr.reason))
    log_policy_blocked(ctx.base_dir, action, pr.reason)
    return False


def handle_task_mutation(route: str, args: list[str], ctx: TaskMutationContext) -> bool:
    """Handle task mutation routes. Returns True if the route was handled, False otherwise."""
    if route == "gorev_olustur":
        desc = (args[0] if args else "").strip()
        if not desc:
            print("Kullanım: görev oluştur <açıklama>")
            return True
        if not _enforce_task_policy(ctx, CREATE_TASK):
            return True
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
            return True
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
        # Sözleşme: kalıcı silme öncesi tek satır uyarı (geri alınamaz).
        print("Dikkat: Bu görev kalıcı silinecek, geri alınamaz.")
        if ctx.task_store.delete(tid, user_initiated=True):
            print("Görev silindi.")
        else:
            print("Silinecek görev bulunamadı.")
        return True

    return False
