"""S1: classify_sensitivity does not decide the current gate.

The patch pipeline still classifies paths. lumos_gate and the panel action
gate do not read that classification.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import core.write_interceptor as write_interceptor
from core.change_sensitivity import ChangeSensitivity, classify_sensitivity
from core.panel_bridge_state import task_action_gate
from kando_runtime.lumos_gate import (
    _risk_gate_execution_mode,
    classify_risk,
)
from policy.action_policy import check_policy

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GATE_SOURCE = _REPO_ROOT / "packages/kando_runtime/src/kando_runtime/lumos_gate.py"


def _path(tmp_path: Path, rel: str) -> Path:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# fixture", encoding="utf-8")
    return path


def test_same_text_keeps_the_same_risk_on_critical_and_low_paths(tmp_path: Path):
    critical = _path(tmp_path, "src/security/lock.py")
    low = _path(tmp_path, "tests/fixture.py")
    assert classify_sensitivity(critical) is ChangeSensitivity.CRITICAL
    assert classify_sensitivity(low) is ChangeSensitivity.LOW

    low_text = "bunu özetle"
    assert classify_risk(low_text, str(critical)) == "low"
    assert classify_risk(low_text, str(low)) == "low"
    assert _risk_gate_execution_mode(classify_risk(low_text, str(critical))) == "direct_patch"

    high_text = "delete the file"
    assert classify_risk(high_text, str(low)) == "high"
    assert classify_risk(high_text, str(critical)) == "high"
    assert _risk_gate_execution_mode(classify_risk(high_text, str(critical))) == "pending_approval"


def test_classify_risk_discards_the_file_path():
    source = inspect.getsource(classify_risk)
    assert "_ = file_path" in source


def test_gate_modules_do_not_import_classify_sensitivity():
    gate = _GATE_SOURCE.read_text(encoding="utf-8")
    assert "classify_sensitivity" not in gate
    assert "change_sensitivity" not in gate

    panel_gate = inspect.getsource(task_action_gate)
    assert "classify_sensitivity" not in panel_gate
    assert "path" not in inspect.signature(task_action_gate).parameters

    policy = inspect.getsource(check_policy)
    assert "classify_sensitivity" not in policy


def test_write_interceptor_still_owns_sensitivity():
    source = inspect.getsource(write_interceptor)
    assert "classify_sensitivity" in source
