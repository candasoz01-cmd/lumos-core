"""CLI command routing and dispatch for Lumos core.

Extracted from main.py for stabilization. Owns command normalization, dispatch
table, and the main CLI loop; routes only to existing CLI modules.
No observation logic here; routing only. No bootstrap, security, lock,
presence, or workspace contract logic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from cli.cli_notes import handle_notes
from cli.cli_parse import (
    HATIRLA_NOTE_MAX_LEN,
    get_fallback_message,
    normalize_command,
)
from cli.cli_readonly import ReadOnlyContext, handle_gorev_kuyruk, handle_readonly
from cli.cli_tasks_mutation import TaskMutationContext, handle_task_mutation
from task_engine import ALL_PROFILES, get_profile_display_name

# CLI mode constants (command vs text-input modes)
CLI_NORMAL = "normal_komut_modu"
CLI_NOT_BEKLEME = "not_bekleme_modu"
CLI_NOT_DUZENLEME = "not_duzenleme_modu"


class RouterContext:
    """Context for the CLI loop and dispatch. Main builds this; router only routes."""

    base_dir: str
    aliases: dict
    ctx: ReadOnlyContext
    mut_ctx: TaskMutationContext
    pending_ref: list  # [str | None]; router sets pending_ref[0] for kilit/kamera
    cli_mode: list
    last_route: list
    last_note_undo: list
    get_raw_input: Callable[[], str]
    watchdog_tick: Callable[[], None]
    on_lock_menu: Callable[[list], str | None]
    on_presence_menu: Callable[[list], str | None]
    on_self_test: Callable[[], None]
    on_alias_menu: Callable[[list], None]
    # Observation task layer: internal tasks from system_monitor signals (set by runtime).
    observation_engine: Any = None  # ObservationTaskEngine | None
    queue_watcher_tick: Callable[[], None] | None = None  # optional; prints new tasks to CLI


def run_cli_loop(router_ctx: RouterContext) -> None:
    """Run the main CLI loop: input, normalization, dispatch to CLI modules. No bootstrap."""
    while True:
        try:
            router_ctx.watchdog_tick()
        except Exception:
            pass
        if router_ctx.queue_watcher_tick is not None:
            try:
                router_ctx.queue_watcher_tick()
            except Exception:
                pass
        if router_ctx.pending_ref[0] is not None:
            raw = router_ctx.pending_ref[0]
            router_ctx.pending_ref[0] = None
        else:
            raw = router_ctx.get_raw_input()

        # ---- Metin-bekleyen modlar: parser çalışmaz ----
        if router_ctx.cli_mode[0] == CLI_NOT_BEKLEME:
            router_ctx.cli_mode[0] = CLI_NORMAL
            if not raw.strip():
                print("Boş metin kabul edilmiyor.")
                continue
            note_text = raw.strip()
            if len(note_text) > HATIRLA_NOTE_MAX_LEN:
                note_text = (
                    note_text[:HATIRLA_NOTE_MAX_LEN].rsplit(maxsplit=1)[0].rstrip(".,")
                    or note_text[:HATIRLA_NOTE_MAX_LEN]
                )
            router_ctx.ctx.saved_notes[0].append(note_text)
            router_ctx.ctx.record_note_op("bunu hatırla")
            router_ctx.ctx.last_response_reason[0] = "bunu hatırla dedin"
            router_ctx.ctx.last_action[0] = "En son hatırla işlemini yaptım."
            router_ctx.ctx.last_response_text[0] = "Bunu not ettim."
            router_ctx.ctx.record_today_action(router_ctx.ctx.last_action[0])
            print("Bunu not ettim.")
            continue
        if router_ctx.cli_mode[0] == CLI_NOT_DUZENLEME:
            router_ctx.cli_mode[0] = CLI_NORMAL
            if not raw.strip():
                print("Boş metin kabul edilmiyor.")
                continue
            old_content = router_ctx.ctx.saved_notes[0][-1]
            router_ctx.ctx.saved_notes[0][-1] = raw.strip()
            router_ctx.last_note_undo[0] = ("notu_duzenle", old_content)
            router_ctx.ctx.record_note_op("notu düzenle")
            router_ctx.ctx.last_action[0] = "En son notu düzenledim."
            router_ctx.ctx.last_response_text[0] = "Son notu güncelledim."
            print("Son notu güncelledim.")
            continue

        # ---- normal_komut_modu: normalize and dispatch ----
        route, args = normalize_command(raw, Path(router_ctx.base_dir), router_ctx.aliases)

        if route == "":
            continue
        if route != "unknown":
            router_ctx.last_route[0] = route
        if route == "unknown":
            print(get_fallback_message(raw, router_ctx.last_route[0]))
            continue
        if handle_notes(route, args, router_ctx.ctx, router_ctx.cli_mode, router_ctx.last_note_undo):
            continue
        if handle_readonly(route, args, router_ctx.ctx):
            continue
        # ---- Yetki + genel onay (session state) ----
        if route == "yetki_profili":
            name = (args[0] or "").strip().lower().replace("-", "_")
            if name in ALL_PROFILES:
                router_ctx.ctx.current_permission_profile[0] = name
                print("Yetki profili: " + get_profile_display_name(name))
            else:
                print("Geçerli profiller: rapor, guvenli_yurut, kisitli_otonom")
            continue
        if route == "genel_onay_ac":
            router_ctx.mut_ctx.general_approval[0] = True
            print("Genel onay açık. Bu oturumda izin profili kapsamında işler yürütülebilir.")
            continue
        if route == "genel_onay_kapat":
            router_ctx.mut_ctx.general_approval[0] = False
            print("Genel onay kapalı.")
            continue
        if handle_task_mutation(route, args, router_ctx.mut_ctx):
            continue
        if route == "gorev_kuyruk":
            handle_gorev_kuyruk(getattr(router_ctx, "observation_engine", None))
            continue
        if route == "exit":
            print("OK")
            break
        if route == "kilit":
            router_ctx.ctx.current_task[0] = "kilit menüsündeyim."
            try:
                result = router_ctx.on_lock_menu(args)
                if result is not None:
                    router_ctx.pending_ref[0] = result
                else:
                    router_ctx.ctx.last_action[0] = "En son kilit menüsünü açtım."
                    router_ctx.ctx.record_today_action(router_ctx.ctx.last_action[0])
            finally:
                router_ctx.ctx.current_task[0] = None
            continue
        if route == "kamera":
            router_ctx.ctx.current_task[0] = "kamera menüsündeyim."
            try:
                result = router_ctx.on_presence_menu(args)
                if result is not None:
                    router_ctx.pending_ref[0] = result
                else:
                    router_ctx.ctx.last_action[0] = "En son kamera menüsünü açtım."
                    router_ctx.ctx.record_today_action(router_ctx.ctx.last_action[0])
            finally:
                router_ctx.ctx.current_task[0] = None
            continue
        if route == "self_test":
            router_ctx.on_self_test()
            continue
        if route == "alias":
            if handle_readonly(route, args, router_ctx.ctx):
                continue
            router_ctx.on_alias_menu(args)
            router_ctx.ctx.last_action[0] = "En son alias işlemi yaptım."
            router_ctx.ctx.record_today_action(router_ctx.ctx.last_action[0])
            continue
        print(get_fallback_message(raw, router_ctx.last_route[0]))
