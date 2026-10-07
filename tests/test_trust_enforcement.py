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


def _old_log(tmp_path: Path) -> Path:
    log_dir = tmp_path / ".lumos" / "logs"
    log_dir.mkdir(parents=True)
    old = log_dir / "2020-01-01.log"
    old.write_text("{}\n", encoding="utf-8")
    return old


def test_chat_telemetry_write_removes_expired_audit_logs(tmp_path: Path) -> None:
    from kando_runtime.lumos_audit import append_chat_turn_telemetry

    old = _old_log(tmp_path)
    log_id = append_chat_turn_telemetry(
        tmp_path, user_message="selam", intent="i", reply="r"
    )
    assert not old.exists()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".log"
    assert log_id in (tmp_path / ".lumos" / "logs" / today).read_text(encoding="utf-8")


def test_bridge_gate_audit_write_removes_expired_audit_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kando_bridge import server

    monkeypatch.setattr(server, "ROOT", tmp_path)
    old = _old_log(tmp_path)
    entry = {"schema_version": "lumos.audit_log.v1", "log_id": "abc"}
    assert server.BridgeHandler._append_gate_audit_log(
        None, {"lumos_audit_log": entry}  # type: ignore[arg-type]
    )
    assert not old.exists()


def test_audit_write_survives_retention_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kando_runtime import lumos_audit

    def boom(*_a, **_k):
        raise OSError("unlink failed")

    monkeypatch.setattr(lumos_audit, "cleanup_audit_logs", boom)
    lumos_audit.append_audit_log(tmp_path, {"log_id": "keep"})
    assert lumos_audit.find_audit_entry(tmp_path, "keep") == {"log_id": "keep"}


def test_cleanup_continues_after_an_undeletable_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_dir = tmp_path / ".lumos" / "logs"
    log_dir.mkdir(parents=True)
    for name in ("2020-01-01.log", "2020-01-02.log"):
        (log_dir / name).write_text("{}\n", encoding="utf-8")
    real_unlink = Path.unlink

    def flaky(self: Path, *a, **k):
        if self.name == "2020-01-01.log":
            raise PermissionError("locked")
        return real_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", flaky)
    assert cleanup_audit_logs(tmp_path, max_age_days=14) == ["2020-01-02.log"]


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
