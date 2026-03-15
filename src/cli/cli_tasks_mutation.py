"""Task mutation CLI handlers for Lumos core.

Extracted from main.py for stabilization. Handles task creation, update/cancel,
archive, and delete flows only. No lock/presence, security-sensitive, or
workspace_contract logic; main.py remains the single entry router.
"""
from __future__ import annotations

from typing import Any, Callable

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


def handle_task_mutation(route: str, args: list[str], ctx: TaskMutationContext) -> bool:
    """Handle task mutation routes. Returns True if the route was handled, False otherwise."""
    if route == "gorev_olustur":
        desc = (args[0] if args else "").strip()
        if not desc:
            print("Kullanım: görev oluştur <açıklama>")
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
        t = ctx.task_store.create(title=desc[:80], description=desc, permission_profile=profile)
        print(f"Görev {t.task_id} oluşturuldu: {t.title}")
        task_engine = TaskEngine(
            ctx.task_store, profile, ctx.general_approval[0], base_dir=ctx.base_dir,
            observation_engine=getattr(ctx, "event_recording_engine", None),
        )
        ctx.current_task[0] = "görev yürütülüyor."
        try:
            ok, msg = task_engine.run_task(t.task_id)
            print(msg)
            ctx.last_action[0] = f"Görev {t.task_id} oluşturulup yürütüldü: {t.title}"
            ctx.record_today_action(ctx.last_action[0])
        finally:
            ctx.current_task[0] = None
        return True

    if route == "gorev_iptal":
        id_str = (args[0] if args else "").strip()
        if not id_str:
            print("Kullanım: görev iptal <id>")
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
