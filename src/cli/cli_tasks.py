"""Read-only task CLI handlers for Lumos core.

Extracted from cli_readonly for stabilization. Handles only task list/view/summary/steps/counter;
no task creation, mutation, engine writes, or security-sensitive flows.
"""
from __future__ import annotations

from typing import Any, Protocol


def _task_block_line(task: Any) -> str | None:
    """If task has a blocking reason, return one line for display (görev durumu / görev özeti)."""
    from task_engine.diagnostics import format_task_block_line
    return format_task_block_line(task)


class _TaskReadOnlyContext(Protocol):
    """Minimal context for read-only task handlers. Avoids coupling to ReadOnlyContext."""

    task_store: Any


def handle_tasks_readonly(route: str, args: list[str], ctx: _TaskReadOnlyContext) -> bool:
    """Handle read-only task routes. Returns True if the route was handled, False otherwise."""
    if route == "gorevler":
        tasks = ctx.task_store.list_all()
        if not tasks:
            print("Kayıtlı görev yok.")
        else:
            from task_engine import compute_task_stats, format_task_stats_line
            stats = compute_task_stats(tasks)
            print(format_task_stats_line(stats))
            for t in tasks:
                status_label = t.status
                if getattr(t, "archived", False):
                    status_label = f"{status_label} (arşiv)"
                print(f"  {t.task_id}: {t.title} — {status_label}")
        return True
    if route == "gorev_durumu":
        id_str = (args[0] if args else "").strip()
        if not id_str:
            print("Kullanım: görev durumu <id>")
            return True
        try:
            tid = int(id_str)
        except ValueError:
            print("Geçerli bir görev id yaz.")
            return True
        t = ctx.task_store.get(tid)
        if not t:
            print("Görev bulunamadı.")
            return True
        print(f"Görev {t.task_id}: {t.title}")
        print(f"  Durum: {t.status} | Profil: {t.permission_profile} | Oluşturulma: {t.created_at}")
        block_line = _task_block_line(t)
        if block_line:
            print(f"  {block_line}")
        elif t.error_summary:
            print(f"  Hata: {t.error_summary}")
        return True
    if route == "gorev_adimlari":
        id_str = (args[0] if args else "").strip()
        if not id_str:
            print("Kullanım: görev adımları <id>")
            return True
        try:
            tid = int(id_str)
        except ValueError:
            print("Geçerli bir görev id yaz.")
            return True
        t = ctx.task_store.get(tid)
        if not t:
            print("Görev bulunamadı.")
            return True
        print(f"Görev {t.task_id}: {t.title} — adımlar:")
        for i, s in enumerate(t.steps, 1):
            rk = getattr(s, "result_kind", "") or "-"
            line = f"  {i}. [{s.status}] sonuç: {rk} — {s.title}"
            if getattr(s, "error", ""):
                line += f" | Engel: {s.error}"
            print(line)
        return True
    if route == "gorev_ozeti":
        id_str = (args[0] if args else "").strip()
        if not id_str:
            print("Kullanım: görev özeti <id>")
            return True
        try:
            tid = int(id_str)
        except ValueError:
            print("Geçerli bir görev id yaz.")
            return True
        t = ctx.task_store.get(tid)
        if not t:
            print("Görev bulunamadı.")
            return True
        total_steps = len(t.steps)
        completed_steps = sum(1 for s in t.steps if s.status == "tamamlandi")
        verified = getattr(t, "verified_count", 0)
        unverified = getattr(t, "unverified_count", 0)
        simulation = getattr(t, "simulation_count", 0)
        parts = [
            f"Toplam adım: {total_steps}",
            f"Tamamlanan adım: {completed_steps}",
            f"Doğrulanan adım: {verified}",
            f"Doğrulanamayan adım: {unverified}",
            f"Simülasyon adım: {simulation}",
            f"Son durum: {t.status}",
        ]
        if getattr(t, "elapsed_seconds", 0) > 0:
            parts.append(f"Geçen süre: {t.elapsed_seconds:.1f}s")
        block_line = _task_block_line(t)
        if block_line:
            parts.append(block_line)
        short_result = (t.description or "")[:80]
        if len(t.description or "") > 80:
            short_result += "..."
        parts.append(f"Kısa sonuç: {short_result or '(yok)'}")
        print("\n".join(parts))
        return True
    if route == "gorev_sayac":
        from task_engine import compute_task_stats, format_task_stats_line
        stats = compute_task_stats(ctx.task_store.list_all())
        print(format_task_stats_line(stats))
        return True
    return False
