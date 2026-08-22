"""ADR-031: Task Registry + Capability Token + Immutable Ledger."""
from __future__ import annotations

import json
import threading
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
    REGISTRY_DIR,
    SCHEMA_REGISTRY,
    KIND_CAPABILITY_DEVIATION,
    KIND_MISSING_IDENTITY,
    KIND_REPLAY,
    KIND_UNKNOWN_TASK,
    KIND_UNREGISTERED_KEY,
    REASON_BINDING_INCOMPLETE,
    REASON_DISABLED,
    REASON_DUPLICATE_TASK,
    REASON_EXPIRED,
    REASON_IDENTITY_MISSING,
    REASON_KEY_NOT_REGISTERED,
    REASON_MALFORMED,
    REASON_MISMATCH,
    REASON_MISSING,
    REASON_SURFACE_BLOCKED,
    REASON_USED,
    SUSPICION_HIGH,
    SUSPICION_MEDIUM,
    ExecutionBinding,
    _finalize_registry_grant,
    accept_execution_task,
    action_is_grant_forbidden,
    append_ledger_entry,
    authorize_execution,
    capability_from_plan,
    consume_task_execution_grant,
    issue_task_execution_grant,
    load_ledger_entries,
    load_registered_task,
    require_task_execution_grant,
    resolve_execution_binding,
    token_hash,
    verify_ledger_chain,
)


@pytest.fixture(autouse=True)
def _clear_grant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_ENABLED, raising=False)


def _binding(**overrides: str) -> ExecutionBinding:
    data = {
        "subject_id": "user:X",
        "agent_id": "agent:kando",
        "session_id": "session:s1",
        "task_id": "G-12841",
        "action_key": "file_read",
        "resource": "notes/fileA.md",
        "permission": "read",
    }
    data.update(overrides)
    return ExecutionBinding(**data)


def _write_grant_expires_at(
    tmp_path: Path, grant_id: str, expires_at: object | None, *, drop: bool = False
) -> None:
    path = tmp_path / GRANTS_DIR / f"{grant_id}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    if drop:
        record.pop("expires_at", None)
    else:
        record["expires_at"] = expires_at
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")


def test_disabled_require_is_noop(tmp_path: Path) -> None:
    result = require_task_execution_grant("", _binding(), base_dir=tmp_path)
    assert result.allowed
    assert result.reason == REASON_DISABLED
    assert load_ledger_entries(tmp_path) == []


def test_accept_registers_task_and_mints_once(tmp_path: Path) -> None:
    binding = _binding()
    issued = accept_execution_task(binding, base_dir=tmp_path)
    registered = load_registered_task("G-12841", base_dir=tmp_path)
    assert registered is not None
    assert registered["token_hash"] == issued.token_hash
    assert registered["agent_id"] == "agent:kando"
    path = tmp_path / GRANTS_DIR / f"{issued.grant_id}.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert "token" not in stored
    assert issued.token not in path.read_text(encoding="utf-8")
    first = consume_task_execution_grant(issued.token, binding, base_dir=tmp_path)
    assert first.allowed
    second = consume_task_execution_grant(issued.token, binding, base_dir=tmp_path)
    assert not second.allowed
    assert second.reason == REASON_USED
    assert second.event_kind == KIND_REPLAY
    assert second.classification == CLASSIFICATION_UNCLASSIFIED


def test_colon_and_underscore_task_ids_are_distinct_registry_records(tmp_path: Path) -> None:
    colon = _binding(task_id="a:b")
    underscore = _binding(task_id="a_b")
    issued_colon = accept_execution_task(colon, base_dir=tmp_path)
    issued_under = accept_execution_task(underscore, base_dir=tmp_path)
    loaded_colon = load_registered_task("a:b", base_dir=tmp_path)
    loaded_under = load_registered_task("a_b", base_dir=tmp_path)
    assert loaded_colon is not None
    assert loaded_under is not None
    assert loaded_colon["task_id"] == "a:b"
    assert loaded_under["task_id"] == "a_b"
    assert loaded_colon["token_hash"] == issued_colon.token_hash
    assert loaded_under["token_hash"] == issued_under.token_hash
    registry = tmp_path / REGISTRY_DIR
    assert (registry / "a%3Ab.json").is_file()
    assert (registry / "a_b.json").is_file()
    assert (registry / "G-12841.json").is_file() is False
    hyphen = accept_execution_task(_binding(), base_dir=tmp_path)
    assert load_registered_task("G-12841", base_dir=tmp_path) is not None
    assert (registry / "G-12841.json").is_file()
    assert hyphen.token != issued_colon.token
    crossed = consume_task_execution_grant(issued_colon.token, underscore, base_dir=tmp_path)
    assert not crossed.allowed
    assert crossed.reason == REASON_KEY_NOT_REGISTERED
    own = consume_task_execution_grant(issued_colon.token, colon, base_dir=tmp_path)
    assert own.allowed


def test_issue_is_authority_accept_not_agent_mint(tmp_path: Path) -> None:
    issued = issue_task_execution_grant(_binding(), base_dir=tmp_path)
    assert load_registered_task("G-12841", base_dir=tmp_path) is not None
    with pytest.raises(ValueError, match=REASON_DUPLICATE_TASK):
        issue_task_execution_grant(_binding(), base_dir=tmp_path)
    assert issued.token.startswith("teg1.")


def test_accept_retry_recovers_incomplete_registry(tmp_path: Path) -> None:
    binding = _binding()
    path = tmp_path / REGISTRY_DIR / "G-12841.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    stub = {
        "schema_version": SCHEMA_REGISTRY,
        "task_id": binding.task_id,
        "subject_id": binding.subject_id,
        "agent_id": binding.agent_id,
        "session_id": binding.session_id,
        "action_key": binding.action_key,
        "resource": binding.resource,
        "permission": binding.permission,
        "binding_hash": "pending",
        "grant_id": "",
        "token_hash": "",
        "status": "accepted",
        "created_at": "2026-08-21T00:00:00Z",
    }
    path.write_text(json.dumps(stub, indent=2), encoding="utf-8")
    issued = accept_execution_task(binding, base_dir=tmp_path)
    registered = load_registered_task("G-12841", base_dir=tmp_path)
    assert registered is not None
    assert registered["grant_id"] == issued.grant_id
    assert registered["token_hash"] == issued.token_hash
    assert consume_task_execution_grant(issued.token, binding, base_dir=tmp_path).allowed
    with pytest.raises(ValueError, match=REASON_DUPLICATE_TASK):
        accept_execution_task(binding, base_dir=tmp_path)

    leftover = _binding(task_id="G-12842")
    leftover_path = tmp_path / REGISTRY_DIR / "G-12842.json"
    leftover_stub = dict(stub)
    leftover_stub["task_id"] = leftover.task_id
    leftover_stub["grant_id"] = "deadbeefdeadbeef"
    leftover_stub["token_hash"] = ""
    leftover_path.write_text(json.dumps(leftover_stub, indent=2), encoding="utf-8")
    recovered = accept_execution_task(leftover, base_dir=tmp_path)
    loaded = load_registered_task("G-12842", base_dir=tmp_path)
    assert loaded is not None
    assert loaded["grant_id"] == recovered.grant_id
    assert loaded["token_hash"] == recovered.token_hash
    assert consume_task_execution_grant(recovered.token, leftover, base_dir=tmp_path).allowed


def test_hung_accept_does_not_clobber_recovered_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hung first accept must not overwrite a recovered registry hash."""
    binding = _binding(task_id="G-HUNG01")
    path = tmp_path / REGISTRY_DIR / "G-HUNG01.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    stub = {
        "schema_version": SCHEMA_REGISTRY,
        "task_id": binding.task_id,
        "subject_id": binding.subject_id,
        "agent_id": binding.agent_id,
        "session_id": binding.session_id,
        "action_key": binding.action_key,
        "resource": binding.resource,
        "permission": binding.permission,
        "binding_hash": "pending",
        "grant_id": "",
        "token_hash": "",
        "status": "accepted",
        "created_at": "2026-08-22T00:00:00Z",
    }
    path.write_text(json.dumps(stub, indent=2), encoding="utf-8")

    widened = _binding(task_id="G-HUNG01", action_key="mail_send", permission="send")
    with pytest.raises(ValueError, match=REASON_DUPLICATE_TASK):
        accept_execution_task(widened, base_dir=tmp_path)
    stalled = json.loads(path.read_text(encoding="utf-8"))
    assert stalled["grant_id"] == ""
    assert stalled["action_key"] == binding.action_key

    recovered = accept_execution_task(binding, base_dir=tmp_path)
    registered = load_registered_task("G-HUNG01", base_dir=tmp_path)
    assert registered is not None
    assert registered["grant_id"] == recovered.grant_id
    assert registered["token_hash"] == recovered.token_hash

    hung_grant_id = "cafebabecafebabe"
    hung_token = f"teg1.{hung_grant_id}.hung-secret"
    with pytest.raises(ValueError, match=REASON_DUPLICATE_TASK):
        _finalize_registry_grant(
            path,
            grant_id=hung_grant_id,
            token_digest=token_hash(hung_token),
            binding=binding,
        )

    after = load_registered_task("G-HUNG01", base_dir=tmp_path)
    assert after is not None
    assert after["grant_id"] == recovered.grant_id
    assert after["token_hash"] == recovered.token_hash
    assert consume_task_execution_grant(recovered.token, binding, base_dir=tmp_path).allowed

    hung = consume_task_execution_grant(hung_token, binding, base_dir=tmp_path)
    assert not hung.allowed
    assert hung.reason == REASON_KEY_NOT_REGISTERED

    with pytest.raises(ValueError, match=REASON_DUPLICATE_TASK):
        accept_execution_task(binding, base_dir=tmp_path)
    still = load_registered_task("G-HUNG01", base_dir=tmp_path)
    assert still is not None
    assert still["token_hash"] == recovered.token_hash

    race = _binding(task_id="G-HUNG02")
    hung_at_finalize = threading.Event()
    recovered_done = threading.Event()
    hung_errors: list[BaseException] = []
    orig_finalize = _finalize_registry_grant
    first = {"seen": False}

    def pausing_finalize(*args: object, **kwargs: object) -> None:
        if not first["seen"]:
            first["seen"] = True
            hung_at_finalize.set()
            assert recovered_done.wait(timeout=5.0)
        orig_finalize(*args, **kwargs)

    monkeypatch.setattr(
        "policy.task_execution_grant._finalize_registry_grant",
        pausing_finalize,
    )

    def hung_worker() -> None:
        try:
            accept_execution_task(race, base_dir=tmp_path)
        except ValueError as exc:
            hung_errors.append(exc)

    worker = threading.Thread(target=hung_worker)
    worker.start()
    assert hung_at_finalize.wait(timeout=5.0)
    recovered_race = accept_execution_task(race, base_dir=tmp_path)
    recovered_done.set()
    worker.join(timeout=5.0)
    assert not worker.is_alive()
    assert hung_errors and str(hung_errors[0]) == REASON_DUPLICATE_TASK
    raced = load_registered_task("G-HUNG02", base_dir=tmp_path)
    assert raced is not None
    assert raced["grant_id"] == recovered_race.grant_id
    assert raced["token_hash"] == recovered_race.token_hash
    assert consume_task_execution_grant(recovered_race.token, race, base_dir=tmp_path).allowed


def test_unknown_task_denied_before_execute(tmp_path: Path) -> None:
    result = consume_task_execution_grant(
        "teg1.aaaaaaaaaaaaaaaa.not-registered",
        _binding(),
        base_dir=tmp_path,
    )
    assert not result.allowed
    assert result.reason == "task_execution_grant_unknown_task"
    assert result.event_kind == KIND_UNKNOWN_TASK
    assert result.suspicion == SUSPICION_HIGH


def test_registered_task_wrong_key_is_unregistered(tmp_path: Path) -> None:
    accept_execution_task(_binding(), base_dir=tmp_path)
    result = consume_task_execution_grant(
        "teg1.bbbbbbbbbbbbbbbb.forged-secret-value",
        _binding(),
        base_dir=tmp_path,
    )
    assert not result.allowed
    assert result.reason == REASON_KEY_NOT_REGISTERED
    assert result.event_kind == KIND_UNREGISTERED_KEY


def test_file_read_grant_cannot_send_mail(tmp_path: Path) -> None:
    issued = accept_execution_task(_binding(), base_dir=tmp_path)
    mail = _binding(action_key="mail_send", permission="send")
    result = consume_task_execution_grant(issued.token, mail, base_dir=tmp_path)
    assert not result.allowed
    assert result.reason == REASON_MISMATCH
    assert result.event_kind == KIND_CAPABILITY_DEVIATION
    still = consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path)
    assert still.allowed


def test_wrong_subject_or_resource_mismatch(tmp_path: Path) -> None:
    issued = accept_execution_task(_binding(), base_dir=tmp_path)
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


def test_missing_identity_never_reaches_executor(tmp_path: Path) -> None:
    result = authorize_execution(
        "teg1.cccccccccccccccc.x",
        subject_id="",
        task_id="G-12841",
        action_key="file_read",
        resource="fileA",
        permission="read",
        base_dir=tmp_path,
    )
    assert not result.allowed
    assert result.reason == REASON_IDENTITY_MISSING
    assert result.event_kind == KIND_MISSING_IDENTITY
    assert result.classification == CLASSIFICATION_UNCLASSIFIED


def test_missing_token_on_registered_task_is_not_attacker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    accept_execution_task(_binding(), base_dir=tmp_path)
    result = require_task_execution_grant("", _binding(), base_dir=tmp_path)
    assert not result.allowed
    assert result.reason == REASON_MISSING
    assert result.event_kind == KIND_UNREGISTERED_KEY
    assert result.classification == CLASSIFICATION_UNCLASSIFIED
    events = load_ledger_entries(tmp_path)
    denied = [row for row in events if row["event_type"] == EVENT_DENIED]
    assert denied[-1]["classification"] == CLASSIFICATION_UNCLASSIFIED
    assert "attacker" not in json.dumps(denied[-1]).lower()


def test_malformed_token_on_registered_task(tmp_path: Path) -> None:
    accept_execution_task(_binding(), base_dir=tmp_path)
    bad = consume_task_execution_grant("not-a-grant", _binding(), base_dir=tmp_path)
    assert not bad.allowed
    assert bad.reason == REASON_MALFORMED


def test_expired_grant_medium_suspicion(tmp_path: Path) -> None:
    issued = accept_execution_task(_binding(), base_dir=tmp_path, ttl_seconds=1)
    past = (datetime.now(timezone.utc) - timedelta(seconds=5)).replace(microsecond=0)
    _write_grant_expires_at(
        tmp_path, issued.grant_id, past.isoformat().replace("+00:00", "Z")
    )
    result = consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path)
    assert not result.allowed
    assert result.reason == REASON_EXPIRED
    assert result.suspicion == SUSPICION_MEDIUM


@pytest.mark.parametrize(
    "expires_at,drop",
    [
        (None, True),
        ("garbage", False),
        (12345, False),
        ("2020-01-01T00:00:00", False),
        (None, False),
    ],
)
def test_invalid_expires_at_is_fail_closed(
    tmp_path: Path, expires_at: object | None, drop: bool
) -> None:
    issued = accept_execution_task(_binding(), base_dir=tmp_path)
    _write_grant_expires_at(tmp_path, issued.grant_id, expires_at, drop=drop)
    result = consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path)
    assert not result.allowed
    assert result.reason == REASON_MALFORMED


def test_aware_future_z_expiry_still_allows(tmp_path: Path) -> None:
    issued = accept_execution_task(_binding(), base_dir=tmp_path)
    future = (datetime.now(timezone.utc) + timedelta(seconds=60)).replace(microsecond=0)
    _write_grant_expires_at(
        tmp_path, issued.grant_id, future.isoformat().replace("+00:00", "Z")
    )
    result = consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path)
    assert result.allowed


def test_never_auto_surface_cannot_be_granted(tmp_path: Path) -> None:
    assert action_is_grant_forbidden("permanent_delete")
    with pytest.raises(ValueError, match=REASON_SURFACE_BLOCKED):
        accept_execution_task(_binding(action_key="permanent_delete"), base_dir=tmp_path)
    assert load_registered_task("G-12841", base_dir=tmp_path) is None


def test_enabled_incomplete_binding_denies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_ENABLED, "true")
    result = require_task_execution_grant(
        "teg1.deadbeefdeadbeef.x",
        None,
        base_dir=tmp_path,
        subject_id="user:X",
    )
    assert not result.allowed
    assert result.reason == REASON_BINDING_INCOMPLETE


def test_ledger_is_evidence_not_the_gate(tmp_path: Path) -> None:
    issued = accept_execution_task(_binding(), base_dir=tmp_path)
    ledger = tmp_path / "ledgers" / "execution_ledger.jsonl"
    assert ledger.is_file()
    ledger.unlink()
    (tmp_path / "ledgers" / "execution_ledger.tip").unlink()
    assert consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path).allowed
    assert load_registered_task("G-12841", base_dir=tmp_path) is not None


def test_ledger_chain_and_no_raw_token(tmp_path: Path) -> None:
    issued = accept_execution_task(_binding(), base_dir=tmp_path)
    consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path)
    blob = (tmp_path / "ledgers" / "execution_ledger.jsonl").read_text(encoding="utf-8")
    assert issued.token not in blob
    assert verify_ledger_chain(tmp_path)
    events = load_ledger_entries(tmp_path)
    assert events[0]["event_type"] == "execution_task_accepted"
    assert any(row["event_type"] == EVENT_ISSUED for row in events)
    assert events[0]["token_hash"] == token_hash(issued.token)
    assert events[0]["resource"] == "fileA.md"
    tampered = dict(events[-1])
    tampered["subject_id"] = "user:forged"
    lines = blob.splitlines()
    lines[-1] = json.dumps(tampered)
    (tmp_path / "ledgers" / "execution_ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not verify_ledger_chain(tmp_path)


def test_default_ttl_is_short() -> None:
    assert DEFAULT_TTL_SECONDS == 120
    assert DEFAULT_TTL_SECONDS < 900


def test_concurrent_consume_only_one_wins(tmp_path: Path) -> None:
    issued = accept_execution_task(_binding(), base_dir=tmp_path)

    def _once() -> bool:
        return consume_task_execution_grant(issued.token, _binding(), base_dir=tmp_path).allowed

    with ThreadPoolExecutor(max_workers=8) as pool:
        wins = list(pool.map(lambda _: _once(), range(8)))
    assert sum(1 for ok in wins if ok) == 1


def test_concurrent_ledger_appends_preserve_chain(tmp_path: Path) -> None:
    n = 24

    def _once(i: int) -> None:
        append_ledger_entry(
            tmp_path,
            EVENT_DENIED,
            reason=f"concurrent-{i}",
            task_id=f"G-{i}",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_once, range(n)))
    entries = load_ledger_entries(tmp_path)
    assert len(entries) == n
    assert verify_ledger_chain(tmp_path) is True


def test_capability_from_plan_uses_patch_step() -> None:
    cap = capability_from_plan(
        {"steps": [{"type": "patch", "file": "notes/fileA.md", "content": "x"}]}
    )
    assert cap == ("patch", "write", "notes/fileA.md")


def test_capability_from_plan_rejects_mixed_patch_and_agent() -> None:
    cap = capability_from_plan(
        {
            "steps": [
                {"type": "patch", "file": "a.md", "content": "x"},
                {"type": "agent", "goal": "do other work"},
            ]
        }
    )
    assert cap is None


def test_file_read_metadata_versus_patch_plan_is_capability_deviation(
    tmp_path: Path,
) -> None:
    data = {
        "subject_id": "user:X",
        "task_id": "G-12841",
        "task_execution_action_key": "file_read",
        "task_execution_permission": "read",
    }
    plan = {"steps": [{"type": "patch", "file": "notes/fileA.md", "content": "x"}]}
    binding, denied = resolve_execution_binding(
        data,
        plan=plan,
        norm={"target_rel": "notes/fileA.md"},
        base_dir=tmp_path,
    )
    assert binding is None
    assert denied is not None
    assert not denied.allowed
    assert denied.reason == REASON_MISMATCH
    assert denied.event_kind == KIND_CAPABILITY_DEVIATION


def test_matching_patch_plan_binding_consumes(tmp_path: Path) -> None:
    plan = {"steps": [{"type": "patch", "file": "notes/fileA.md", "content": "x"}]}
    issued = accept_execution_task(
        _binding(action_key="patch", permission="write"), base_dir=tmp_path
    )
    expected, denied = resolve_execution_binding(
        {
            "subject_id": "user:X",
            "task_id": "G-12841",
            "agent_id": "agent:kando",
            "session_id": "session:s1",
            "task_execution_action_key": "patch",
            "task_execution_permission": "write",
            "task_execution_grant_token": issued.token,
        },
        plan=plan,
        norm={"target_rel": "notes/fileA.md"},
        base_dir=tmp_path,
    )
    assert denied is None
    assert expected is not None
    assert expected.action_key == "patch"
    assert consume_task_execution_grant(issued.token, expected, base_dir=tmp_path).allowed
