"""Person table: add_person, list_people."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Person:
    id: int
    display_name: str
    created_at: str


def add_person(conn: sqlite3.Connection, display_name: str) -> Person:
    cur = conn.execute(
        "INSERT INTO person (display_name) VALUES (?)",
        (display_name.strip(),),
    )
    conn.commit()
    pid = int(cur.lastrowid)
    row = conn.execute(
        "SELECT id, display_name, created_at FROM person WHERE id = ?", (pid,)
    ).fetchone()
    return Person(
        id=int(row["id"]),
        display_name=str(row["display_name"]),
        created_at=str(row["created_at"]),
    )


def list_people(conn: sqlite3.Connection) -> list[Person]:
    rows = conn.execute(
        "SELECT id, display_name, created_at FROM person ORDER BY id ASC"
    ).fetchall()
    return [
        Person(id=int(r["id"]), display_name=str(r["display_name"]), created_at=str(r["created_at"]))
        for r in rows
    ]
