"""SQLite connection and schema init."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DbConfig:
    path: Path


def connect(cfg: DbConfig) -> sqlite3.Connection:
    cfg.path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cfg.path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
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

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('in','out')),
            text TEXT NOT NULL,
            ts TEXT NOT NULL,
            meta_json TEXT NULL,
            FOREIGN KEY(person_id) REFERENCES person(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_interactions_person_ts ON interactions(person_id, ts)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS interaction_features (
            interaction_id INTEGER PRIMARY KEY,
            person_id INTEGER NOT NULL,
            text_len INTEGER NOT NULL,
            sentiment REAL NULL,
            FOREIGN KEY(interaction_id) REFERENCES interactions(id) ON DELETE CASCADE,
            FOREIGN KEY(person_id) REFERENCES person(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_features_person ON interaction_features(person_id)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS person_stats (
            person_id INTEGER PRIMARY KEY,
            interaction_count INTEGER NOT NULL,
            last_contact_at TEXT NULL,
            response_delay_avg_sec REAL NULL,
            sentiment_avg REAL NULL,
            importance_score REAL NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(person_id) REFERENCES person(id) ON DELETE CASCADE
        )
        """
    )

    from lumos_social.db.tg_repo import init_tg_tables

    init_tg_tables(conn)
    conn.commit()
