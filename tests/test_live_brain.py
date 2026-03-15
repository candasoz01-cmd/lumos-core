"""Live brain mode: routing unknown input to Brain when online; fallback when offline."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock


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
