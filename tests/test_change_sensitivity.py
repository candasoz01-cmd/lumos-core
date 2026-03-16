from __future__ import annotations

from pathlib import Path

from core.change_sensitivity import ChangeSensitivity, classify_sensitivity


def _under_src(tmp_path: Path, rel: str) -> Path:
    src = tmp_path / "src"
    p = src / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# test", encoding="utf-8")
    return p


def test_core_path_is_critical(tmp_path: Path):
    p = _under_src(tmp_path, "core/workspace_contract.py")
    assert classify_sensitivity(p) == ChangeSensitivity.CRITICAL


def test_policy_path_is_critical(tmp_path: Path):
    p = _under_src(tmp_path, "policy/rules.py")
    assert classify_sensitivity(p) == ChangeSensitivity.CRITICAL


def test_security_path_is_critical(tmp_path: Path):
    p = _under_src(tmp_path, "security/crypto.py")
    assert classify_sensitivity(p) == ChangeSensitivity.CRITICAL


def test_engine_path_is_high(tmp_path: Path):
    p = _under_src(tmp_path, "engine/model_client.py")
    assert classify_sensitivity(p) == ChangeSensitivity.HIGH


def test_task_engine_path_is_high(tmp_path: Path):
    p = _under_src(tmp_path, "task_engine/engine.py")
    assert classify_sensitivity(p) == ChangeSensitivity.HIGH


def test_tools_path_is_normal(tmp_path: Path):
    p = _under_src(tmp_path, "tools/run_classify.py")
    assert classify_sensitivity(p) == ChangeSensitivity.NORMAL


def test_scripts_path_is_normal(tmp_path: Path):
    p = _under_src(tmp_path, "scripts/init_keystore.py")
    assert classify_sensitivity(p) == ChangeSensitivity.NORMAL


def test_docs_path_is_low(tmp_path: Path):
    p = _under_src(tmp_path, "docs/README.md")
    assert classify_sensitivity(p) == ChangeSensitivity.LOW


def test_tests_path_is_low(tmp_path: Path):
    p = _under_src(tmp_path, "tests/test_something.py")
    assert classify_sensitivity(p) == ChangeSensitivity.LOW

