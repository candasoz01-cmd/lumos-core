"""Live brain mode: free-text input in online mode → direct answer and/or task creation.

When CLI receives unknown input and online mode is enabled, this module handles
the input via the online engine (LLM) and optionally creates a task through Brain.
Safe: no bypass of consent/lock/profile; task creation goes through Planner/TaskEngine.

--- Pending intent / clarification / resume flow ---

1. User says something that matches a deterministic intent (e.g. "klasördeki dosyaları listele").
2. If the intent needs a missing param (e.g. folder), we ask clarification: "Hangi klasör?"
   and store pending state so the next user message is treated as the answer:
   - state.pending_intent = intent name (e.g. "list_files")
   - state.pending_params = { "_missing_param": "folder", ... }
   - pending_intent_ref[0] = detected dict (intent, params, missing_param, user_message)
3. Next turn: user message is routed to the resume path first (before consent or LLM).
   We read pending_intent from state or pending_intent_ref and call _resume_pending_intent.
4. In _resume_pending_intent:
   - If the reply looks like chitchat/emoji (e.g. "merhaba"), we do not consume: return
     a prompt to answer the question; pending state is kept.
   - If the reply is a valid clarification answer (e.g. "WORK_2026"), we clear pending
     state (state.pending_intent, pending_params, pending_action; pending_intent_ref[0]),
     then either execute the intent or reject with "Bu özellik şu an mevcut değil."

State: CoreState.pending_intent, pending_params, pending_action hold the active intent
between clarification question and answer. Ref (pending_intent_ref) is used when
caller does not have access to state so the next handle_live_brain call can see the
pending intent.

Pending action: when a task is blocked due to consent, we set pending_action_ref;
when the user says "onaylıyorum", we set general_approval and propose the next action.

Active response path: CLI (unknown) → router on_live_brain → handle_live_brain
→ online_engine.process (state injected) → model_client.generate → user output.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.brain import run as brain_run
from core.intent_params import extract_intent_params
from core.next_step import (
    REASON_CLARIFICATION_NEEDED,
    REASON_CONSENT_MISSING,
    REASON_TOOL_UNAVAILABLE,
    suggest_next_step,
)

if TYPE_CHECKING:
    from core.state import CoreState
    from task_engine.observation import ObservationEngine

# Deterministic intent map: exact phrase (normalized) → intent name. Checked before any LLM call.
INTENT_MAP: dict[str, str] = {
    "listele": "list_files",
    "dosyaları listele": "list_files",
    "klasör içeriği": "list_files",
    "kilit aç": "unlock",
    "kilidi aç": "unlock",
    "kilit kapat": "lock",
    "çık": "exit",
}

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


def _tool_available(name: str) -> bool:
    """True if the intent has a registered tool that is available. No registry module: always False."""
    return False


def _reject_intent(intent: str, raw: str = "", folder: str | None = None) -> str:
    """Reject message when tool is not available; use next-step guidance."""
    g = suggest_next_step(intent, None, REASON_TOOL_UNAVAILABLE, None)
    if intent == "list_files" and (folder or raw):
        display = (folder or raw).strip()
        return f"{display} klasörü için listeleme istedin. {g['message']}"
    return g["message"] if not raw else f"Niyet: {intent}. Yanıt: {raw!r}. {g['message']}"


def _resume_pending_intent(
    raw: str,
    intent: str,
    missing_param: str,
    state: "CoreState | None",
    pending_intent_ref: list | None,
) -> tuple[str, bool]:
    """
    Handle user reply when a pending intent exists. Does not call the LLM.
    Flow: intent → tool check → execute or reject.
    Returns (response_message, consumed).
    - consumed True: reply was used as clarification; state/ref cleared; intent resumed (or rejected).
    - consumed False: reply is unrelated (chitchat/emoji); state kept; ask again or prompt.
    """
    if _is_likely_unrelated_reply(raw, missing_param):
        # Do not consume; keep pending intent; prompt again.
        if intent == "list_files":
            return "Hangi klasör demek istemiştim; lütfen klasör adı yaz.", False
        return "Lütfen önceki soruya yanıt ver (ör. parametre veya değer yaz).", False

    # Capture params before clearing (e.g. folder from pending_params or ref)
    _params: dict = {}
    if state is not None:
        _params = dict(getattr(state, "pending_params", None) or {})
    if not _params and pending_intent_ref and len(pending_intent_ref) > 0 and pending_intent_ref[0]:
        _params = dict((pending_intent_ref[0].get("params") or {}))

    # Valid clarification reply: clear state, then intent → tool check → execute / reject
    if pending_intent_ref is not None and len(pending_intent_ref) > 0:
        pending_intent_ref[0] = None
    if state is not None:
        state.pending_intent = None
        state.pending_params = {}
        state.pending_action = None

    if not _tool_available(intent):
        _folder = _params.get("folder") or raw
        return _reject_intent(intent, raw, folder=_folder), True
    # Tool available; execute (real implementation not wired yet — no filesystem)
    if intent == "list_files":
        _folder = _params.get("folder") or raw
        return f"{_folder.strip()} klasörü için listeleme istedin; dosya erişimi henüz bağlanmadı.", True
    return f"Niyet: {intent}. Yanıt: {raw!r}. Dosya erişimi henüz bağlanmadı.", True


def _is_consent_phrase(text: str) -> bool:
    """True if the user message is granting consent (e.g. onaylıyorum)."""
    t = (text or "").strip()
    return bool(t and _CONSENT_PHRASES.match(t))


def _normalize_for_intent(text: str) -> str:
    """Strip and lower for intent map lookup."""
    return (text or "").strip().lower()


def _lookup_deterministic_intent(normalized: str) -> str | None:
    """Return intent name if normalized input is in INTENT_MAP, else None."""
    return INTENT_MAP.get(normalized) if normalized else None


def _resolve_deterministic_intent_and_params(raw: str) -> tuple[str | None, dict[str, str]]:
    """
    Resolve deterministic intent (list_files, lock, unlock, exit) and params from raw message.
    Uses INTENT_MAP, _detect_list_files_intent, and extract_intent_params. No execution.
    Returns (intent_name, params) or (None, {}) when no deterministic intent matches.
    """
    t = (raw or "").strip()
    if not t:
        return (None, {})
    normalized = _normalize_for_intent(t)
    intent_name = _lookup_deterministic_intent(normalized)
    if intent_name:
        params = extract_intent_params(intent_name, raw)
        return (intent_name, params)
    detected = _detect_list_files_intent(raw)
    if detected:
        intent_name = (detected.get("intent") or "").strip() or "list_files"
        params = dict(detected.get("params") or {})
        if not params:
            params = extract_intent_params("list_files", raw)
        return (intent_name, params)
    return (None, {})


def _detect_list_files_intent(text: str) -> dict | None:
    """
    Detect "list files in folder" / "klasördeki dosyaları listele" or "X klasörünü listele" style intent.
    Returns a pending_intent dict; if folder can be extracted from same message, params has "folder" and no missing_param.
    Does not fake filesystem: we only store intent; when user answers, we continue
    (engine or handler will state clearly if the tool does not exist).
    """
    t = (text or "").strip().lower()
    if not t:
        return None
    # If we can extract folder from this message, return list_files with params and no clarification
    params = extract_intent_params("list_files", text)
    if params.get("folder"):
        return {"intent": "list_files", "params": params, "missing_param": None, "user_message": text}
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

    # --- Deterministic intent routing: resolve intent + params, print only (no execution, no clarification flow) ---
    resolved_intent, resolved_params = _resolve_deterministic_intent_and_params(raw)
    if resolved_intent is not None:
        lines = [f"intent = {resolved_intent}", f"params = {resolved_params!r}"]
        if resolved_intent == "list_files" and not resolved_params.get("folder"):
            g = suggest_next_step("list_files", state, REASON_CLARIFICATION_NEEDED, "folder")
            if g.get("next_step"):
                lines.append(f"next_step = {g['next_step']!r}")
        return "\n".join(lines)

    # --- Pending intent first: route to resume path before consent, chitchat, or LLM ---
    # If we asked a clarification (e.g. "Hangi klasör?"), the next reply must fill missing params and resume intent.
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

    # --- Deterministic intent map (before LLM): exact phrase → intent, handle directly ---
    normalized = _normalize_for_intent(raw)
    intent_name = _lookup_deterministic_intent(normalized)
    if intent_name:
        if intent_name == "list_files":
            params = extract_intent_params("list_files", raw)
            if params.get("folder"):
                # Folder present in same message: no clarification; go to reject/next-step with folder
                if not _tool_available("list_files"):
                    return _reject_intent("list_files", raw, folder=params["folder"])
                return f"{params['folder']} klasörü için listeleme istedin; dosya erişimi henüz bağlanmadı."
            if not _tool_available("list_files"):
                g = suggest_next_step("list_files", state, REASON_TOOL_UNAVAILABLE, None)
                return g["message"]
            detected = {"intent": "list_files", "params": {}, "missing_param": "folder", "user_message": raw}
            params = dict(detected.get("params") or {})
            params["_missing_param"] = "folder"
            if state is not None:
                state.pending_intent = "list_files"
                state.pending_params = params
                state.pending_action = "list_files"
            if pending_intent_ref is not None and len(pending_intent_ref) > 0:
                pending_intent_ref[0] = detected
            g = suggest_next_step("list_files", state, REASON_CLARIFICATION_NEEDED, "folder")
            return g["message"]
        if intent_name == "unlock":
            return "Kilit açma bu arayüzden yapılmıyor."
        if intent_name == "lock":
            return "Kilit kapatma bu arayüzden yapılmıyor."
        if intent_name == "exit":
            return "Çıkış için uygun komutu kullan (ör. Ctrl+C veya komut satırından çık)."
        g = suggest_next_step(intent_name, state, REASON_TOOL_UNAVAILABLE, None)
        return g["message"]

    # --- Regex-based list_files detection (if not in INTENT_MAP) ---
    detected = _detect_list_files_intent(raw)
    if detected:
        intent_name = (detected.get("intent") or "").strip() or "unknown"
        params = dict(detected.get("params") or {})
        missing_param = (detected.get("missing_param") or "").strip()
        if params.get("folder"):
            # Folder extracted from same message: no clarification; reject/next-step with folder
            if not _tool_available(intent_name):
                return _reject_intent(intent_name, raw, folder=params["folder"])
            return f"{params['folder']} klasörü için listeleme istedin; dosya erişimi henüz bağlanmadı."
        if not _tool_available(intent_name):
            g = suggest_next_step(intent_name, state, REASON_TOOL_UNAVAILABLE, None)
            return g["message"]
        if missing_param:
            params["_missing_param"] = missing_param
        if state is not None:
            state.pending_intent = intent_name
            state.pending_params = params
            state.pending_action = intent_name
        if pending_intent_ref is not None and len(pending_intent_ref) > 0:
            pending_intent_ref[0] = detected
        g = suggest_next_step(intent_name, state, REASON_CLARIFICATION_NEEDED, missing_param or "folder")
        return g["message"]

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
            pl = getattr(brain_result, "pipeline", None)
            if pl:
                from core.patch_pipeline_lifecycle import format_pipeline_summary_line

                summary = summary + "\n" + format_pipeline_summary_line(pl)
            block = getattr(brain_result, "block_reason_or_observation", "") or ""
            # Store pending_action when blocked due to consent / genel onay; add next-step message
            if pending_action_ref is not None and len(pending_action_ref) > 0:
                if "genel onay" in (block or "").lower() or "consent" in (block or "").lower() or "yetki kısıtı" in (block or "").lower():
                    pending_action_ref[0] = {
                        "task_id": getattr(brain_result, "task_id", None),
                        "goal": getattr(brain_result, "goal", "") or task_goal,
                        "block_reason": block[:200] if block else "",
                    }
                    g = suggest_next_step(None, state, REASON_CONSENT_MISSING, None)
                    return _format_live_with_task(response_text, summary) + "\n" + g["message"]
            return _format_live_with_task(response_text, summary)
        except Exception:
            return response_text + "\nGörev oluşturulurken hata oluştu."

    return _format_live_direct(response_text)

# lumos:instruction-pipeline safe touch

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)
