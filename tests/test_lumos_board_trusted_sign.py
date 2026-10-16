"""The authorized signer copies a range onto a new branch and rejects the proof key."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from lumos_board.task_claim import ClaimStatus, TaskClaimStore
from lumos_board.trusted_sign import (
    SIGNER_OWNER,
    TrustedSignError,
    assert_authorized_context,
    assert_production_secret,
    public_proof_key,
    push_args,
    push_signed,
    rebuild_message,
    sign_range,
)
from lumos_board.write_attestation import REASON_OK, REASON_UNAUTHORIZED, ClaimGuard

SECRET = "b" * 32
OTHER = "c" * 32


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    merged = os.environ.copy()
    merged.update(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
        }
    )
    merged.pop("LUMOS_WRITE_GATE_SECRET", None)
    if env:
        merged.update(env)
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=merged,
    )
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "keep.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "keep.txt")
    _git(repo, "commit", "-m", "base")
    _git(repo, "branch", "feature")
    return repo


def _commit(repo: Path, rel: str, body: str, message: str) -> str:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    _git(repo, "add", rel)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _sign(repo: Path, store: Path, *, base: str, head: str, dest: str = "trusted-sign/pr-944") -> str:
    signed = sign_range(
        repo,
        base=base,
        head=head,
        dest=dest,
        source_branch="feature",
        store=TaskClaimStore(store),
        secret=SECRET,
        proof_key=public_proof_key(),
    )
    return signed[-1].signed


def test_proof_key_cannot_sign(tmp_path: Path) -> None:
    proof = public_proof_key()
    with pytest.raises(TrustedSignError, match="prova anahtarı"):
        assert_production_secret(proof, proof_key=proof)
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "feature")
    head = _commit(repo, "src/a.py", "a\n", "change")
    before = _git(repo, "rev-parse", "feature")
    with pytest.raises(TrustedSignError, match="prova anahtarı"):
        sign_range(
            repo,
            base=base,
            head=head,
            dest="trusted-sign/pr-1",
            source_branch="feature",
            store=TaskClaimStore(tmp_path / "board"),
            secret=proof,
            proof_key=proof,
        )
    assert _git(repo, "rev-parse", "feature") == before
    missing = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", "refs/heads/trusted-sign/pr-1"],
        check=False,
        capture_output=True,
    )
    assert missing.returncode != 0


def test_short_secret_is_unconfigured() -> None:
    with pytest.raises(TrustedSignError, match="UNCONFIGURED"):
        assert_production_secret("short", proof_key="x" * 32)
    with pytest.raises(TrustedSignError, match="UNCONFIGURED"):
        assert_production_secret(None, proof_key="x" * 32)


def test_central_context_requires_main_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_REF", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    with pytest.raises(TrustedSignError, match="refs/heads/main"):
        assert_authorized_context()
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    with pytest.raises(TrustedSignError, match="workflow_dispatch"):
        assert_authorized_context()
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    assert_authorized_context()


def test_signed_range_verifies_and_releases_claims(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "feature")
    _commit(
        repo,
        "src/a.py",
        "a\n",
        "first\n\nLumos-Claim: old\nLumos-Agent: old\nLumos-Claim-Attestation: old\nCo-authored-by: A <a@example.com>\n",
    )
    head = _commit(repo, "src/a.py", "b\n", "second")
    feature = _git(repo, "rev-parse", "feature")
    main = _git(repo, "rev-parse", "main")
    store = TaskClaimStore(tmp_path / "board")
    signed = sign_range(
        repo,
        base=base,
        head=head,
        dest="trusted-sign/pr-944",
        source_branch="feature",
        store=store,
        secret=SECRET,
        proof_key=public_proof_key(),
    )
    assert len(signed) == 2
    assert signed[0].source != signed[1].source
    assert _git(repo, "rev-parse", "feature") == feature
    assert _git(repo, "rev-parse", "main") == main
    tip = _git(repo, "rev-parse", "trusted-sign/pr-944")
    assert tip == signed[1].signed
    verdict = ClaimGuard(secret=SECRET).verify_range(repo, base=base, head=tip)
    assert verdict.allowed is True
    assert verdict.reason == REASON_OK
    other = ClaimGuard(secret=OTHER).verify_range(repo, base=base, head=tip)
    assert other.allowed is False
    assert other.reason == REASON_UNAUTHORIZED
    message = _git(repo, "log", "-1", "--format=%B", signed[0].signed)
    assert "Lumos-Claim-Attestation: old" not in message
    assert f"Lumos-Agent: {SIGNER_OWNER}" in message
    assert "Co-authored-by: A <a@example.com>" in message
    assert SECRET not in message
    assert "write_token" not in message
    parents = _git(repo, "rev-list", "--parents", "-n", "1", signed[1].signed).split()
    assert parents[1] == signed[0].signed
    claims = store.list_claims(include_closed=True)
    assert claims
    assert all(item.status is ClaimStatus.RELEASED for item in claims)
    assert store.list_claims() == ()


def test_existing_destination_and_bad_names_refuse(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "feature")
    head = _commit(repo, "src/a.py", "a\n", "change")
    store = tmp_path / "board"
    _sign(repo, store, base=base, head=head)
    with pytest.raises(TrustedSignError, match="hedef dal zaten var"):
        _sign(repo, tmp_path / "board-2", base=base, head=head)
    with pytest.raises(TrustedSignError, match="trusted-sign/pr"):
        sign_range(
            repo,
            base=base,
            head=head,
            dest="main",
            source_branch="feature",
            store=TaskClaimStore(tmp_path / "board-3"),
            secret=SECRET,
            proof_key="not-the-test-secret-32-bytes!!",
        )


def test_nonlinear_range_refuses(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-b", "left")
    _commit(repo, "src/left.py", "l\n", "left")
    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "right")
    _commit(repo, "src/right.py", "r\n", "right")
    _git(repo, "merge", "--no-ff", "left", "-m", "merge")
    head = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(TrustedSignError, match="doğrusal"):
        sign_range(
            repo,
            base=base,
            head=head,
            dest="trusted-sign/pr-2",
            source_branch="feature",
            store=TaskClaimStore(tmp_path / "board"),
            secret=SECRET,
            proof_key=public_proof_key(),
        )


def test_push_refuses_an_existing_remote_ref(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "feature")
    head = _commit(repo, "src/a.py", "a\n", "change")
    tip = _sign(repo, tmp_path / "board", base=base, head=head, dest="trusted-sign/pr-7")
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    _git(repo, "remote", "add", "origin", str(bare))
    args = push_args("origin", tip, "trusted-sign/pr-7")
    assert "--force" not in args
    assert "-f" not in args
    push_signed(repo, remote="origin", sha=tip, dest="trusted-sign/pr-7")
    with pytest.raises(TrustedSignError, match="uzak hedef"):
        push_signed(repo, remote="origin", sha=tip, dest="trusted-sign/pr-7")


def test_message_keeps_one_trailer_block() -> None:
    message = rebuild_message(
        "subject\n\nbody\n\nLumos-Claim: old\nLumos-Agent: old\nCo-authored-by: A <a@example.com>\n",
        claim_id="claim-1",
        owner=SIGNER_OWNER,
        attestation="sig",
    )
    assert "\n\n\n" not in message
    assert message.endswith(
        "\n".join(
        [
            "Lumos-Claim: claim-1",
            f"Lumos-Agent: {SIGNER_OWNER}",
            "Lumos-Claim-Attestation: sig",
            "Co-authored-by: A <a@example.com>",
            "",
        ]
    )
    )


def test_workflow_is_main_dispatch_and_does_not_take_the_proof_key() -> None:
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "write-sign-trusted.yml"
    ).read_text(encoding="utf-8")
    assert "\non:\n  workflow_dispatch:\n" in workflow
    assert "pull_request:" not in workflow
    assert "pull_request_target:" not in workflow
    assert "environment: lumos-write-gate" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert workflow.count("${{ secrets.LUMOS_WRITE_GATE_SECRET }}") == 1
    assert "lumos-ci-write-attestation-proof-not-prod-32" not in workflow
    assert "--central" in workflow
    assert "--store" not in workflow
    assert "--force" not in workflow
    assert "ref: main" in workflow
    assert "trusted-sign/pr-" in workflow
    jobs = workflow.split("\njobs:\n", 1)[1]
    assert "contents: write" in jobs
    assert "permissions:\n  contents: read\n" in workflow.split("\njobs:\n", 1)[0]


def test_cli_result_omits_secret_and_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "feature")
    head = _commit(repo, "src/a.py", "a\n", "change")
    monkeypatch.setenv("LUMOS_WRITE_GATE_SECRET", SECRET)
    from lumos_board.trusted_sign import main as sign_main

    code = sign_main(
        [
            "--repo",
            str(repo),
            "--base",
            base,
            "--head",
            head,
            "--dest",
            "trusted-sign/pr-3",
            "--source-branch",
            "feature",
            "--store",
            str(tmp_path / "board"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["dest"] == "trusted-sign/pr-3"
    assert payload["pushed"] is False
    assert SECRET not in captured.out
    assert SECRET not in captured.err
    assert "write_token" not in captured.out
