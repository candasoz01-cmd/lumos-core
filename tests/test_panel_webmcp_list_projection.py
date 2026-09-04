"""TD-27 — lumos-list-tasks yerel projeksiyon beyanı ve ayrışma kilidi.

Davranış değişmez: liste hâlâ panelGorevlerTasks'ten okunur, Tasks API'ye
gitmez. Ajan başarılı yanıtta bunu `source: local_projection` ile görür.
"""

from __future__ import annotations

from pathlib import Path

_RUNTIME = (
    Path(__file__).resolve().parents[1]
    / "ui"
    / "src"
    / "components"
    / "panel"
    / "PanelRuntime.astro"
)


def _src() -> str:
    return _RUNTIME.read_text(encoding="utf-8")


def _list_body(src: str) -> str:
    start = src.index("async function panelWebMcpListTasks(")
    return src[start : src.index("function panelWebMcpEnsureTasksModuleVisible(")]


def test_successful_list_declares_local_projection() -> None:
    body = _list_body(_src())
    assert 'source: "local_projection"' in body
    assert "authoritative: false" in body
    # Ret yolu bu alanları taşımaz — başarıya özgü beyan.
    refusal = _src()
    start = refusal.index("function panelWebMcpReadRefusal(")
    ref_body = refusal[start : refusal.index("async function panelWebMcpRequestReadConsent(")]
    assert "local_projection" not in ref_body
    assert "authoritative" not in ref_body


def test_list_does_not_call_tasks_api() -> None:
    body = _list_body(_src())
    assert "tasksApiPost" not in body
    assert "tasksApiGet" not in body
    assert "fetch(" not in body
    assert "/tasks" not in body
    assert "XMLHttpRequest" not in body


def test_list_reads_in_memory_board_not_server() -> None:
    body = _list_body(_src())
    assert "panelGorevlerTasks[i]" in body
    assert "panelWebMcpTaskView" in body
    # Önce bellek dizisi, sonra dönüş — API ara katmanı yok.
    assert body.index("panelGorevlerTasks.length") < body.index('source: "local_projection"')


def test_divergence_from_rejected_replay_is_possible() -> None:
    """Yerel tahta, sunucunun reddettiği replay satırını tutabilir (TD-25).

    list bu diziyi olduğu gibi yansıtır; sunucu kapısından geçmez. Bu test
    o ayrışmanın *mümkün* olduğunu kilitler — kapatmaz.
    """
    src = _src()
    body = _list_body(src)
    assert "panelGorevlerTasks" in body
    # Replay reddi yerel kaydı silmez; list o kaydı okuyabilir.
    assert "replayEvidencePendingOp" in src
    replay_start = src.index("async function replayEvidencePendingOp(")
    replay = src[replay_start : src.index("function scheduleEvidenceQueueFlush(")]
    # Red yolunda yerel diziyi boşaltan bir çağrı yok (sessiz kalma, TD-25).
    assert "panelGorevlerTasks.length = 0" not in replay
    assert "panelGorevlerTasks.splice" not in replay
    assert "panelGorevlerTasks.pop" not in replay
