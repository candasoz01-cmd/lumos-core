"""Read-only CLI command handlers for Lumos core.

Extracted from main.py for stabilization. Handles only display/list/status flows;
no write paths, no security-sensitive or task-mutation logic.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Callable

from cli.cli_parse import (
    HELP_ETIKETLER_TEXT,
    HELP_GORUNTULEME_TEXT,
    HELP_GUVENLIK_TEXT,
    HELP_KISA_TEXT,
    HELP_TEMEL_TEXT,
    HELP_TEXT,
    KISACA_ANLAT_SHORT_THRESHOLD,
    REHBER_TEXT,
    _format_neden_cevap,
    _format_today_bullet,
    _get_en_onemli_eksik,
    _get_guvenli_cevap,
    _get_mod_cevabi,
    _get_oneri,
    _get_tek_sonraki_adim,
    _shorten_previous_response,
)


class ReadOnlyContext:
    """Context passed to read-only handlers. Main builds this; handlers only read and update response tracking."""

    base_dir: str
    state: Any
    ks: Any
    pl: Any
    mode: str
    engine: Any
    saved_notes: list
    note_ops_history: list
    last_response_reason: list
    last_action: list
    last_response_text: list
    today_date: list
    today_actions: list
    current_task: list
    current_permission_profile: list
    task_store: Any
    aliases: dict
    record_note_op: Callable[[str], None]
    record_today_action: Callable[[str], None]


def handle_readonly(route: str, args: list[str], ctx: ReadOnlyContext) -> bool:
    """Handle read-only routes. Returns True if the route was handled, False otherwise."""
    # ---- Help ----
    if route == "help":
        ctx.last_response_reason[0] = "komut listesini istedin"
        ctx.last_action[0] = "En son yardım listesini gösterdim."
        ctx.record_today_action(ctx.last_action[0])
        ctx.last_response_text[0] = HELP_TEXT
        print(HELP_TEXT)
        return True
    if route == "help_etiketler":
        ctx.last_response_reason[0] = "etiket komutlarını istedin"
        ctx.last_action[0] = "En son etiket yardımını gösterdim."
        ctx.record_today_action(ctx.last_action[0])
        ctx.last_response_text[0] = HELP_ETIKETLER_TEXT
        print(HELP_ETIKETLER_TEXT)
        return True
    if route == "help_temel":
        ctx.last_response_reason[0] = "temel komutları istedin"
        ctx.last_action[0] = "En son temel yardımını gösterdim."
        ctx.record_today_action(ctx.last_action[0])
        ctx.last_response_text[0] = HELP_TEMEL_TEXT
        print(HELP_TEMEL_TEXT)
        return True
    if route == "help_guvenlik":
        ctx.last_response_reason[0] = "güvenlik komutlarını istedin"
        ctx.last_action[0] = "En son güvenlik yardımını gösterdim."
        ctx.record_today_action(ctx.last_action[0])
        ctx.last_response_text[0] = HELP_GUVENLIK_TEXT
        print(HELP_GUVENLIK_TEXT)
        return True
    if route == "help_kisa":
        ctx.last_response_reason[0] = "kısa yardımı istedin"
        ctx.last_action[0] = "En son kısa yardımı gösterdim."
        ctx.record_today_action(ctx.last_action[0])
        ctx.last_response_text[0] = HELP_KISA_TEXT
        print(HELP_KISA_TEXT)
        return True
    if route == "help_goruntuleme":
        ctx.last_response_reason[0] = "görüntüleme komutlarını istedin"
        ctx.last_action[0] = "En son görüntüleme yardımını gösterdim."
        ctx.record_today_action(ctx.last_action[0])
        ctx.last_response_text[0] = HELP_GORUNTULEME_TEXT
        print(HELP_GORUNTULEME_TEXT)
        return True
    if route == "rehber":
        ctx.last_response_reason[0] = "rehberi istedin"
        ctx.last_action[0] = "En son yardım rehberini gösterdim."
        ctx.record_today_action(ctx.last_action[0])
        ctx.last_response_text[0] = REHBER_TEXT
        print(REHBER_TEXT)
        return True

    # ---- Status / öneri / güvenlik (read-only) ----
    if route == "onerir":
        oneriler = _get_oneri(ctx.base_dir, ctx.ks.is_initialized(), ctx.pl)
        for o in oneriler:
            print(o)
        ctx.last_response_reason[0] = (oneriler[0].rstrip(".") if oneriler and oneriler[0] else None)
        ctx.last_action[0] = "En son sonraki adım önerisini verdim."
        ctx.last_response_text[0] = "\n".join(oneriler) if oneriler else None
        ctx.record_today_action(ctx.last_action[0])
        return True
    if route == "sonraki_adim":
        step = _get_tek_sonraki_adim(ctx.base_dir, ctx.ks.is_initialized(), ctx.pl)
        print(step)
        ctx.last_response_reason[0] = step.replace("Bir sonraki adım: ", "").strip() if step.startswith("Bir sonraki adım:") else step
        ctx.last_action[0] = "En son tek sonraki adımı söyledim."
        ctx.last_response_text[0] = step
        ctx.record_today_action(ctx.last_action[0])
        return True
    if route == "guvenli_miyim":
        resp = _get_guvenli_cevap(ctx.base_dir, ctx.ks.is_initialized(), ctx.pl)
        print(resp)
        ctx.last_response_reason[0] = resp.split(". ", 1)[1].strip().rstrip(".") if ". " in resp else resp
        ctx.last_action[0] = "En son güvenlik cevabını verdim."
        ctx.last_response_text[0] = resp
        ctx.record_today_action(ctx.last_action[0])
        return True
    if route == "en_onemli_eksik":
        resp = _get_en_onemli_eksik(ctx.base_dir, ctx.ks.is_initialized(), ctx.pl)
        print(resp)
        ctx.last_response_reason[0] = resp
        ctx.last_action[0] = "En son tek kritik eksiği söyledim."
        ctx.last_response_text[0] = resp
        ctx.record_today_action(ctx.last_action[0])
        return True
    if route == "hangi_moddayim":
        resp = _get_mod_cevabi(ctx.mode, ctx.base_dir, ctx.ks.is_initialized(), ctx.pl)
        print(resp)
        ctx.last_response_reason[0] = resp
        ctx.last_action[0] = "En son mod cevabını verdim."
        ctx.last_response_text[0] = resp
        ctx.record_today_action(ctx.last_action[0])
        return True
    if route == "neden_boyle":
        ned_cevap = _format_neden_cevap(ctx.last_response_reason[0])
        print(ned_cevap)
        ctx.last_action[0] = "En son önceki cevabın gerekçesini söyledim."
        ctx.last_response_text[0] = ned_cevap
        ctx.record_today_action(ctx.last_action[0])
        return True
    if route == "kisaca_anlat":
        prev = (ctx.last_response_text[0] or "").strip()
        if not prev or len(prev) < KISACA_ANLAT_SHORT_THRESHOLD:
            out_short = "Zaten kısa söyledim."
            print(out_short)
        else:
            out_short = _shorten_previous_response(prev)
            print(out_short)
        ctx.last_response_reason[0] = "kısaca anlat dedin"
        ctx.last_action[0] = "En son önceki cevabı kısaca özetledim."
        ctx.last_response_text[0] = out_short
        ctx.record_today_action(ctx.last_action[0])
        return True

    # ---- Yetki profili: display only (no args or empty args) ----
    if route == "yetki_profili":
        if not args or not args[0].strip():
            from task_engine import get_profile_display_name
            profile = ctx.current_permission_profile[0]
            print("Yetki profili: " + get_profile_display_name(profile))
            return True
        return False

    # ---- Görev: read-only list/status/summary ----
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
        if t.error_summary:
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
            print(f"  {i}. [{s.status}] sonuç: {rk} — {s.title}")
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

    # ---- ne yapıyorsun / son yaptığın ne / bugün ne yaptın ----
    if route == "ne_yapiyorsun":
        if ctx.current_task[0]:
            txt = "Şu an " + ctx.current_task[0]
            print(txt)
            ctx.last_response_reason[0] = ctx.current_task[0]
        else:
            txt = "Şu an aktif bir görevim yok."
            print(txt)
            ctx.last_response_reason[0] = "aktif görev yoktu"
        ctx.last_response_text[0] = txt
        return True
    if route == "son_yaptigin_ne":
        if ctx.last_action[0]:
            print(ctx.last_action[0])
            ctx.last_response_reason[0] = ctx.last_action[0]
            ctx.last_response_text[0] = ctx.last_action[0]
        else:
            txt = "Henüz kayda değer bir işlem yapmadım."
            print(txt)
            ctx.last_response_reason[0] = "henüz işlem yoktu"
            ctx.last_response_text[0] = txt
        return True
    if route == "bugun_ne_yaptin":
        if ctx.today_date[0] != date.today().isoformat():
            ctx.today_date[0] = date.today().isoformat()
            ctx.today_actions[0] = []
        if not ctx.today_actions[0]:
            txt = "Bugün kayda değer bir işlem yapmadım."
            print(txt)
            ctx.last_response_reason[0] = "bugün işlem yoktu"
            ctx.last_response_text[0] = txt
        else:
            items = ctx.today_actions[0][-5:]
            lines = ["Bugün şunları yaptım:"] + ["- " + _format_today_bullet(a) for a in items]
            txt = "\n".join(lines)
            print(txt)
            ctx.last_response_reason[0] = "bugünkü işlere baktım"
            ctx.last_response_text[0] = txt
        return True

    # ---- durum / hazir (read-only status) ----
    if route == "durum":
        from core.state import format_durum
        from core.startup_health import get_durum_parts
        from core.workspace_contract import logs_file_path
        ctx.current_task[0] = "durum çıktısını hazırlıyorum."
        try:
            is_ozet = bool(
                args
                and ("ozet" in (args[0].lower().replace("ö", "o").replace("ı", "i") or "")
                     or "özet" in (args[0] or ""))
            )
            if is_ozet:
                print("Durum özeti:")
            log_path = logs_file_path(ctx.base_dir)
            snap = ctx.state.snapshot(base_dir=ctx.base_dir, log_path=log_path)
            parts = get_durum_parts(Path(ctx.base_dir), ctx.ks.is_initialized(), ctx.engine.pl)
            durum_txt = format_durum(snap, parts["consent_ok"], parts["lock_ok"], parts["durum_label"], parts["not_line"])
            print(durum_txt)
            ctx.last_response_reason[0] = parts.get("not_line") or parts.get("durum_label", "")
            ctx.last_action[0] = "En son durum özetini gösterdim."
            ctx.last_response_text[0] = durum_txt
            ctx.record_today_action(ctx.last_action[0])
        finally:
            ctx.current_task[0] = None
        return True
    if route == "hazir":
        from core.startup_health import get_startup_summary
        ctx.current_task[0] = "açılış sağlık özetini doğruluyorum."
        try:
            summary = get_startup_summary(Path(ctx.base_dir), not ctx.state.is_locked(), ctx.pl)
            print(summary)
            ctx.last_response_reason[0] = summary
            ctx.last_action[0] = "En son hazır olma özetini verdim."
            ctx.last_response_text[0] = summary
            ctx.record_today_action(ctx.last_action[0])
        finally:
            ctx.current_task[0] = None
        return True

    # ---- Alias: list only (display) ----
    if route == "alias" and args and args[0] == "liste":
        if not ctx.aliases:
            print("(alias yok)")
        else:
            for k, v in sorted(ctx.aliases.items()):
                print(f"  {k} -> {v}")
        ctx.last_action[0] = "En son alias işlemi yaptım."
        ctx.record_today_action(ctx.last_action[0])
        return True

    return False
