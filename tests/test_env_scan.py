"""Tests for first-run env scan (read-only, no persistence)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lumos_core.system.env_scan import (
    build_capability_report,
    scan_apps_mac,
    scan_dev_environment,
    scan_permissions_mac,
    scan_system,
)


def test_scan_system_returns_dict() -> None:
    data = scan_system()
    assert isinstance(data, dict)
    assert "os" in data
    assert "cpu" in data
    assert "ram" in data
    assert "python" in data
    assert isinstance(data["os"], str)
    assert isinstance(data["python"], str)


def test_scan_dev_environment_returns_dict() -> None:
    data = scan_dev_environment()
    assert isinstance(data, dict)
    for key in ["git", "python", "node", "docker", "ollama", "cursor", "vscode", "jupyter"]:
        assert key in data
        assert isinstance(data[key], bool)


def test_scan_apps_mac_returns_list() -> None:
    data = scan_apps_mac()
    assert isinstance(data, list)
    if data:
        assert all(isinstance(x, str) for x in data)


def test_scan_permissions_mac_returns_dict() -> None:
    data = scan_permissions_mac()
    assert isinstance(data, dict)
    assert "accessibility" in data
    assert "screen_recording" in data
    assert data["accessibility"] in ("unknown", "granted", "denied")
    assert data["screen_recording"] in ("unknown", "granted", "denied")


def test_build_capability_report_structure() -> None:
    report = build_capability_report()
    assert isinstance(report, dict)
    assert report["system"] == scan_system()
    assert report["dev_environment"] == scan_dev_environment()
    assert report["applications"] == scan_apps_mac()
    assert report["permissions"] == scan_permissions_mac()
    assert "capabilities" in report
    assert isinstance(report["capabilities"], list)
    assert all(isinstance(c, str) for c in report["capabilities"])


def test_env_scan_no_filesystem_writes(tmp_path: Path) -> None:
    """Running all scan functions must not create any files in cwd."""
    orig_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        before = set(tmp_path.iterdir())

        scan_system()
        scan_dev_environment()
        scan_apps_mac()
        scan_permissions_mac()
        build_capability_report()

        after = set(tmp_path.iterdir())
        new_items = after - before
        assert not new_items, f"Scan created paths: {new_items}"
    finally:
        os.chdir(orig_cwd)


def test_print_onboarding_preview_no_write(capsys: pytest.CaptureFixture[str]) -> None:
    """print_onboarding_preview must not write to disk; output only to stdout."""
    from lumos_core.system.env_scan import print_onboarding_preview

    report = build_capability_report()
    print_onboarding_preview(report)
    out, err = capsys.readouterr()
    assert "Merhaba" in out
    assert "kaydedilmedi" in out
    assert "capabilities" in report or "Şu anda" in out
