"""Tests for config (Config dataclass, toml or defaults)."""

from pathlib import Path

import pytest

from lumos_social.config import load_config


def test_load_config_defaults() -> None:
    cfg = load_config(config_path=Path("/nonexistent/config.toml"))
    assert cfg.env == "dev" or cfg.env != ""
    assert cfg.log_level
    assert cfg.connector == "mock"


def test_load_config_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMOS_SOCIAL_ENV", "test")
    monkeypatch.setenv("LUMOS_SOCIAL_LOG_LEVEL", "DEBUG")
    cfg = load_config(config_path=Path("/nonexistent/config.toml"))
    assert cfg.env == "test"
    assert cfg.log_level == "DEBUG"
