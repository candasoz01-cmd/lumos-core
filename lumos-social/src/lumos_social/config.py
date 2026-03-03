"""Simple config: env first, optional TOML. No secrets in repo."""

import os
from pathlib import Path
from typing import Any

# Optional TOML: use tomli on older Python
try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore[assignment]

if tomllib is None:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load config: env overrides, then optional TOML file. No secrets committed."""
    out: dict[str, Any] = {
        "env": _env("LUMOS_SOCIAL_ENV", "dev"),
        "log_level": _env("LUMOS_SOCIAL_LOG_LEVEL", "INFO"),
        "connectors": [],
    }
    path = config_path or Path.cwd() / "config.toml"
    if isinstance(path, str):
        path = Path(path)
    if path.exists() and tomllib is not None:
        try:
            raw_bytes = path.read_bytes()
            # stdlib tomllib (3.11+) uses load(b); tomli uses load(s) with str
            try:
                data = tomllib.loads(raw_bytes)  # type: ignore[arg-type]
            except TypeError:
                data = tomllib.loads(raw_bytes.decode("utf-8"))  # type: ignore[arg-type]
            if isinstance(data, dict):
                out.update({k: v for k, v in data.items() if k in out or k == "connectors"})
                if "connectors" in data and isinstance(data["connectors"], list):
                    out["connectors"] = list(data["connectors"])
        except Exception:
            pass
    return out
