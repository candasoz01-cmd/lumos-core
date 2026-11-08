"""Production head attestation stays outside the commit and off PR code."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lumos_board.head_attestation import (
    CHECK_NAME,
    ENVIRONMENT_NAME,
    REASON_EXPIRED,
    REASON_INACTIVE,
    REASON_MISMATCH,
    REASON_OK,
    REASON_PR_CODE,
    REASON_SHA,
    REASON_TRIGGER,
    REASON_UNCONFIGURED,
    REASON_UNAUTHORIZED,
    SIGN_BOARD_REF,
    authorize_dispatch,
    check_run_body,
    main as head_main,
    sign_head,
    verify_head,
)
from lumos_board.task_claim import ClaimError, ClaimStatus, TaskClaim

SECRET = "production-secret-value-must-not-leak-32"
HEAD = "a" * 40
OTHER = "b" * 40
NOW = datetime(2026, 10, 13, 5, 0, tzinfo=timezone.utc)


def _claim(*, status: ClaimStatus = ClaimStatus.ACTIVE, expires_at: datetime | None = None) -> TaskClaim:
    started = NOW - timedelta(minutes=5)
    return TaskClaim(
        claim_id="96d276ea-029c-475d-81ff-aef699291828",
        task_id="CB-007",
        repo="lumos-core",
        branch="cursor/write-attest-sign-eff5",
        worktree="/workspace",
        owner="cursor-cloud",
        scopes=(".github/workflows/write-attest-sign.yml",),
        status=status,
        started_at=started,
        heartbeat_at=started,
        expires_at=expires_at or (NOW + timedelta(hours=1)),
    )


def test_unauthorized_trigger_is_refused() -> None:
    try:
        authorize_dispatch(
            event_name="pull_request",
            ref="refs/heads/main",
            code_sha=HEAD,
            main_sha=HEAD,
        )
    except ClaimError as exc:
        assert str(exc) == REASON_TRIGGER
    else:
        raise AssertionError("pull_request must not sign")


def test_dispatch_off_main_is_refused() -> None:
    try:
        authorize_dispatch(
            event_name="workflow_dispatch",
            ref="refs/heads/cursor/write-attest-sign-eff5",
            code_sha=HEAD,
            main_sha=HEAD,
        )
    except ClaimError as exc:
        assert str(exc) == REASON_TRIGGER
    else:
        raise AssertionError("a non-main ref must not sign")


def test_pr_checkout_cannot_sign() -> None:
    try:
        authorize_dispatch(
            event_name="workflow_dispatch",
            ref="refs/heads/main",
            code_sha=OTHER,
            main_sha=HEAD,
        )
    except ClaimError as exc:
        assert str(exc) == REASON_PR_CODE
    else:
        raise AssertionError("PR code must not sign")


def test_active_claim_signs_and_verifies() -> None:
    claim = _claim()
    token = sign_head(
        secret=SECRET,
        head_sha=HEAD,
        claim=claim,
        trailer_claim_ids=(claim.claim_id,),
        actor="candasoz01-cmd",
        now=NOW,
    )
    assert SECRET not in token
    verdict = verify_head(
        secret=SECRET,
        token=token,
        head_sha=HEAD,
        claim=claim,
        trailer_claim_ids=(claim.claim_id,),
        now=NOW,
    )
    assert verdict.allowed is True
    assert verdict.reason == REASON_OK


def test_claim_mismatch_is_refused() -> None:
    claim = _claim()
    try:
        sign_head(
            secret=SECRET,
            head_sha=HEAD,
            claim=claim,
            trailer_claim_ids=("4998251d-c3fd-42ce-9230-c815477b1f27",),
            actor="candasoz01-cmd",
            now=NOW,
        )
    except ClaimError as exc:
        assert str(exc) == REASON_MISMATCH
    else:
        raise AssertionError("trailer claim must match")


def test_expired_claim_is_refused() -> None:
    claim = _claim(expires_at=NOW - timedelta(seconds=1))
    try:
        sign_head(
            secret=SECRET,
            head_sha=HEAD,
            claim=claim,
            trailer_claim_ids=(claim.claim_id,),
            actor="candasoz01-cmd",
            now=NOW,
        )
    except ClaimError as exc:
        assert str(exc) == REASON_EXPIRED
    else:
        raise AssertionError("expired claim must not sign")
    stored = sign_head(
        secret=SECRET,
        head_sha=HEAD,
        claim=_claim(),
        trailer_claim_ids=(_claim().claim_id,),
        actor="candasoz01-cmd",
        now=NOW,
    )
    verdict = verify_head(
        secret=SECRET,
        token=stored,
        head_sha=HEAD,
        claim=claim,
        trailer_claim_ids=(claim.claim_id,),
        now=NOW,
    )
    assert verdict.allowed is False
    assert verdict.reason == REASON_EXPIRED


def test_tampered_token_is_unauthorized() -> None:
    claim = _claim()
    token = sign_head(
        secret=SECRET,
        head_sha=HEAD,
        claim=claim,
        trailer_claim_ids=(claim.claim_id,),
        actor="candasoz01-cmd",
        now=NOW,
    )
    verdict = verify_head(
        secret=SECRET,
        token=token + "x",
        head_sha=HEAD,
        claim=claim,
        trailer_claim_ids=(claim.claim_id,),
        now=NOW,
    )
    assert verdict.allowed is False
    assert verdict.reason == REASON_UNAUTHORIZED


def test_inactive_claim_is_refused() -> None:
    claim = _claim(status=ClaimStatus.RELEASED)
    try:
        sign_head(
            secret=SECRET,
            head_sha=HEAD,
            claim=claim,
            trailer_claim_ids=(claim.claim_id,),
            actor="candasoz01-cmd",
            now=NOW,
        )
    except ClaimError as exc:
        assert str(exc) == REASON_INACTIVE
    else:
        raise AssertionError("released claim must not sign")


def test_missing_secret_is_refused_and_not_echoed() -> None:
    try:
        sign_head(
            secret=None,
            head_sha=HEAD,
            claim=_claim(),
            trailer_claim_ids=(_claim().claim_id,),
            actor="candasoz01-cmd",
            now=NOW,
        )
    except ClaimError as exc:
        assert str(exc) == REASON_UNCONFIGURED
        assert SECRET not in str(exc)
    else:
        raise AssertionError("missing secret must fail closed")


def test_cli_output_does_not_contain_the_secret(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.delenv("LUMOS_WRITE_GATE_SECRET", raising=False)  # type: ignore[attr-defined]
    monkeypatch.setenv("LUMOS_WRITE_GATE_SECRET", SECRET)  # type: ignore[attr-defined]
    code = head_main(["sign", "--secret", SECRET, "--event-name", "workflow_dispatch"])
    assert code == 2
    captured = tmp_path / "out.txt"
    env = os.environ.copy()
    env["LUMOS_WRITE_GATE_SECRET"] = SECRET
    result = subprocess.run(
        [
            "python3",
            "-m",
            "lumos_board.head_attestation",
            "sign",
            "--event-name",
            "pull_request",
            "--ref",
            "refs/heads/main",
            "--code-sha",
            HEAD,
            "--main-sha",
            HEAD,
        ],
        cwd=Path(__file__).resolve().parents[1],
        env={**env, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
        check=False,
    )
    captured.write_text(result.stdout + result.stderr, encoding="utf-8")
    assert SECRET not in captured.read_text(encoding="utf-8")
    assert result.returncode == 2
    assert REASON_TRIGGER in result.stderr


def _other_claim(*, expires_at: datetime) -> TaskClaim:
    started = expires_at - timedelta(minutes=5)
    return TaskClaim(
        claim_id="cbf82326-f320-4bdd-bf5a-b9fe30f16342",
        task_id="CB-004",
        repo="lumos-core",
        branch="claude/other",
        worktree="/tmp/other",
        owner="claude-cloud",
        scopes=("ops/claim_guard",),
        status=ClaimStatus.ACTIVE,
        started_at=started,
        heartbeat_at=started,
        expires_at=expires_at,
    )


def _board_snapshot(repo: Path, claims: list[TaskClaim]) -> str:
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True, text=True)
    for key, value in (("user.email", "sign-test@example.com"), ("user.name", "sign-test")):
        subprocess.run(["git", "-C", str(repo), "config", key, value], check=True, capture_output=True, text=True)
    payload = {"schema": "lumos.task_claim_store.v1", "claims": [claim.to_dict() for claim in claims]}
    (repo / "claims.json").write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "claims.json"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "board snapshot"],
        check=True,
        capture_output=True,
        text=True,
    )
    sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", SIGN_BOARD_REF, sha],
        check=True,
        capture_output=True,
        text=True,
    )
    return sha


def _sign_argv(repo: Path, message: Path, claim_id: str) -> list[str]:
    return [
        "sign",
        "--event-name",
        "workflow_dispatch",
        "--ref",
        "refs/heads/main",
        "--code-sha",
        HEAD,
        "--main-sha",
        HEAD,
        "--repo",
        str(repo),
        "--head-sha",
        HEAD,
        "--claim-id",
        claim_id,
        "--actor",
        "candasoz01-cmd",
        "--message-file",
        str(message),
    ]


def _forbid_board_writes(monkeypatch: object) -> list[list[str]]:
    calls: list[list[str]] = []

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("signing path must not call list_claims")

    monkeypatch.setattr("lumos_board.central_store.CentralClaimStore.list_claims", refuse)  # type: ignore[attr-defined]
    monkeypatch.setattr("lumos_board.task_claim.TaskClaimStore.list_claims", refuse)  # type: ignore[attr-defined]
    real_run = subprocess.run

    def spy(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        argv = [str(item) for item in args]
        calls.append(argv)
        if any(token in {"push", "fetch", "commit-tree", "mktree"} for token in argv):
            raise AssertionError("signing path must not write the board: " + " ".join(argv))
        return real_run(args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("lumos_board.head_attestation.subprocess.run", spy)  # type: ignore[attr-defined]
    return calls


def _board_sha(repo: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", SIGN_BOARD_REF],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_cli_signs_without_push_when_another_active_claim_is_stale(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    moment = datetime.now(timezone.utc)
    target = _claim(expires_at=moment + timedelta(hours=2))
    repo = tmp_path / "repo"
    before = _board_snapshot(repo, [target, _other_claim(expires_at=moment - timedelta(seconds=1))])
    message = tmp_path / "message.txt"
    message.write_text(f"feat: sign\n\nLumos-Claim: {target.claim_id}\n", encoding="utf-8")
    monkeypatch.setenv("LUMOS_WRITE_GATE_SECRET", SECRET)  # type: ignore[attr-defined]
    calls = _forbid_board_writes(monkeypatch)
    code = head_main(_sign_argv(repo, message, target.claim_id))
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert code == 0
    body = json.loads(captured.out)
    assert body["claim_id"] == target.claim_id
    assert SECRET not in captured.out
    assert _board_sha(repo) == before
    shown = [argv for argv in calls if "show" in argv]
    assert shown
    assert all(f"{SIGN_BOARD_REF}:claims.json" in argv for argv in shown)
    assert not any("push" in argv or "fetch" in argv for argv in calls)


def test_cli_refuses_expired_claim_without_push(tmp_path: Path, monkeypatch: object, capsys: object) -> None:
    moment = datetime.now(timezone.utc)
    target = _claim(expires_at=moment - timedelta(seconds=1))
    repo = tmp_path / "repo"
    before = _board_snapshot(repo, [target, _other_claim(expires_at=moment - timedelta(minutes=30))])
    message = tmp_path / "message.txt"
    message.write_text(f"feat: sign\n\nLumos-Claim: {target.claim_id}\n", encoding="utf-8")
    monkeypatch.setenv("LUMOS_WRITE_GATE_SECRET", SECRET)  # type: ignore[attr-defined]
    calls = _forbid_board_writes(monkeypatch)
    code = head_main(_sign_argv(repo, message, target.claim_id))
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert code == 2
    assert REASON_EXPIRED in captured.err
    assert SECRET not in captured.out + captured.err
    assert "attestation" not in captured.out
    assert _board_sha(repo) == before
    assert not any("push" in argv or "fetch" in argv for argv in calls)


def test_check_run_body_binds_head_sha_without_the_secret() -> None:
    token = sign_head(
        secret=SECRET,
        head_sha=HEAD,
        claim=_claim(),
        trailer_claim_ids=(_claim().claim_id,),
        actor="candasoz01-cmd",
        now=NOW,
    )
    body = check_run_body(attestation=token, head_sha=HEAD)
    encoded = json.dumps(body)
    assert body["name"] == CHECK_NAME
    assert body["head_sha"] == HEAD
    assert SECRET not in encoded
    try:
        check_run_body(attestation=token, head_sha="short")
    except ClaimError as exc:
        assert str(exc) == REASON_SHA
    else:
        raise AssertionError("check run must bind a full sha")


def test_workflow_is_dispatch_on_main_and_hides_the_secret() -> None:
    text = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "write-attest-sign.yml"
    ).read_text(encoding="utf-8")
    on_block = text.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    assert "workflow_dispatch:" in on_block
    assert "pull_request" not in on_block
    assert f"environment: {ENVIRONMENT_NAME}" in text
    assert "github.ref == 'refs/heads/main'" in text
    assert "ref: refs/heads/main" in text
    assert "git checkout" not in text
    assert "echo \"$LUMOS_WRITE_GATE_SECRET\"" not in text
    assert "echo $LUMOS_WRITE_GATE_SECRET" not in text
    assert "--secret" not in text
    secret_at = text.index("LUMOS_WRITE_GATE_SECRET: ${{ secrets.LUMOS_WRITE_GATE_SECRET }}")
    environment_at = text.index(f"environment: {ENVIRONMENT_NAME}")
    assert environment_at < secret_at
    assert text.count("secrets.LUMOS_WRITE_GATE_SECRET") == 1
    assert (
        "git fetch --no-tags origin +refs/heads/claude/lumos-board:refs/remotes/origin/claude/lumos-board"
        in text
    )
