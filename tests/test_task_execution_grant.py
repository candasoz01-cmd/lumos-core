"""ADR-031 task execution grant kernel tests."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from policy.task_execution_grant import (
    CLASSIFICATION_UNCLASSIFIED,
    DEFAULT_TTL_SECONDS,
    ENV_ENABLED,
    EVENT_DENIED,
    EVENT_ISSUED,
    GRANTS_DIR,
    REASON_BINDING_INCOMPLETE,
    REASON_DISABLED,
    REASON_EXPIRED,
    REASON_MALFORMED,
    REASON_MISMATCH,
    REASON_MISSING,
    REASON_SURFACE_BLOCKED,
    REASON_UNKNOWN,
    REASON_USED,
    SUSPICION_HIGH,
    SUSPICION_MEDIUM,
    ExecutionBinding,
    action_is_grant_forbidden,
    consume_task_execution_grant,
    issue_task_execution_grant,
    require_task_execution_grant,
    token_hash,
)


@pytest.fixture(autouse=True)
def _clear_grant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_ENABLED, raising=False)


def _binding(**overrides: str) -> ExecutionBinding:
    data = {
        "subject_id": "user:alice",
        "task_id": "task-file-1",
        "action_key": "file_read",
        "resource": "notes/readme.md",
        "permission": "read",
    }
    data.update(overrides)
    return ExecutionBinding(**data)


def _audit_events(base: Path) -> list[dict]:
    path = base / "logs" / "task_execution_grant.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_disabled_require_is_noop(tmp_path: Path) -> None:
    result = require_task_execution_grant(
        "",
        _binding(),
        base_dir=tmp_path,
    )
    assert result.allowed
    assert result.reason == REASON_DISABLED
    assert _audit_events(tmp_path) == []


def test_issue_and_consume_once(tmp_path: Path) -> None:
    binding = _binding()
    issued = issue_task_execution_grant(binding, base_dir=tmp_path)
    path = tmp_path / GRANTS_DIR / f"{issued.grant_id}.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert "token" not in stored
    assert stored["token_hash"] == issued.token_hash
    assert issued.token not in path.read_text(encoding="utf-8")

    first = consume_task_execution_grant(issued.token, binding, base_dir=tmp_path)
    assert first.allowed
    second = consume_task_execution_grant(issued.token, binding, base_dir=tmp_path)
    assert not second.allowed
    assert second.reason == REASON_USED
    assert second.suspicion == SUSPICION_HIGH
    assert second.classification == CLASSIFICATION_UNCLASSIFIED


def test_file_read_grant_cannot_send_mail(tmp_path: Path) -> None:
    issued = issue_task_execution_grant(_binding(), base_dir=tmp_path)
    mail = _binding(action_key="mail_send", task_id="task-mail-1", permission="send")
    result = consume_task_execution_grant(issued.token, mail, base_dir=tmp_path)
    assert not result.allowed
    assert result.reason == REASON_MISMATCH
    assert result.suspicion == SUSPICION_HIGH
    still = consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path)
    assert still.allowed


def test_wrong_subject_or_resource_mismatch(tmp_path: Path) -> None:
    issued = issue_task_execution_grant(_binding(), base_dir=tmp_path)
    other_user = consume_task_execution_grant(
        issued.token,
        _binding(subject_id="user:mallory"),
        base_dir=tmp_path,
    )
    assert not other_user.allowed
    assert other_user.reason == REASON_MISMATCH
    other_file = consume_task_execution_grant(
        issued.token,
        _binding(resource="secrets/wallet.txt"),
        base_dir=tmp_path,
    )
    assert not other_file.allowed


def test_missing_token_is_deny_not_attacker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    result = require_task_execution_grant("", _binding(), base_dir=tmp_path)
    assert not result.allowed
    assert result.reason == REASON_MISSING
    assert result.suspicion == SUSPICION_HIGH
    assert result.classification == CLASSIFICATION_UNCLASSIFIED
    events = _audit_events(tmp_path)
    assert events[-1]["event_type"] == EVENT_DENIED
    assert events[-1]["classification"] == CLASSIFICATION_UNCLASSIFIED
    assert "attacker" not in json.dumps(events[-1]).lower()


def test_malformed_and_unknown_token(tmp_path: Path) -> None:
    binding = _binding()
    bad = consume_task_execution_grant("not-a-grant", binding, base_dir=tmp_path)
    assert not bad.allowed
    assert bad.reason == REASON_MALFORMED
    forged = consume_task_execution_grant(
        "teg1.aaaaaaaaaaaaaaaa.this-secret-does-not-exist",
        binding,
        base_dir=tmp_path,
    )
    assert not forged.allowed
    assert forged.reason == REASON_UNKNOWN


def test_expired_grant_medium_suspicion(tmp_path: Path) -> None:
    issued = issue_task_execution_grant(_binding(), base_dir=tmp_path, ttl_seconds=1)
    path = tmp_path / GRANTS_DIR / f"{issued.grant_id}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    past = (datetime.now(timezone.utc) - timedelta(seconds=5)).replace(microsecond=0)
    record["expires_at"] = past.isoformat().replace("+00:00", "Z")
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    result = consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path)
    assert not result.allowed
    assert result.reason == REASON_EXPIRED
    assert result.suspicion == SUSPICION_MEDIUM
    assert result.classification == CLASSIFICATION_UNCLASSIFIED


def test_never_auto_surface_cannot_be_granted(tmp_path: Path) -> None:
    assert action_is_grant_forbidden("permanent_delete")
    assert action_is_grant_forbidden("delete_permanent")
    assert action_is_grant_forbidden("external_write")
    with pytest.raises(ValueError, match=REASON_SURFACE_BLOCKED):
        issue_task_execution_grant(_binding(action_key="permanent_delete"), base_dir=tmp_path)


def test_enabled_incomplete_binding_denies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    result = require_task_execution_grant("teg1.deadbeefdeadbeef.x", None, base_dir=tmp_path)
    assert not result.allowed
    assert result.reason == REASON_BINDING_INCOMPLETE
    assert result.suspicion == SUSPICION_HIGH


def test_audit_never_contains_raw_token(tmp_path: Path) -> None:
    issued = issue_task_execution_grant(_binding(), base_dir=tmp_path)
    consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path)
    blob = (tmp_path / "logs" / "task_execution_grant.jsonl").read_text(encoding="utf-8")
    assert issued.token not in blob
    events = _audit_events(tmp_path)
    assert events[0]["event_type"] == EVENT_ISSUED
    assert events[0]["token_hash"] == token_hash(issued.token)
    assert events[0]["resource"] == "readme.md"


def test_default_ttl_is_short() -> None:
    assert DEFAULT_TTL_SECONDS == 120
    assert DEFAULT_TTL_SECONDS < 900


def test_concurrent_consume_only_one_wins(tmp_path: Path) -> None:
    issued = issue_task_execution_grant(_binding(), base_dir=tmp_path)

    def _once() -> bool:
        return consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path).allowed

    with ThreadPoolExecutor(max_workers=8) as pool:
        wins = list(pool.map(lambda _: _once(), range(8)))
    assert sum(1 for ok in wins if ok) == 1
