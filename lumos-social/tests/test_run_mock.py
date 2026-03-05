"""context ingest + report: subprocess ile çalıştır, exit 0 ve report çıktısı."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
# Use a separate DB for this test so it doesn't pollute .data/lumos_social.db
TEST_DB = ROOT / ".data" / "test_run_mock.db"


def test_context_ingest_and_report_exit_zero() -> None:
    env = {"PYTHONPATH": str(SRC), **__import__("os").environ}
    r1 = subprocess.run(
        [sys.executable, "-m", "lumos_social", "context", "ingest", "TestPerson", "Hello", "--ts", "2026-03-03T20:30:00Z", "--db", str(TEST_DB)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r1.returncode == 0
    assert "ingested" in r1.stdout

    r2 = subprocess.run(
        [sys.executable, "-m", "lumos_social", "context", "report", "TestPerson", "--db", str(TEST_DB)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r2.returncode == 0
    assert "interaction_count" in r2.stdout or "name=" in r2.stdout
    assert "importance_score" in r2.stdout
