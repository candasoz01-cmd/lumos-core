from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DbConfig:
    path: Path


def default_db_path() -> Path:
    base = Path(os.getenv("LUMOS_SOCIAL_DATA_DIR", ".data"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "lumos_social.db"


def connect(cfg: DbConfig) -> sqlite3.Connection:
    conn = sqlite3.connect(str(cfg.path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS person (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
