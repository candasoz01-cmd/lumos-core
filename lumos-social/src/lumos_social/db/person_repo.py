from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class Person:
    id: int
    display_name: str
    created_at: str


def add_person(conn: sqlite3.Connection, display_name: str) -> Person:
    cur = conn.execute(
        "INSERT INTO person (display_name) VALUES (?) RETURNING id, display_name, created_at",
        (display_name,),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("Insert failed: no row returned")
    conn.commit()
    return Person(
        id=row["id"], display_name=row["display_name"], created_at=row["created_at"]
    )


def list_people(conn: sqlite3.Connection) -> list[Person]:
    cur = conn.execute(
        "SELECT id, display_name, created_at FROM person ORDER BY id ASC"
    )
    rows = cur.fetchall()
    return [
        Person(id=r["id"], display_name=r["display_name"], created_at=r["created_at"])
        for r in rows
    ]
