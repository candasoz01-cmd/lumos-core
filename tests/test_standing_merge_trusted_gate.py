"""Trusted base-SHA gate: PR checkout is never the classifier root."""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

from standing_merge.trusted_gate import (
    TrustedClassifierMissing,
    gate_exit_for_missing_base,
    materialize_trusted_classifier,
    run_trusted_classify,
    write_nul_paths,
)

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "standing-class.yml"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "gate@example.test")
    _git(repo, "config", "user.name", "gate")
    return repo


def _copy_current_classifier(dest_src: Path) -> None:
    src = REPO / "src" / "standing_merge"
    package = dest_src / "standing_merge"
    package.mkdir(parents=True)
    for name in ("__init__.py", "classify.py", "excluded_paths.json"):
        package.joinpath(name).write_bytes(src.joinpath(name).read_bytes())


def test_workflow_uses_base_sha_nul_paths_and_double_dash() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "github.event.pull_request.base.sha" in text
    assert "git diff -z --name-only" in text
    assert "--paths-nul" in text
    assert 'classify \\\n            --paths-nul "${RUNNER_TEMP}/changed-paths.nul" --' in text
    assert "github.workspace }}/src" not in text
    assert "trusted classifier missing" in text
    assert "exit 2" in text


def test_missing_classifier_on_base_is_fail_closed(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README").write_text("empty base\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-m", "base without classifier")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    with pytest.raises(TrustedClassifierMissing):
        materialize_trusted_classifier(repo, base, tmp_path / "trusted")
    assert gate_exit_for_missing_base() == 2


def test_trojaned_pr_classifier_cannot_make_security_path_eligible(
    tmp_path: Path,
) -> None:
    """Attack: rewrite classify.py to always-eligible and touch src/security/.

    Trusted materialization from the base SHA must still fail-closed.
    """
    repo = _init_repo(tmp_path)
    _copy_current_classifier(repo / "src")
    (repo / "src" / "security").mkdir(parents=True)
    (repo / "src" / "security" / "permissions.py").write_text(
        "ALLOW = False\n", encoding="utf-8"
    )
    _git(repo, "add", "src")
    _git(repo, "commit", "-m", "trusted classifier on base")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()

    trojan = textwrap.dedent(
        """
        import json
        import sys

        def main(argv=None):
            sys.stdout.write(json.dumps({
                "schema": "lumos.standing_merge.verdict.v1",
                "class": "eligible",
                "standing_merge": True,
            }) + "\\n")
            return 0

        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )
    (repo / "src" / "standing_merge" / "classify.py").write_text(trojan, encoding="utf-8")
    (repo / "src" / "security" / "permissions.py").write_text(
        "ALLOW = True\n", encoding="utf-8"
    )
    _git(repo, "add", "src")
    _git(repo, "commit", "-m", "trojan classifier plus security path")

    trusted_src = materialize_trusted_classifier(repo, base, tmp_path / "trusted")
    nul = tmp_path / "changed-paths.nul"
    write_nul_paths(
        nul,
        [
            "src/standing_merge/classify.py",
            "src/security/permissions.py",
        ],
    )
    trusted = run_trusted_classify(trusted_src, nul)
    assert trusted.returncode == 2
    assert "excluded" in trusted.stderr

    trojan_run = subprocess.run(
        [
            "python3",
            "-m",
            "standing_merge.classify",
            "--paths-nul",
            str(nul),
            "--",
        ],
        cwd=str(repo),
        env={**os.environ, "PYTHONPATH": str(repo / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert trojan_run.returncode == 0
