"""Config dataclass and load from config.toml or defaults."""

import os
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore[assignment]


@dataclass
class Config:
    """App config: local toml, env override, default fallback."""

    env: str = "dev"
    log_level: str = "INFO"
    connector: str = "mock"
    mode: str = "primary"
    auto_send_default: bool = False
    cloud_enabled: bool = False


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def load_config(config_path: str | Path | None = None) -> Config:
    """Load config: config.toml if exists, else defaults. Env overrides."""
    cfg = Config(
        env=_env("LUMOS_SOCIAL_ENV", "dev"),
        log_level=_env("LUMOS_SOCIAL_LOG_LEVEL", "INFO"),
        connector=_env("LUMOS_SOCIAL_CONNECTOR", "mock"),
        mode=_env("LUMOS_SOCIAL_MODE", "primary"),
        auto_send_default=_env("LUMOS_SOCIAL_AUTO_SEND_DEFAULT", "false").lower()
        in ("1", "true", "yes"),
        cloud_enabled=_env("LUMOS_SOCIAL_CLOUD_ENABLED", "false").lower() in ("1", "true", "yes"),
    )
    path = config_path or Path.cwd() / "config.toml"
    if isinstance(path, str):
        path = Path(path)
    if path.exists() and tomllib is not None:
        try:
            data = tomllib.loads(path.read_bytes())
            if isinstance(data, dict):
                if "env" in data and isinstance(data["env"], str):
                    cfg.env = data["env"]
                if "log_level" in data and isinstance(data["log_level"], str):
                    cfg.log_level = data["log_level"]
                if "connector" in data and isinstance(data["connector"], str):
                    cfg.connector = data["connector"]
                if "mode" in data and isinstance(data["mode"], str):
                    cfg.mode = data["mode"]
                if "auto_send_default" in data and isinstance(data["auto_send_default"], bool):
                    cfg.auto_send_default = data["auto_send_default"]
                if "cloud_enabled" in data and isinstance(data["cloud_enabled"], bool):
                    cfg.cloud_enabled = data["cloud_enabled"]
        except Exception:
            pass
    return cfg
