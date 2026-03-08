"""Telegram sources and messages (tg_sources, tg_messages)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import sqlite3


@dataclass(frozen=True)
class TgSource:
    id: int
    peer: str
    enabled: bool
    created_at: str


def init_tg_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tg_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            peer TEXT NOT NULL UNIQUE,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tg_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_peer TEXT NOT NULL,
            chat_id INTEGER,
            message_id INTEGER,
            sender_id INTEGER,
            text TEXT,
            raw_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def add_source(conn: sqlite3.Connection, peer: str) -> TgSource:
    now = datetime.now(UTC).isoformat()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO tg_sources(peer, enabled, created_at) VALUES (?, 1, ?)",
        (peer, now),
    )
    conn.commit()

    row = cur.execute(
        "SELECT id, peer, enabled, created_at FROM tg_sources WHERE peer=?",
        (peer,),
    ).fetchone()
    assert row is not None
    return TgSource(id=row[0], peer=row[1], enabled=bool(row[2]), created_at=row[3])


def set_source_enabled(conn: sqlite3.Connection, peer: str, enabled: bool) -> None:
    cur = conn.cursor()
    cur.execute("UPDATE tg_sources SET enabled=? WHERE peer=?", (1 if enabled else 0, peer))
    conn.commit()


def list_sources(conn: sqlite3.Connection) -> list[TgSource]:
    cur = conn.cursor()
    rows = cur.execute("SELECT id, peer, enabled, created_at FROM tg_sources ORDER BY id ASC").fetchall()
    return [TgSource(id=r[0], peer=r[1], enabled=bool(r[2]), created_at=r[3]) for r in rows]


def save_message(
    conn: sqlite3.Connection,
    *,
    source_peer: str,
    chat_id: int | None,
    message_id: int | None,
    sender_id: int | None,
    text: str | None,
    raw_json: str | None,
) -> None:
    now = datetime.now(UTC).isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tg_messages(source_peer, chat_id, message_id, sender_id, text, raw_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (source_peer, chat_id, message_id, sender_id, text, raw_json, now),
    )
    conn.commit()
