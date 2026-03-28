"""core.patch_pipeline_lifecycle: intent → … → verify özeti."""
from core.patch_pipeline_lifecycle import (
    build_pipeline_snapshot,
    enrich_pipeline_with_execution,
    format_pipeline_summary_line,
)


def test_patch_pending_pipeline():
    class S:
        kind = "safe_local"
        output = "patch_pending_approval\nDIFF:"

    class T:
        steps = [S()]
        error_summary = ""
        status = "tamamlandi"

    snap = build_pipeline_snapshot("patch: x.txt\ny", T(), True)
    assert snap["current_stage"] == "apply"
    assert snap["awaiting_user_action"] == "görev: onayla"
    assert any(s["id"] == "patch_produce" and s["state"] == "done" for s in snap["stages"])


def test_enrich_instruction_pending():
    snap = enrich_pipeline_with_execution(
        None,
        {"execution_result": "pending_approval"},
        "TARGET: a.txt\nx",
    )
    assert snap["variant"] == "instruction_target"


def test_format_line_contains_stages():
    snap = build_pipeline_snapshot("patch: f\nc", None, False)
    line = format_pipeline_summary_line(snap)
    assert "intent" in line and "plan" in line
