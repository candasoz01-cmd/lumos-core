"""Create production-signed commits on a new branch.

``write-attestation-trusted`` only verifies. This module is the signer.
It runs in the ``lumos-write-gate`` environment, which GitHub opens for
``refs/heads/main`` after the required reviewer approves. The production
secret stays in that environment. The public CI proof key is rejected.

The source branch is not updated. Each commit is copied with ``commit-tree``
onto ``trusted-sign/pr-<number>``. One ACTIVE claim and one write token are
used per commit, then the claim is released. Nothing here grants merge.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from lumos_board.claim_cli import _claim_store
from lumos_board.task_claim import ClaimError, TaskClaimStore
from lumos_board.write_attestation import ClaimGuard, _changed_paths
from lumos_board.write_gate import WriteGate

SIGNER_OWNER = "lumos-write-gate"
SIGNER_EMAIL = "lumos-write-gate@users.noreply.github.com"
REPO_NAME = "lumos-core"
DEST_RE = re.compile(r"trusted-sign/pr-[1-9][0-9]*")
BRANCH_RE = re.compile(r"[A-Za-z0-9._/-]+")
SHA_RE = re.compile(r"[0-9a-f]{40}")
_SECRET_ENV = (
    "LUMOS_WRITE_GATE_SECRET",
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "ACTIONS_RUNTIME_TOKEN",
)


class TrustedSignError(ClaimError):
    """The authorized signer refused the request."""


@dataclass(frozen=True)
class SignedCommit:
    source: str
    signed: str
    claim_id: str

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "signed": self.signed, "claim_id": self.claim_id}


def public_proof_key() -> str:
    """Read the public CI proof key from the workflow that already publishes it."""
    workflow = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "claim-guard.yml"
    marker = "LUMOS_WRITE_GATE_SECRET:"
    try:
        lines = workflow.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise TrustedSignError("genel prova anahtarı okunamadı") from exc
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(marker) and "secrets." not in stripped:
            value = stripped.split(":", 1)[1].strip()
            if len(value.encode("utf-8")) >= 32:
                return value
    raise TrustedSignError("genel prova anahtarı okunamadı")


def assert_production_secret(secret: str | None, *, proof_key: str | None = None) -> str:
    if secret is None or len(secret.encode("utf-8")) < 32:
        raise TrustedSignError("CLAIM_GUARD_UNCONFIGURED")
    if secret == (proof_key if proof_key is not None else public_proof_key()):
        raise TrustedSignError("prova anahtarı üretim imzası basamaz")
    return secret


def assert_authorized_context() -> None:
    """Central signing is workflow_dispatch on main. Any other ref refuses."""
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise TrustedSignError("yetkili imza yalnız refs/heads/main üzerinde çalışır")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise TrustedSignError("yetkili imza yalnız workflow_dispatch ile çalışır")


def destination_branch(dest: str) -> str:
    if not DEST_RE.fullmatch(dest):
        raise TrustedSignError("hedef dal trusted-sign/pr-<numara> olmalı")
    return dest


def _sha(value: str, field: str) -> str:
    if not SHA_RE.fullmatch(value):
        raise TrustedSignError(f"{field} geçersiz")
    return value


def _source_branch(value: str, dest: str) -> str:
    if not BRANCH_RE.fullmatch(value) or value.startswith("-"):
        raise TrustedSignError("kaynak dal adı geçersiz")
    if value in {"main", "master"} or value == dest or value.startswith("trusted-sign/"):
        raise TrustedSignError("kaynak dal imza hedefi olamaz")
    return value


def _git(repo: Path, *args: str, input_text: str | None = None, env: dict[str, str] | None = None) -> str:
    merged = os.environ.copy()
    for key in _SECRET_ENV:
        merged.pop(key, None)
    if env:
        merged.update(env)
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
        env=merged,
    )
    if result.returncode != 0:
        detail = " ".join((result.stderr or result.stdout).split())[:200]
        raise TrustedSignError(detail or "git komutu başarısız")
    return result.stdout


def _ref_sha(repo: Path, ref: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", ref],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _linear_commits(repo: Path, base: str, head: str) -> tuple[str, ...]:
    out = _git(repo, "rev-list", "--reverse", "--no-merges", f"{base}..{head}")
    commits = tuple(line.strip() for line in out.splitlines() if line.strip())
    if not commits:
        raise TrustedSignError("CLAIM_GUARD_EMPTY_RANGE")
    parent = base
    for sha in commits:
        parts = _git(repo, "rev-list", "--parents", "-n", "1", sha).split()
        if len(parts) != 2 or parts[0] != sha or parts[1] != parent:
            raise TrustedSignError("aralık doğrusal değil")
        parent = sha
    if parent != head:
        raise TrustedSignError("aralık doğrusal değil")
    return commits


def rebuild_message(original: str, *, claim_id: str, owner: str, attestation: str) -> str:
    coauthors: list[str] = []
    kept: list[str] = []
    for line in original.splitlines():
        if line.startswith(("Lumos-Claim:", "Lumos-Agent:", "Lumos-Claim-Attestation:")):
            continue
        if line.startswith("Co-authored-by:"):
            coauthors.append(line)
            continue
        kept.append(line)
    body = "\n".join(kept).rstrip()
    trailers = [
        f"Lumos-Claim: {claim_id}",
        f"Lumos-Agent: {owner}",
        f"Lumos-Claim-Attestation: {attestation}",
        *coauthors,
    ]
    return body + "\n\n" + "\n".join(trailers) + "\n"


def _commit_tree(
    repo: Path,
    *,
    tree: str,
    parent: str,
    message: str,
    author_name: str,
    author_email: str,
    author_date: str,
) -> str:
    sha = _git(
        repo,
        "commit-tree",
        tree,
        "-p",
        parent,
        input_text=message,
        env={
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_AUTHOR_DATE": author_date,
            "GIT_COMMITTER_NAME": SIGNER_OWNER,
            "GIT_COMMITTER_EMAIL": SIGNER_EMAIL,
            "GIT_COMMITTER_DATE": datetime.now(timezone.utc).isoformat(),
        },
    ).strip()
    return _sha(sha, "signed")


def _create_branch(repo: Path, dest: str, sha: str) -> None:
    ref = f"refs/heads/{dest}"
    if _ref_sha(repo, ref) is not None:
        raise TrustedSignError("hedef dal zaten var")
    _git(repo, "update-ref", "--stdin", "--no-deref", input_text=f"create {ref} {sha}\n")


def _snapshot(repo: Path, *refs: str) -> dict[str, str | None]:
    return {ref: _ref_sha(repo, ref) for ref in refs}


def sign_range(
    repo: Path,
    *,
    base: str,
    head: str,
    dest: str,
    source_branch: str,
    store: TaskClaimStore,
    secret: str,
    proof_key: str | None = None,
) -> tuple[SignedCommit, ...]:
    """Copy ``base..head`` onto ``dest``. Source refs stay where they are."""
    repo = repo.resolve()
    base = _sha(base, "base")
    head = _sha(head, "head")
    dest = destination_branch(dest)
    source_branch = _source_branch(source_branch, dest)
    secret = assert_production_secret(secret, proof_key=proof_key)
    before = _snapshot(
        repo,
        f"refs/heads/{source_branch}",
        "refs/heads/main",
        f"refs/heads/{dest}",
    )
    if before[f"refs/heads/{dest}"] is not None:
        raise TrustedSignError("hedef dal zaten var")
    commits = _linear_commits(repo, base, head)
    guard = ClaimGuard(secret=secret)
    gate = WriteGate(store, secret=secret)
    signed: list[SignedCommit] = []
    parent = base
    number = dest.rsplit("-", 1)[-1]
    for sha in commits:
        paths = _changed_paths(repo, sha)
        claim_id: str | None = None
        try:
            result = store.claim(
                task_id=f"trusted-sign-{number}-{sha[:12]}",
                repo=REPO_NAME,
                branch=dest,
                worktree=str(repo),
                owner=SIGNER_OWNER,
                scopes=list(paths),
                ttl_seconds=1800,
                queue_on_conflict=False,
            )
            if not result.accepted or result.claim is None:
                raise TrustedSignError("claim kabul edilmedi")
            claim = result.claim
            claim_id = claim.claim_id
            token = gate.issue(claim)
            attestation = guard.attest(
                write_gate=gate,
                token=token,
                owner=SIGNER_OWNER,
                paths=list(paths),
                parent_sha=parent,
                claim_id=claim.claim_id,
                task_id=claim.task_id,
                scopes=list(claim.scopes),
            )
            message = rebuild_message(
                _git(repo, "log", "-1", "--format=%B", sha),
                claim_id=claim.claim_id,
                owner=SIGNER_OWNER,
                attestation=attestation,
            )
            new_sha = _commit_tree(
                repo,
                tree=_git(repo, "rev-parse", f"{sha}^{{tree}}").strip(),
                parent=parent,
                message=message,
                author_name=_git(repo, "log", "-1", "--format=%an", sha).strip(),
                author_email=_git(repo, "log", "-1", "--format=%ae", sha).strip(),
                author_date=_git(repo, "log", "-1", "--format=%aI", sha).strip(),
            )
            signed.append(SignedCommit(sha, new_sha, claim.claim_id))
            parent = new_sha
        finally:
            if claim_id is not None:
                store.release(claim_id, owner=SIGNER_OWNER)
    _create_branch(repo, dest, signed[-1].signed)
    after = _snapshot(
        repo,
        f"refs/heads/{source_branch}",
        "refs/heads/main",
        f"refs/heads/{dest}",
    )
    if after[f"refs/heads/{source_branch}"] != before[f"refs/heads/{source_branch}"]:
        raise TrustedSignError("kaynak dal değişti")
    if after["refs/heads/main"] != before["refs/heads/main"]:
        raise TrustedSignError("main değişti")
    if after[f"refs/heads/{dest}"] != signed[-1].signed:
        raise TrustedSignError("hedef dal yazılamadı")
    return tuple(signed)


def push_args(remote: str, sha: str, dest: str) -> list[str]:
    if not remote or remote.startswith("-") or any(char.isspace() for char in remote):
        raise TrustedSignError("remote geçersiz")
    dest = destination_branch(dest)
    sha = _sha(sha, "signed")
    return ["push", remote, f"{sha}:refs/heads/{dest}"]


def push_signed(repo: Path, *, remote: str, sha: str, dest: str) -> None:
    args = push_args(remote, sha, dest)
    listed = _git(repo, "ls-remote", remote, f"refs/heads/{destination_branch(dest)}")
    if listed.strip():
        raise TrustedSignError("uzak hedef dal zaten var")
    _git(repo, *args)


STOP_CHECKS = (
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
PROOF_KEY_CHECK = "write-attestation"


def compare_url(repo_slug: str, base: str, head: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo_slug):
        raise TrustedSignError("repo slug geçersiz")
    base = _sha(base, "base")
    head = _sha(head, "head")
    return f"https://github.com/{repo_slug}/compare/{base}...{head}"


def build_manifest(
    repo: Path,
    *,
    base: str,
    head: str,
    dest: str,
    source_branch: str,
    repo_slug: str,
) -> dict[str, Any]:
    dest = destination_branch(dest)
    if (
        not source_branch
        or source_branch.startswith("-")
        or any(char.isspace() for char in source_branch)
        or ".." in source_branch
    ):
        raise TrustedSignError("kaynak dal geçersiz")
    commits = _linear_commits(repo, base, head)
    items: list[dict[str, Any]] = []
    for sha in commits:
        subject = _git(repo, "log", "-1", "--format=%s", sha).strip()
        items.append(
            {
                "paths": list(_changed_paths(repo, sha)),
                "sha": sha,
                "subject": subject,
            }
        )
    return {
        "base": _sha(base, "base"),
        "commits": items,
        "compare_url": compare_url(repo_slug, base, head),
        "dest": dest,
        "grants_merge": False,
        "head": _sha(head, "head"),
        "source_branch": source_branch,
    }


def manifest_core(manifest: Mapping[str, Any]) -> dict[str, Any]:
    commits = manifest.get("commits")
    if not isinstance(commits, list):
        raise TrustedSignError("manifest commit listesi yok")
    core_commits = []
    for item in commits:
        if not isinstance(item, Mapping):
            raise TrustedSignError("manifest commit kaydı geçersiz")
        paths = item.get("paths")
        if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
            raise TrustedSignError("manifest yolları geçersiz")
        core_commits.append({"paths": list(paths), "sha": _sha(str(item.get("sha")), "commit")})
    return {
        "base": _sha(str(manifest.get("base")), "base"),
        "commits": core_commits,
        "dest": destination_branch(str(manifest.get("dest"))),
        "head": _sha(str(manifest.get("head")), "head"),
        "source_branch": str(manifest.get("source_branch") or ""),
    }


def require_same_manifest(approved: Mapping[str, Any], live: Mapping[str, Any]) -> None:
    if manifest_core(approved) != manifest_core(live):
        raise TrustedSignError("onaylanan değişiklik ile canlı başlık farklı")
    if approved.get("grants_merge") is True or live.get("grants_merge") is True:
        raise TrustedSignError("imza kaydı merge izni taşıyamaz")


def judge_checks(rollup: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_name: dict[str, dict[str, str]] = {}
    for item in rollup:
        name = str(item.get("name") or item.get("context") or "")
        if not name:
            continue
        status = str(item.get("status") or "").lower()
        conclusion = str(item.get("conclusion") or "").lower()
        by_name[name] = {"conclusion": conclusion, "status": status}
    pending: list[str] = []
    failed: list[str] = []
    for name in STOP_CHECKS:
        row = by_name.get(name)
        if row is None or row["status"] != "completed":
            pending.append(name)
        elif row["conclusion"] != "success":
            failed.append(name)
    return {
        "failed": failed,
        "grants_merge": False,
        "pending": pending,
        "proof_key_check": by_name.get(PROOF_KEY_CHECK),
        "standing_class": by_name.get("standing-class"),
        "stop": bool(pending or failed),
    }


def _emit(payload: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _preview_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m lumos_board.trusted_sign preview")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--dest", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--repo-slug", required=True)
    args = parser.parse_args(argv)
    _emit(
        build_manifest(
            Path(args.repo),
            base=args.base,
            head=args.head,
            dest=args.dest,
            source_branch=args.source_branch,
            repo_slug=args.repo_slug,
        )
    )
    return 0


def _judge_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m lumos_board.trusted_sign judge-checks")
    parser.add_argument("--file", required=True)
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    rollup = payload.get("statusCheckRollup", payload)
    if not isinstance(rollup, list):
        raise TrustedSignError("kontrol listesi geçersiz")
    verdict = judge_checks(rollup)
    _emit(verdict)
    return 2 if verdict["stop"] else 0


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv and argv[0] == "preview":
            return _preview_main(argv[1:])
        if argv and argv[0] == "judge-checks":
            return _judge_main(argv[1:])
        return _sign_main(argv)
    except (ClaimError, TrustedSignError, OSError, ValueError) as exc:
        sys.stderr.write(json.dumps({"error": str(exc)}, ensure_ascii=False) + "\n")
        return 2


def _sign_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m lumos_board.trusted_sign")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--dest", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--repo-slug", default="")
    parser.add_argument("--manifest-file")
    parser.add_argument("--store")
    parser.add_argument("--central", action="store_true")
    parser.add_argument("--push", metavar="REMOTE")
    args = parser.parse_args(argv)
    if args.manifest_file:
        if not args.repo_slug:
            raise TrustedSignError("manifest karşılaştırması repo slug ister")
        approved = json.loads(Path(args.manifest_file).read_text(encoding="utf-8"))
        live = build_manifest(
            Path(args.repo),
            base=args.base,
            head=args.head,
            dest=args.dest,
            source_branch=args.source_branch,
            repo_slug=args.repo_slug,
        )
        require_same_manifest(approved, live)
    if args.central == bool(args.store):
        raise TrustedSignError("yalnız --central veya --store verilir")
    if args.central:
        assert_authorized_context()
    secret = assert_production_secret(os.environ.get(_SECRET_ENV[0]))
    store = _claim_store(args.store)
    signed = sign_range(
        Path(args.repo),
        base=args.base,
        head=args.head,
        dest=args.dest,
        source_branch=args.source_branch,
        store=store,
        secret=secret,
    )
    pushed = False
    if args.push:
        if not args.central:
            raise TrustedSignError("push yalnız yetkili ortamda")
        push_signed(Path(args.repo), remote=args.push, sha=signed[-1].signed, dest=args.dest)
        pushed = True
    _emit(
        {
            "commits": [item.to_dict() for item in signed],
            "dest": args.dest,
            "grants_merge": False,
            "pushed": pushed,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
