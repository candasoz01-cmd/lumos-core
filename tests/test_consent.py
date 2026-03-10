"""Tests for V1 consent persistence: single source .lumos/consent.json."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from lumos_core.security.consent import (
    has_user_consent,
    save_consent,
    ask_and_persist_consent_if_needed,
)


def test_has_user_consent_no_file_returns_false(tmp_path: Path) -> None:
    """When consent.json does not exist, has_user_consent is False."""
    assert has_user_consent(base_dir=tmp_path) is False


def test_has_user_consent_invalid_file_returns_false(tmp_path: Path) -> None:
    """When consent.json is invalid or not granted, has_user_consent is False."""
    (tmp_path / "consent.json").write_text("{}", encoding="utf-8")
    assert has_user_consent(base_dir=tmp_path) is False
    (tmp_path / "consent.json").write_text('{"granted": false}', encoding="utf-8")
    assert has_user_consent(base_dir=tmp_path) is False


def test_has_user_consent_granted_returns_true(tmp_path: Path) -> None:
    """When consent.json has granted=true, has_user_consent is True."""
    (tmp_path / "consent.json").write_text('{"granted": true}', encoding="utf-8")
    assert has_user_consent(base_dir=tmp_path) is True


def test_save_consent_creates_file(tmp_path: Path) -> None:
    """save_consent creates consent.json with granted true."""
    save_consent(base_dir=tmp_path)
    path = tmp_path / "consent.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("granted") is True


def test_ask_and_persist_consent_if_needed_skips_when_consented(tmp_path: Path) -> None:
    """When already consented, ask_and_persist does not prompt (no input needed)."""
    save_consent(base_dir=tmp_path)
    ask_and_persist_consent_if_needed(base_dir=tmp_path)
    assert (tmp_path / "consent.json").exists()


def test_consent_persisted_after_e_then_reopen_no_onboarding(tmp_path: Path) -> None:
    """First run: no consent file -> user sends 'e' -> consent file created.
    Second run: consent file exists -> onboarding (Merhaba) not shown.
    """
    # Run CLI from tmp_path so .lumos is under tmp_path; send e then help then exit.
    repo_src = Path(__file__).resolve().parent.parent / "src"
    env = {**os.environ, "PYTHONPATH": str(repo_src)}
    inp = "e\nhelp\nexit\n"
    r1 = subprocess.run(
        [sys.executable, "-m", "lumos_core", "cli"],
        cwd=tmp_path,
        input=inp,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert r1.returncode == 0
    consent_file = tmp_path / ".lumos" / "consent.json"
    # If src/.lumos was used (e.g. later logic), check both
    if not consent_file.exists():
        consent_file = tmp_path / "src" / ".lumos" / "consent.json"
    assert consent_file.exists(), "consent.json should exist after user answered e"
    assert json.loads(consent_file.read_text(encoding="utf-8")).get("granted") is True

    # Second run: only help and exit; no consent question, no onboarding Merhaba.
    r2 = subprocess.run(
        [sys.executable, "-m", "lumos_core", "cli"],
        cwd=tmp_path,
        input="help\nexit\n",
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert r2.returncode == 0
    out2 = r2.stdout + r2.stderr
    assert "Merhaba" not in out2, "Onboarding (Merhaba) should not appear when consent already granted"
    assert "Kando v0" in out2
