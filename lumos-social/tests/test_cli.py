"""Tests for CLI status command."""

import subprocess
import sys
from pathlib import Path

# Project root = parent of src
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def test_cli_status_exit_zero() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "lumos_social", "status"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )
    assert r.returncode == 0
    assert "lumos-social status" in r.stdout
    assert "connector" in r.stdout.lower() or "health" in r.stdout.lower()


def test_cli_no_args_shows_usage() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "lumos_social"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "Usage" in out or "Missing command" in out or "COMMAND" in out


def test_cli_run_help() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "lumos_social", "run", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )
    assert r.returncode == 0
    assert "run" in r.stdout.lower()
