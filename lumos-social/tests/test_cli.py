"""Tests for CLI (argparse: status, person, context)."""

import subprocess
import sys
from pathlib import Path

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
    assert "ok" in r.stdout
    assert "db=" in r.stdout


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
    assert "usage" in out.lower() or "required" in out.lower()


def test_cli_context_help() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "lumos_social", "context", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )
    assert r.returncode == 0
    assert "context" in r.stdout.lower()
    assert "ingest" in r.stdout.lower() or "report" in r.stdout.lower()
