"""Minimal trust enforcement: confirmation, local retention, and hosted payload."""

from __future__ import annotations

import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from kando_runtime.lumos_audit import cleanup_audit_logs, delete_audit_logs
from memory.memory import Memory
from memory.schema import MemoryNote
from policy.confirmation_policy import is_confirmation_enabled

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _clear_product_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LUMOS_CONFIRMATION_ENABLED", raising=False)
    monkeypatch.delenv("LUMOS_ENV", raising=False)
    monkeypatch.delenv("LUMOS_PRODUCT_ENV", raising=False)
    monkeypatch.delenv("LUMOS_MEMORY_TTL_SECONDS", raising=False)


def test_production_confirmation_cannot_stay_off(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not is_confirmation_enabled()
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "false")
    assert not is_confirmation_enabled()
    monkeypatch.setenv("LUMOS_ENV", "production")
    assert is_confirmation_enabled()
    monkeypatch.setenv("LUMOS_CONFIRMATION_ENABLED", "0")
    assert is_confirmation_enabled()


def test_local_memory_ttl_and_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_MEMORY_TTL_SECONDS", "1")
    memory = Memory()
    memory._is_unlocked = True
    memory.add(
        MemoryNote(
            kind="fact",
            content="eski",
            ttl_seconds=None,
            created_at=time.time() - 30,
        )
    )
    assert memory.notes[0].ttl_seconds == 1
    memory.cleanup()
    assert memory.notes == []
    memory.add(MemoryNote(kind="fact", content="yeni"))
    assert memory.delete_all() == 1
    assert memory.notes == []


def test_audit_log_retention_cleanup(tmp_path: Path) -> None:
    log_dir = tmp_path / ".lumos" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "2020-01-01.log").write_text("{}\n", encoding="utf-8")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".log"
    (log_dir / today).write_text("{}\n", encoding="utf-8")
    removed = cleanup_audit_logs(tmp_path, max_age_days=14)
    assert removed == ["2020-01-01.log"]
    assert (log_dir / today).is_file()
    assert delete_audit_logs(tmp_path) == 1
    assert list(log_dir.glob("*.log")) == []


def test_hosted_trust_enforcement_node() -> None:
    node = shutil.which("node")
    assert node, "node is required to verify the hosted payload"
    result = subprocess.run(
        [node, "--test", "--test-concurrency=1", "tests/test_trust_enforcement.test.mjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
