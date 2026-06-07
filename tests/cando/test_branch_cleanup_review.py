"""cando.branch_cleanup_review: sınıflandırma ve rapor."""
from __future__ import annotations

from pathlib import Path
import subprocess

from cando.branch_cleanup_review import classify_branch, format_report, run_review


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("main\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "init main")
    _git(repo, "branch", "-M", "main")
    return repo


def test_classify_merged_zero_ahead_is_safe():
    info = classify_branch(
        name="docs/old",
        merged=True,
        ahead=0,
        is_ancestor=True,
        upstream="origin/docs/old",
    )
    assert info.classification == "guvenli"
    assert info.suggested_delete == "git branch -d docs/old"


def test_classify_unmerged_is_uncertain():
    info = classify_branch(
        name="feature/x",
        merged=False,
        ahead=2,
        is_ancestor=False,
        upstream=None,
    )
    assert info.classification == "belirsiz"
    assert info.suggested_delete is None
    assert any("merge edilmemiş" in r for r in info.reasons)


def test_run_review_detects_merged_branch(tmp_path):
    repo = _init_repo(tmp_path)
    _git(repo, "checkout", "-b", "docs/merged-note")
    (repo / "note.txt").write_text("note\n", encoding="utf-8")
    _git(repo, "add", "note.txt")
    _git(repo, "commit", "-m", "add note")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "docs/merged-note", "-m", "merge docs")

    result = run_review(repo, base_branch="main")
    names = {b.name: b for b in result.branches}
    assert "docs/merged-note" in names
    assert names["docs/merged-note"].classification == "guvenli"
    report = format_report(result, dry_run=True)
    assert "DRY-RUN" in report
    assert "öneri (çalıştırılmadı)" in report
