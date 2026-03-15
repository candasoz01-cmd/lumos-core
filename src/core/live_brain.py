"""Live brain mode: free-text input in online mode → direct answer and/or task creation.

When CLI receives unknown input and online mode is enabled, this module handles
the input via the online engine (LLM) and optionally creates a task through Brain.
Safe: no bypass of consent/lock/profile; task creation goes through Planner/TaskEngine.

Active response path: CLI (unknown) → router on_live_brain → handle_live_brain
→ online_engine.process (state injected) → model_client.generate → user output.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.brain import run as brain_run

if TYPE_CHECKING:
    from core.state import CoreState
    from task_engine.observation import ObservationEngine


def _format_live_direct(response: str) -> str:
    """Minimal Turkish response when no task was created."""
    text = (response or "").strip()
    return text if text else "Yanıt üretilemedi."


def _format_live_with_task(direct_response: str, brain_summary: str) -> str:
    """Concise Turkish: direct answer + clear note that a task was created."""
    parts: list[str] = []
    direct = (direct_response or "").strip()
    if direct:
        parts.append(direct)
    parts.append("Görev oluşturuldu ve yürütüldü.")
    if brain_summary:
        parts.append(brain_summary)
    return "\n".join(parts)


def handle_live_brain(
    raw_input: str,
    online_engine: Any,
    task_store: Any,
    base_dir: Path | str,
    permission_profile: str,
    general_approval: bool,
    observation_engine: "ObservationEngine | None" = None,
    state: "CoreState | None" = None,
) -> str:
    """
    Handle free-text input in online mode: ask online engine for response;
    if the engine returns create_task + task_goal, run Brain and merge result.

    When state is provided, mode/presence/consent/lock are injected into the
    engine so the model receives current runtime state (Lumos identity prompt).

    Returns a single string to print (natural Turkish, concise).
    """
    raw = (raw_input or "").strip()
    if not raw:
        return "Boş giriş; işlem yapılmadı."

    short_context = ""
    mode = "—"
    presence = "—"
    consent = "—"
    lock = "—"
    if state is not None:
        mode = state.mode_str()
        lock = state.lock_status()
        try:
            presence = state.presence_display()
        except Exception:
            presence = "—"
        consent = "kayıtlı" if general_approval else "yok"

    if hasattr(online_engine, "process"):
        result = online_engine.process(
            raw,
            short_context=short_context,
            mode=mode,
            presence=presence,
            consent=consent,
            lock=lock,
        )
    else:
        return "Online motor hazır değil."

    response_text = (result.get("response") or "").strip() or "Yanıt yok."
    create_task = result.get("create_task") is True
    task_goal = (result.get("task_goal") or "").strip()

    if create_task and task_goal:
        try:
            brain_result = brain_run(
                task_goal,
                task_store,
                base_dir,
                permission_profile,
                general_approval,
                observation_engine=observation_engine,
            )
            summary = getattr(brain_result, "human_readable_summary", "") or ""
            return _format_live_with_task(response_text, summary)
        except Exception:
            return response_text + "\nGörev oluşturulurken hata oluştu."

    return _format_live_direct(response_text)
