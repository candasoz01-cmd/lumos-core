"""Unit tests: scan output schema, capabilities classification, lumos env."""
from __future__ import annotations

import subprocess
import sys

import pytest

from lumos_core.device.scan import scan
from lumos_core.device.capabilities import classify, format_report, CAPABILITY_LEVELS


def test_scan_output_schema() -> None:
    """Scan çıktısı beklenen anahtarlara sahip olmalı."""
    data = scan()
    assert "os" in data
    assert "cpu" in data
    assert "ram_gb" in data
    assert "disk" in data
    assert "python" in data
    assert "node" in data
    assert "git" in data
    assert "shell" in data
    assert "network" in data
    assert "applications" in data
    assert "applications_note" in data
    assert "permissions" in data

    assert isinstance(data["os"], dict)
    assert "system" in data["os"]
    assert isinstance(data["applications"], list)
    assert isinstance(data["applications_note"], str)
    assert "eksik olabilir" in data["applications_note"] or "applications" in data["applications_note"].lower()

    if data["disk"] is not None:
        assert "path" in data["disk"]
        assert "total_gb" in data["disk"]
        assert "free_gb" in data["disk"]

    assert "version" in data["python"]
    assert "executable" in data["python"]


def test_capabilities_classification() -> None:
    """classify() can/limited/cannot değerleri döner."""
    # Git var, python venv var
    data_full = {
        "git": "git version 2.x",
        "python": {"version": "3.12", "venv": "/path/to/.venv"},
        "node": "v20.0.0",
        "disk": {"free_gb": 10.0},
        "network": "unknown",
        "permissions": {"accessibility": "unknown", "full_disk_access": "unknown", "screen_recording": "unknown"},
    }
    caps = classify(data_full)
    assert caps["repo"] == "can"
    assert caps["python_env"] == "can"
    assert caps["disk"] == "can"
    for v in caps.values():
        assert v in CAPABILITY_LEVELS

    # Git yok -> repo cannot
    data_no_git = {**data_full, "git": None}
    caps2 = classify(data_no_git)
    assert caps2["repo"] == "cannot"

    # Python yok -> python_env cannot
    data_no_py = {**data_full, "python": {}}
    caps3 = classify(data_no_py)
    assert caps3["python_env"] == "cannot"


def test_lumos_env_runs() -> None:
    """lumos env komutu çalışır ve JSON + özet üretir."""
    result = subprocess.run(
        [sys.executable, "-m", "lumos_core", "env"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (result.stderr or result.stdout)
    out = result.stdout
    assert "os" in out or "python" in out
    assert "Özet" in out or "Capabilities" in out or "capabilities" in out
    # İlk satırlar JSON (en azından "os" veya "python" anahtarı görünür)
    assert '"os"' in out or '"python"' in out
