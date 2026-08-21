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
    assert "git diff --name-only -z" in text
    assert "--paths-nul" in text
    assert 'changed-paths.nul" --' in text
    assert "ref: ${{ github.event.pull_request.base.sha }}" in text
    # Fail-closed artık inline shell'de değil, trusted_gate CLI'ında.
    # Workflow onu çağırır; set -euo pipefail sıfırdan farklı çıkışta adımı düşürür.
    assert "standing_merge.trusted_gate" in text
    assert "set -euo pipefail" in text
    # Orkestratör de PR'dan gelmez (Security Reviewer HIGH, 2026-08-21)
    assert "pull_request_target:" in text


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


# --- CI giriş noktası fail-closed olmalı (2026-08-21) ---


def test_cli_without_arguments_fails_closed() -> None:
    """Argümansız çağrı sessizce exit 0 vermemeli.

    Bu tam olarak yaşanan hataydı: modülün CLI'ı yokken workflow adımı hiçbir
    şey yapmadan exit 0 veriyordu — fail-OPEN. Kapı kurmaya çalışırken kapının
    kendisi açık kalıyordu."""
    from standing_merge.trusted_gate import main

    assert main([]) == 2


def test_cli_without_dest_fails_closed() -> None:
    from standing_merge.trusted_gate import main

    assert main(["--repo", ".", "--base-sha", "deadbeef"]) == 2


def test_cli_fails_closed_when_base_lacks_classifier(tmp_path) -> None:
    """Base commit'te classifier yoksa PR sürümüne düşmez, 2 döner."""
    import subprocess

    from standing_merge.trusted_gate import main

    repo = tmp_path / "repo"
    repo.mkdir()
    run = lambda *a: subprocess.run(  # noqa: E731
        ["git", "-C", str(repo), *a], check=True, capture_output=True
    )
    run("init", "-q")
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    (repo / "README.md").write_text("x", encoding="utf-8")
    run("add", "README.md")
    run("commit", "-qm", "no classifier here")
    sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    dest = tmp_path / "trusted"
    assert main(["--repo", str(repo), "--base-sha", sha, "--dest", str(dest)]) == 2
    assert not (dest / "src").exists()


def test_cli_materializes_classifier_from_this_repo(tmp_path) -> None:
    import subprocess

    from standing_merge.trusted_gate import main

    root = Path(__file__).resolve().parents[1]
    sha = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dest = tmp_path / "trusted"
    assert main(["--repo", str(root), "--base-sha", sha, "--dest", str(dest)]) == 0
    assert (dest / "src/standing_merge/classify.py").is_file()
    assert (dest / "src/standing_merge/excluded_paths.json").is_file()


# --- Orkestratör güven kökü: workflow sözleşmesi ---


def test_workflow_orchestrator_comes_from_base_not_pr() -> None:
    """Yeni HIGH: classifier base'den gelse bile workflow PR'dan gelirse
    saldırgan PR classifier'ı hiç çağırmayan bir workflow yazabilir."""
    text = (
        Path(__file__).resolve().parents[1]
        / ".github/workflows/standing-class.yml"
    ).read_text(encoding="utf-8")
    body = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    assert "pull_request_target:" in body
    # Düz pull_request tetikleyicisi orkestratörü PR'dan alır — olmamalı
    assert "\n  pull_request:" not in body
    # PR head'i checkout edilmez; yalnız base.sha
    assert "ref: ${{ github.event.pull_request.base.sha }}" in body
    # Yazma yetkisi ve kalıcı kimlik yok
    assert "contents: read" in body
    assert "persist-credentials: false" in body
    # Yollar PR kodu çalıştırılmadan, NUL-delimited alınır
    assert "--name-only -z" in body
    assert "--paths-nul" in body
