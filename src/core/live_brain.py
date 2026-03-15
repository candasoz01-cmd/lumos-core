"""Live brain mode: free-text input in online mode → direct answer and/or task creation.

When CLI receives unknown input and online mode is enabled, this module handles
the input via the online engine (LLM) and optionally creates a task through Brain.
Safe: no bypass of consent/lock/profile; task creation goes through Planner/TaskEngine.

Pending intent: when we ask a clarification (e.g. "Hangi klasör?"), we store the
active intent; when the user answers, we continue that intent (clarification → answer → resumed intent).
Pending action: when a task is blocked due to consent, we store it; when the user
says "onaylıyorum", we set general_approval and propose the next concrete action.

Active response path: CLI (unknown) → router on_live_brain → handle_live_brain
→ online_engine.process (state injected) → model_client.generate → user output.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.brain import run as brain_run

if TYPE_CHECKING:
    from core.state import CoreState
    from task_engine.observation import ObservationEngine

# Consent phrases: user granting approval so we can resume a blocked action
_CONSENT_PHRASES = re.compile(
    r"^(onayl[\u0131i]yorum|onay\s*veriyorum|onay\s*ver|onay$|genel\s*onay\s*ac|kabul\s*ediyorum)$",
    re.IGNORECASE,
)

# Replies we do not treat as clarification answers (keep pending intent, do not consume)
_CHITCHAT_REPLIES = frozenset(
    s.strip().lower()
    for s in (
        "merhaba", "selam", "hi", "hello", "hey", "ok", "tamam", "evet", "hayır", "hayir",
        "no", "yes", "?", "??", "!", "!!", ":)",
    )
)


def _is_likely_unrelated_reply(raw: str, _missing_param: str) -> bool:
    """True if reply looks like small talk/emoji/greeting; do not consume pending intent."""
    t = (raw or "").strip()
    if not t:
        return True
    if t.lower() in _CHITCHAT_REPLIES:
        return True
    # Emoji/symbol-only: no letter, no digit
    if not re.search(r"[a-zA-Z0-9]", t):
        return True
    return False


def _resume_pending_intent(
    raw: str,
    intent: str,
    missing_param: str,
    state: "CoreState | None",
    pending_intent_ref: list | None,
) -> tuple[str, bool]:
    """
    Handle user reply when a pending intent exists. Does not call the LLM.
    Returns (response_message, consumed).
    - consumed True: reply was used as clarification; state/ref cleared; intent resumed (or rejected).
    - consumed False: reply is unrelated (chitchat/emoji); state kept; ask again or prompt.
    """
    if _is_likely_unrelated_reply(raw, missing_param):
        # Do not consume; keep pending intent; prompt again.
        if intent == "list_files":
            return "Hangi klasör demek istemiştim; lütfen klasör adı yaz.", False
        return "Lütfen önceki soruya yanıt ver (ör. parametre veya değer yaz).", False

    # Valid clarification reply: resume intent, then clear state (no filesystem faked).
    if pending_intent_ref is not None and len(pending_intent_ref) > 0:
        pending_intent_ref[0] = None
    if state is not None:
        state.pending_intent = None
        state.pending_params = {}
        state.pending_action = None

    if intent == "list_files":
        return f"{raw.strip()} klasörü için listeleme istedin; bu özellik şu an mevcut değil.", True
    return f"Niyet: {intent}. Yanıt: {raw!r}. Bu özellik şu an mevcut değil.", True


def _is_consent_phrase(text: str) -> bool:
    """True if the user message is granting consent (e.g. onaylıyorum)."""
    t = (text or "").strip()
    return bool(t and _CONSENT_PHRASES.match(t))


def _detect_list_files_intent(text: str) -> dict | None:
    """
    Detect "list files in folder" / "klasördeki dosyaları listele" style intent.
    Returns a pending_intent dict if we need to ask for folder; else None.
    Does not fake filesystem: we only store intent; when user answers, we continue
    (engine or handler will state clearly if the tool does not exist).
    """
    t = (text or "").strip().lower()
    if not t:
        return None
    # Turkish: klasördeki dosyaları listele (folder implied). Use ASCII+unicode for portability.
    if re.search(r"(klas[o\u00f6]r(deki)?\s*(dosya(lar[\u0131i])?\s*listele?|dosya))", t):
        return {"intent": "list_files", "params": {}, "missing_param": "folder", "user_message": text}
    if re.search(r"dosyalar[\u0131i]\s*listele", t) and "klasör" not in t and "folder" not in t:
        return {"intent": "list_files", "params": {}, "missing_param": "folder", "user_message": text}
    # English
    if re.search(r"list\s+files?\s+(in\s+)?(the\s+)?(folder|dir)", t):
        return {"intent": "list_files", "params": {}, "missing_param": "folder", "user_message": text}
    if re.search(r"list\s+files?", t) and "folder" not in t and "dir" not in t:
        return {"intent": "list_files", "params": {}, "missing_param": "folder", "user_message": text}
    return None


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
    *,
    general_approval_ref: list | None = None,
    pending_intent_ref: list | None = None,
    pending_action_ref: list | None = None,
) -> str:
    """
    Handle free-text input in online mode: ask online engine for response;
    if the engine returns create_task + task_goal, run Brain and merge result.

    When state is provided, mode/presence/consent/lock are injected into the
    engine so the model receives current runtime state (Lumos identity prompt).

    Pending intent/action (optional refs):
    - If pending_intent_ref is set, user message is treated as the clarification
      answer; we build continuation context and call the engine, then clear pending_intent.
    - If user says a consent phrase (e.g. onaylıyorum) and general_approval_ref is
      provided, we set general_approval_ref[0] = True; if pending_action_ref is set,
      we propose the next concrete action and clear pending_action.
    - When we ask a clarification (e.g. list_files → "Hangi klasör?"), we set
      pending_intent_ref[0]. When a task is blocked due to consent, we set
      pending_action_ref[0].

    Returns a single string to print (natural Turkish, concise).
    """
    raw = (raw_input or "").strip()
    if not raw:
        return "Boş giriş; işlem yapılmadı."

    # --- Consent flow: user says "onaylıyorum" (or similar) ---
    if _is_consent_phrase(raw):
        if general_approval_ref is not None:
            general_approval_ref[0] = True
        if pending_action_ref is not None and len(pending_action_ref) > 0 and pending_action_ref[0]:
            pa = pending_action_ref[0]
            task_id = pa.get("task_id")
            goal = (pa.get("goal") or "").strip() or "önceki işlem"
            pending_action_ref[0] = None
            return (
                "Genel onay açıldı. Şimdi şunu yapabilirim: "
                + goal[:120]
                + ("…" if len(goal) > 120 else "")
                + (f"\nDevam etmek için: görev yürüt {task_id}" if task_id else "")
            )
        return "Genel onay açıldı. İstediğin işlemi söyleyebilirsin."

    # --- Pre-LLM: pending intent MUST be handled before any free-text LLM call ---
    # Clarification replies (e.g. "WORK_2026") go to _resume_pending_intent only; original intent is resumed and state cleared.
    _pending_intent_name: str | None = None
    _pending_missing: str = ""
    if state is not None and getattr(state, "pending_intent", None):
        _pending_intent_name = (state.pending_intent or "").strip() or "unknown"
        _params = getattr(state, "pending_params", None) or {}
        _pending_missing = (_params.get("_missing_param") or "").strip()
    elif pending_intent_ref is not None and len(pending_intent_ref) > 0 and pending_intent_ref[0]:
        _pi = pending_intent_ref[0]
        _pending_intent_name = _pi.get("intent") or "unknown"
        _pending_missing = _pi.get("missing_param") or ""

    if _pending_intent_name:
        msg, _ = _resume_pending_intent(raw, _pending_intent_name, _pending_missing, state, pending_intent_ref)
        return msg

    # --- Ask clarification: deterministic intent that needs one param (e.g. list_files → folder) ---
    detected = _detect_list_files_intent(raw)
    if detected:
        intent_name = (detected.get("intent") or "").strip() or "unknown"
        missing_param = (detected.get("missing_param") or "").strip()
        params = dict(detected.get("params") or {})
        if missing_param:
            params["_missing_param"] = missing_param
        if state is not None:
            state.pending_intent = intent_name
            state.pending_params = params
            state.pending_action = intent_name
        if pending_intent_ref is not None and len(pending_intent_ref) > 0:
            pending_intent_ref[0] = detected
        return "Hangi klasör?"

    # --- Normal path: build context and call engine ---
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
            block = getattr(brain_result, "block_reason_or_observation", "") or ""
            # Store pending_action when blocked due to consent / genel onay
            if pending_action_ref is not None and len(pending_action_ref) > 0:
                if "genel onay" in (block or "").lower() or "consent" in (block or "").lower() or "yetki kısıtı" in (block or "").lower():
                    pending_action_ref[0] = {
                        "task_id": getattr(brain_result, "task_id", None),
                        "goal": getattr(brain_result, "goal", "") or task_goal,
                        "block_reason": block[:200] if block else "",
                    }
            return _format_live_with_task(response_text, summary)
        except Exception:
            return response_text + "\nGörev oluşturulurken hata oluştu."

    return _format_live_direct(response_text)
