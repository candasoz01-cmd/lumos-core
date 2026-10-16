"""The authorized signer copies a range onto a new branch and rejects the proof key."""

from __future__ import annotations

import json
import os
import subprocess
import sys
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


def test_workflow_shows_the_change_before_the_environment_gate() -> None:
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "write-sign-trusted.yml"
    ).read_text(encoding="utf-8")
    assert "\non:\n  workflow_dispatch:\n" in workflow
    assert "pull_request:" not in workflow
    assert "pull_request_target:" not in workflow
    assert "name: lumos-write-gate" in workflow
    assert "url: ${{ needs.preview.outputs.compare_url }}" in workflow
    assert "Onay merge izni değildir." in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert workflow.count("${{ secrets.LUMOS_WRITE_GATE_SECRET }}") == 1
    assert "lumos-ci-write-attestation-proof-not-prod-32" not in workflow
    assert "--central" in workflow
    assert "--store" not in workflow
    assert "--manifest-file" in workflow
    assert "--force" not in workflow
    assert "gh pr merge" not in workflow
    assert workflow.count("ref: ${{ github.sha }}") == 3
    assert "ref: main" not in workflow
    assert "trusted-sign/pr-" in workflow
    preview = workflow.index("\n  preview:\n")
    environment = workflow.index("name: lumos-write-gate")
    secret = workflow.index("${{ secrets.LUMOS_WRITE_GATE_SECRET }}")
    watch = workflow.index("\n  watch:\n")
    assert preview < environment < secret < watch
    jobs = workflow.split("\njobs:\n", 1)[1]
    assert jobs.count("contents: write") == 1
    assert "permissions:\n  contents: read\n" in workflow.split("\njobs:\n", 1)[0]
    watch_job = jobs.split("\n  watch:\n", 1)[1]
    assert "LUMOS_WRITE_GATE_SECRET" not in watch_job
    assert "contents: write" not in watch_job


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
    assert payload["grants_merge"] is False


def test_preview_lists_paths_and_does_not_sign(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "feature")
    head = _commit(repo, "src/a.py", "a\n", "change")
    from lumos_board.trusted_sign import main as sign_main

    code = sign_main(
        [
            "preview",
            "--repo",
            str(repo),
            "--base",
            base,
            "--head",
            head,
            "--dest",
            "trusted-sign/pr-9",
            "--source-branch",
            "feature",
            "--repo-slug",
            "candasoz01-cmd/lumos-core",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    manifest = json.loads(captured.out)
    assert manifest["grants_merge"] is False
    assert manifest["commits"] == [
        {"paths": ["src/a.py"], "sha": head, "subject": "change"}
    ]
    assert manifest["compare_url"] == (
        f"https://github.com/candasoz01-cmd/lumos-core/compare/{base}...{head}"
    )
    missing = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", "refs/heads/trusted-sign/pr-9"],
        check=False,
        capture_output=True,
    )
    assert missing.returncode != 0


def test_moved_head_is_not_signed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "feature")
    head = _commit(repo, "src/a.py", "a\n", "change")
    from lumos_board.trusted_sign import build_manifest
    from lumos_board.trusted_sign import main as sign_main

    approved = build_manifest(
        repo,
        base=base,
        head=head,
        dest="trusted-sign/pr-9",
        source_branch="feature",
        repo_slug="candasoz01-cmd/lumos-core",
    )
    moved = _commit(repo, "src/b.py", "b\n", "later")
    manifest_path = tmp_path / "approved.json"
    manifest_path.write_text(json.dumps(approved), encoding="utf-8")
    monkeypatch.setenv("LUMOS_WRITE_GATE_SECRET", SECRET)
    code = sign_main(
        [
            "--repo",
            str(repo),
            "--base",
            base,
            "--head",
            moved,
            "--dest",
            "trusted-sign/pr-9",
            "--source-branch",
            "feature",
            "--repo-slug",
            "candasoz01-cmd/lumos-core",
            "--manifest-file",
            str(manifest_path),
            "--store",
            str(tmp_path / "board"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 2
    assert "canlı başlık" in captured.err
    assert SECRET not in captured.err
    assert not (tmp_path / "board").exists()
    missing = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", "refs/heads/trusted-sign/pr-9"],
        check=False,
        capture_output=True,
    )
    assert missing.returncode != 0


def test_matching_manifest_signs_without_merge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "feature")
    head = _commit(repo, "src/a.py", "a\n", "change")
    from lumos_board.trusted_sign import build_manifest
    from lumos_board.trusted_sign import main as sign_main

    approved = build_manifest(
        repo,
        base=base,
        head=head,
        dest="trusted-sign/pr-9",
        source_branch="feature",
        repo_slug="candasoz01-cmd/lumos-core",
    )
    manifest_path = tmp_path / "approved.json"
    manifest_path.write_text(json.dumps(approved), encoding="utf-8")
    monkeypatch.setenv("LUMOS_WRITE_GATE_SECRET", SECRET)
    code = sign_main(
        [
            "--repo",
            str(repo),
            "--base",
            base,
            "--head",
            head,
            "--dest",
            "trusted-sign/pr-9",
            "--source-branch",
            "feature",
            "--repo-slug",
            "candasoz01-cmd/lumos-core",
            "--manifest-file",
            str(manifest_path),
            "--store",
            str(tmp_path / "board"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["grants_merge"] is False
    assert payload["pushed"] is False
    assert SECRET not in captured.out


def test_merge_flag_in_manifest_is_refused(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "feature")
    head = _commit(repo, "src/a.py", "a\n", "change")
    from lumos_board.trusted_sign import build_manifest
    from lumos_board.trusted_sign import require_same_manifest

    approved = build_manifest(
        repo,
        base=base,
        head=head,
        dest="trusted-sign/pr-9",
        source_branch="feature",
        repo_slug="candasoz01-cmd/lumos-core",
    )
    approved["grants_merge"] = True
    with pytest.raises(TrustedSignError, match="merge"):
        require_same_manifest(approved, approved)


def test_failed_trusted_check_stops_and_does_not_grant_merge() -> None:
    from lumos_board.trusted_sign import judge_checks

    rollup = [
        {"name": name, "status": "COMPLETED", "conclusion": "SUCCESS"}
        for name in (
            "write-attestation-trusted",
            "claim-guard",
            "test",
            "rust",
            "macos-app-build",
            "ui-smoke",
            "ui-e2e",
            "node-tests",
            "publication-gate",
        )
    ]
    clean = judge_checks(rollup)
    assert clean["stop"] is False
    assert clean["grants_merge"] is False
    failed = judge_checks(
        [
            {"name": "write-attestation-trusted", "status": "completed", "conclusion": "failure"},
            *rollup[1:],
            {"name": "write-attestation", "status": "completed", "conclusion": "failure"},
            {"name": "standing-class", "status": "completed", "conclusion": "failure"},
        ]
    )
    assert failed["stop"] is True
    assert failed["failed"] == ["write-attestation-trusted"]
    assert failed["grants_merge"] is False
    assert failed["proof_key_check"]["conclusion"] == "failure"
    assert failed["standing_class"]["conclusion"] == "failure"
    proof_only = judge_checks(
        [
            *rollup,
            {"name": "write-attestation", "status": "COMPLETED", "conclusion": "FAILURE"},
            {"name": "standing-class", "status": "COMPLETED", "conclusion": "FAILURE"},
        ]
    )
    assert proof_only["stop"] is False
    assert proof_only["grants_merge"] is False
    pending = judge_checks(rollup[:-1])
    assert pending["stop"] is True
    assert pending["pending"] == ["publication-gate"]


def test_workflow_python_entrypoints_run_without_installed_package() -> None:
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/write-sign-trusted.yml").read_text(encoding="utf-8")
    )
    env = {"PATH": os.environ.get("PATH", "")}
    env["PYTHONPATH"] = workflow.get("env", {}).get("PYTHONPATH", "").replace(
        "${{ github.workspace }}", str(root)
    )
    for command in ([], ["preview"], ["judge-checks"], ["request"]):
        result = subprocess.run(
            [sys.executable, "-S", "-m", "lumos_board.trusted_sign", *command, "--help"],
            cwd=root, env=env, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr


def test_request_binds_approval_to_main_and_exact_range() -> None:
    from lumos_board.trusted_sign import validate_pr_request

    base, head = "a" * 40, "b" * 40
    payload = {"state": "open", "base": {"ref": "main", "sha": base},
               "head": {"ref": "feature", "sha": head}}
    assert validate_pr_request(payload, base=base, head=head) == (base, head, "feature")
    for change in (
        {"state": "closed"},
        {"base": {"ref": "signed-unmerged", "sha": base}},
        {"base": {"ref": "main", "sha": "c" * 40}},
        {"head": {"ref": "feature", "sha": "c" * 40}},
        {"head": {"ref": "feature\ninjected", "sha": head}},
        {"base": None},
    ):
        with pytest.raises(TrustedSignError):
            validate_pr_request({**payload, **change}, base=base, head=head)


def test_workflow_validates_both_requests_and_authenticates_board() -> None:
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/write-sign-trusted.yml").read_text())
    for job in ("preview", "sign"):
        steps = workflow["jobs"][job]["steps"]
        requests = [step for step in steps if "sign-request" in step.get("run", "")
                    and "gh api" in step.get("run", "")]
        assert len(requests) == 1
        assert '--base "$GITHUB_SHA" --head "$HEAD"' in requests[0]["run"]
    sign = next(step for step in workflow["jobs"]["sign"]["steps"]
                if "--central" in step.get("run", ""))
    env = sign["env"]
    assert env["GH_TOKEN"] == "${{ github.token }}"
    assert env["GIT_CONFIG_KEY_0"] == "credential.https://github.com.helper"
    assert env["GIT_CONFIG_VALUE_0"] == "!gh auth git-credential"
