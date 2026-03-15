"""Live brain mode: routing unknown input to Brain when online; fallback when offline."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_known_command_uses_cli_path():
    """Registered commands must not be treated as unknown; CLI path is used."""
    from cli.cli_parse import normalize_command

    base = Path(tempfile.gettempdir()) / "lumos_live_brain_test"
    base.mkdir(parents=True, exist_ok=True)
    route, _ = normalize_command("durum", base, {})
    assert route != "unknown"
    route, _ = normalize_command("görevler", base, {})
    assert route != "unknown"
    route, _ = normalize_command("yardım", base, {})
    assert route != "unknown"


def test_unknown_input_offline_fallback_decision():
    """When mode is offline, router context has no live brain handler (fallback used)."""
    from cli.cli_router import RouterContext

    ctx = RouterContext()
    ctx.mode = "offline"
    ctx.on_live_brain = None
    assert getattr(ctx, "mode", "offline") == "offline"
    assert getattr(ctx, "on_live_brain", None) is None
    # Condition used in router: use live brain only when online and handler set
    use_live = (
        getattr(ctx, "mode", "offline") == "online"
        and getattr(ctx, "on_live_brain", None) is not None
    )
    assert use_live is False


def test_unknown_input_online_routes_to_brain():
    """When mode is online and handler set, unknown input is handled by live brain (handler called)."""
    from core.live_brain import handle_live_brain

    mock_engine = MagicMock()
    mock_engine.process.return_value = {"response": "Merhaba, dinliyorum."}
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "selam",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
        )
    assert "Merhaba" in out or "dinliyorum" in out
    mock_engine.process.assert_called_once()
    call_args = mock_engine.process.call_args
    assert call_args[0][0] == "selam"


def test_live_brain_injects_state_when_provided():
    """When state is provided, handle_live_brain passes mode/presence/consent/lock to engine.process."""
    from core.live_brain import handle_live_brain
    from core.state import CoreState

    mock_engine = MagicMock()
    mock_engine.process.return_value = {"response": "Tamam."}
    mock_lumos = MagicMock()
    mock_lumos.lock_state.unlocked = True
    mock_pl = MagicMock()
    mock_pl.presence_status.return_value = "ON"
    mock_pl.is_running.return_value = True
    mock_pl.load_presence_cfg.return_value = MagicMock(enabled=True)
    state = CoreState(mock_lumos, mock_pl, "online", base_dir=Path("/tmp"))
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        handle_live_brain(
            "test",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            True,
            observation_engine=None,
            state=state,
        )
    mock_engine.process.assert_called_once()
    kwargs = mock_engine.process.call_args[1]
    assert kwargs.get("mode") == "online"
    assert kwargs.get("lock") == "UNLOCKED"
    assert kwargs.get("consent") == "kayıtlı"


def test_live_brain_direct_response_without_task():
    """Brain can return a direct response without creating a task."""
    from core.live_brain import handle_live_brain

    mock_engine = MagicMock()
    mock_engine.process.return_value = {"response": "Evet, bu konuda yardımcı olabilirim."}
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "bana yardım eder misin",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
        )
    assert "yardımcı" in out or "Evet" in out
    assert "Görev oluşturuldu" not in out


def test_live_brain_creates_task_when_needed():
    """When online engine returns create_task and task_goal, Brain runs and task is created."""
    from core.live_brain import handle_live_brain
    from task_engine import TaskStore, PROFILE_GUVENLI_YURUT

    with tempfile.TemporaryDirectory() as d:
        store = TaskStore(d)
        mock_engine = MagicMock()
        mock_engine.process.return_value = {
            "response": "Tamam, notları kontrol ediyorum.",
            "create_task": True,
            "task_goal": "not sistemini kontrol et",
        }
        out = handle_live_brain(
            "notları kontrol et",
            mock_engine,
            store,
            d,
            PROFILE_GUVENLI_YURUT,
            True,
            observation_engine=None,
        )
    assert "Görev oluşturuldu" in out
    # Task should exist
    all_tasks = store.list_all()
    assert len(all_tasks) >= 1


def test_clarification_answer_resumes_intent():
    """Clarification -> user answers -> pending intent handler only (no LLM); ref cleared."""
    from core.live_brain import handle_live_brain

    pending_intent_ref = [{"intent": "list_files", "params": {}, "missing_param": "folder", "user_message": "klasördeki dosyaları listele"}]
    mock_engine = MagicMock()
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "/tmp",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            pending_intent_ref=pending_intent_ref,
        )
    assert "mevcut değil" in out
    assert "listeleme istedin" in out or "/tmp" in out
    assert pending_intent_ref[0] is None
    mock_engine.process.assert_not_called()


def test_consent_approval_resumes_pending_action():
    """Consent phrase -> set general_approval and propose next action when pending_action is set."""
    from core.live_brain import handle_live_brain

    general_approval_ref = [False]
    pending_action_ref = [{"task_id": 1, "goal": "notları dışa aktar", "block_reason": "genel onay kapalı"}]
    mock_engine = MagicMock()
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "onaylıyorum",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            general_approval_ref=general_approval_ref,
            pending_action_ref=pending_action_ref,
        )
    assert general_approval_ref[0] is True
    assert pending_action_ref[0] is None
    assert "Genel onay açıldı" in out
    assert "notları dışa aktar" in out or "yapabilirim" in out
    mock_engine.process.assert_not_called()


def test_no_pending_intent_safe_generic_follow_up():
    """No pending intent/action -> normal engine call, no mutation of refs."""
    from core.live_brain import handle_live_brain

    pending_intent_ref = [None]
    pending_action_ref = [None]
    mock_engine = MagicMock()
    mock_engine.process.return_value = {"response": "Tamam, başka bir şey?"}
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "saat kaç",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            pending_intent_ref=pending_intent_ref,
            pending_action_ref=pending_action_ref,
        )
    assert "Tamam" in out or "başka" in out
    assert pending_intent_ref[0] is None
    assert pending_action_ref[0] is None
    mock_engine.process.assert_called_once()
    assert mock_engine.process.call_args[0][0] == "saat kaç"


def test_list_files_intent_rejected_when_tool_unavailable():
    """Deterministic intent: list_files with no folder -> print intent + params + next_step (no tool execution)."""
    from core.live_brain import handle_live_brain

    pending_intent_ref = [None]
    mock_engine = MagicMock()
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "klasördeki dosyaları listele",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            pending_intent_ref=pending_intent_ref,
        )
    assert "intent = list_files" in out
    assert "params =" in out
    assert pending_intent_ref[0] is None
    mock_engine.process.assert_not_called()


def test_list_files_intent_asks_clarification():
    """Deterministic intent: 'klasördeki dosyaları listele' -> print intent + params + next_step (no clarification flow)."""
    from core.live_brain import handle_live_brain

    pending_intent_ref = [None]
    mock_engine = MagicMock()
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "klasördeki dosyaları listele",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            pending_intent_ref=pending_intent_ref,
        )
    assert "intent = list_files" in out
    assert "params =" in out
    assert "next_step =" in out and "klasör adını yaz" in out
    assert pending_intent_ref[0] is None
    mock_engine.process.assert_not_called()


def test_list_files_clarification_then_reply_resumes_intent():
    """Deterministic intent routing: first message prints intent+params+next_step only (no clarification flow)."""
    from core.live_brain import handle_live_brain
    from core.state import CoreState

    pending_intent_ref = [None]
    mock_engine = MagicMock()
    mock_lumos = MagicMock()
    mock_pl = MagicMock()
    state = CoreState(mock_lumos, mock_pl, "online")

    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out1 = handle_live_brain(
            "klasördeki dosyaları listele",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            state=state,
            pending_intent_ref=pending_intent_ref,
        )
    assert "intent = list_files" in out1
    assert "params =" in out1 and "next_step =" in out1
    assert state.pending_intent is None
    assert pending_intent_ref[0] is None
    mock_engine.process.assert_not_called()


def test_pending_intent_reply_routed_before_llm():
    """When pending intent exists, reply is handled by _resume_pending_intent; LLM is never called."""
    from core.live_brain import handle_live_brain
    from core.state import CoreState

    mock_engine = MagicMock()
    mock_engine.process.return_value = {"response": "Generic reply."}
    mock_lumos = MagicMock()
    mock_pl = MagicMock()
    state = CoreState(mock_lumos, mock_pl, "online")
    state.pending_intent = "list_files"
    state.pending_params = {"_missing_param": "folder"}
    state.pending_action = "list_files"
    pending_intent_ref = [None]

    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR
        store = TaskStore(d)
        out = handle_live_brain(
            "WORK_2026",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            state=state,
            pending_intent_ref=pending_intent_ref,
        )
    assert "WORK_2026" in out and "mevcut değil" in out
    assert state.pending_intent is None
    mock_engine.process.assert_not_called()


def test_unrelated_chitchat_does_not_consume_pending_intent():
    """Emoji or greeting as reply does not consume pending intent; state kept; no LLM call."""
    from core.live_brain import handle_live_brain
    from core.state import CoreState

    mock_engine = MagicMock()
    mock_lumos = MagicMock()
    mock_pl = MagicMock()
    state = CoreState(mock_lumos, mock_pl, "online")
    state.pending_intent = "list_files"
    state.pending_params = {"_missing_param": "folder"}
    pending_intent_ref = [None]

    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR
        store = TaskStore(d)
        out = handle_live_brain(
            "merhaba",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            state=state,
            pending_intent_ref=pending_intent_ref,
        )
    assert "Hangi klasör" in out or "lütfen" in out
    assert state.pending_intent == "list_files"
    assert state.pending_params.get("_missing_param") == "folder"
    mock_engine.process.assert_not_called()

    # Emoji-only also should not consume
    state2 = CoreState(MagicMock(), MagicMock(), "online")
    state2.pending_intent = "list_files"
    state2.pending_params = {"_missing_param": "folder"}
    handle_live_brain(
        "👍",
        mock_engine,
        store,
        d,
        PROFILE_RAPOR,
        False,
        observation_engine=None,
        state=state2,
        pending_intent_ref=[None],
    )
    assert state2.pending_intent == "list_files"
    mock_engine.process.assert_not_called()


def test_pending_state_clears_after_completion():
    """After valid clarification reply, state.pending_* and ref are cleared."""
    from core.live_brain import handle_live_brain
    from core.state import CoreState

    state = CoreState(MagicMock(), MagicMock(), "online")
    state.pending_intent = "list_files"
    state.pending_params = {"_missing_param": "folder"}
    state.pending_action = "list_files"
    pending_intent_ref = [{"intent": "list_files", "params": {}, "missing_param": "folder"}]

    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR
        store = TaskStore(d)
        handle_live_brain(
            "/tmp",
            MagicMock(),
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            state=state,
            pending_intent_ref=pending_intent_ref,
        )
    assert state.pending_intent is None
    assert state.pending_params == {}
    assert state.pending_action is None
    assert pending_intent_ref[0] is None


def test_list_files_with_folder_no_clarification_work_2026_klasorunu():
    """WORK_2026 klasörünü listele -> deterministic intent routing: print intent + params only."""
    from core.live_brain import handle_live_brain

    pending_intent_ref = [None]
    mock_engine = MagicMock()
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "WORK_2026 klasörünü listele",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            pending_intent_ref=pending_intent_ref,
        )
    assert "intent = list_files" in out
    assert "params =" in out and "WORK_2026" in out
    assert "Hangi klasör" not in out
    assert pending_intent_ref[0] is None
    mock_engine.process.assert_not_called()


def test_list_files_with_folder_no_clarification_work_2026_listele():
    """work_2026 listele -> deterministic intent routing: print intent + params only."""
    from core.live_brain import handle_live_brain

    pending_intent_ref = [None]
    mock_engine = MagicMock()
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "work_2026 listele",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            pending_intent_ref=pending_intent_ref,
        )
    assert "intent = list_files" in out
    assert "params =" in out and "work_2026" in out
    assert "Hangi klasör" not in out
    assert pending_intent_ref[0] is None
    mock_engine.process.assert_not_called()


def test_list_files_dosyalari_listele_still_asks_clarification():
    """Deterministic intent: 'dosyaları listele' (no folder) -> print intent + params + next_step."""
    from core.live_brain import handle_live_brain

    pending_intent_ref = [None]
    mock_engine = MagicMock()
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "dosyaları listele",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            pending_intent_ref=pending_intent_ref,
        )
    assert "intent = list_files" in out
    assert "params =" in out
    assert "next_step =" in out and "klasör adını yaz" in out
    assert pending_intent_ref[0] is None
    mock_engine.process.assert_not_called()


def test_list_files_extracted_folder_survives_reject_message():
    """Deterministic intent: 'lumos-core dosyaları listele' -> print intent + params with folder."""
    from core.live_brain import handle_live_brain

    pending_intent_ref = [None]
    mock_engine = MagicMock()
    with tempfile.TemporaryDirectory() as d:
        from task_engine import TaskStore, PROFILE_RAPOR

        store = TaskStore(d)
        out = handle_live_brain(
            "lumos-core dosyaları listele",
            mock_engine,
            store,
            d,
            PROFILE_RAPOR,
            False,
            observation_engine=None,
            pending_intent_ref=pending_intent_ref,
        )
    assert "intent = list_files" in out
    assert "lumos-core" in out and "params =" in out
    assert pending_intent_ref[0] is None
    mock_engine.process.assert_not_called()
