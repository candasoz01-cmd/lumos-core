"""Safe contract tests for the one-command Google Meet launcher."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "lumos-meet"


def run_launcher(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(LAUNCHER), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_launcher_has_help_without_starting_a_bot():
    result = run_launcher("--help")

    assert result.returncode == 0
    assert "./lumos-meet https://meet.google.com/" in result.stdout


def test_launcher_rejects_missing_or_non_meet_url():
    missing = run_launcher()
    other = run_launcher("https://zoom.us/j/123")

    assert missing.returncode == 2
    assert other.returncode == 2
    assert "yalnız https://meet.google.com/" in other.stderr
