"""run --once: subprocess ile çalıştır, stdout'ta incoming_message, exit 0."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def test_run_once_prints_incoming_message_exit_zero() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "lumos_social", "run", "--once"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(SRC), **__import__("os").environ},
    )
    assert r.returncode == 0
    assert "incoming_message" in r.stdout
    assert "platform=" in r.stdout
    assert "connector başlatıldı" in r.stdout
