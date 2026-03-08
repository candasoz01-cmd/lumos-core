"""Context engine: interactions, stats, importance score."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class PersonStats:
    person_id: int
    display_name: str
    interaction_count: int
    last_contact_at: str | None
    importance_score: float


def _get_or_create_person_id(conn: sqlite3.Connection, display_name: str) -> int:
    cur = conn.execute(
        "SELECT id FROM person WHERE display_name = ?", (display_name.strip(),)
    )
    row = cur.fetchone()
    if row is not None:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO person (display_name) VALUES (?) RETURNING id",
        (display_name.strip(),),
    )
    r = cur.fetchone()
    conn.commit()
    if r is None:
        raise RuntimeError("insert person failed")
    return r["id"]


def ingest(
    conn: sqlite3.Connection,
    person_name: str,
    text: str,
    ts: str,
    source: str = "cli",
    direction: str = "in",
) -> None:
    """Store one interaction and refresh person_stats (count, last_contact, importance)."""
    person_id = _get_or_create_person_id(conn, person_name)
    conn.execute(
        """
        INSERT INTO interactions (person_id, source, direction, text, ts)
        VALUES (?, ?, ?, ?, ?)
        """,
        (person_id, source, direction, text.strip(), ts),
    )
    conn.commit()
    _refresh_person_stats(conn, person_id)


def _refresh_person_stats(conn: sqlite3.Connection, person_id: int) -> None:
    cur = conn.execute(
        """
        SELECT COUNT(*) AS cnt, MAX(ts) AS last_ts
        FROM interactions WHERE person_id = ?
        """,
        (person_id,),
    )
    row = cur.fetchone()
    count = row["cnt"] if row else 0
    last_ts = row["last_ts"] if row and row["last_ts"] else None
    importance = min(1.0, (count / 10.0) + 0.1) if count else 0.0
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """
        INSERT INTO person_stats (person_id, interaction_count, last_contact_at, importance_score, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET
            interaction_count = excluded.interaction_count,
            last_contact_at = excluded.last_contact_at,
            importance_score = excluded.importance_score,
            updated_at = excluded.updated_at
        """,
        (person_id, count, last_ts, importance, now_utc),
    )
    conn.commit()


def report(conn: sqlite3.Connection, person_name: str) -> PersonStats | None:
    """Return stats for person by display_name, or None if no interactions."""
    cur = conn.execute(
        "SELECT id, display_name FROM person WHERE display_name = ?",
        (person_name.strip(),),
    )
    row = cur.fetchone()
    if row is None:
        return None
    person_id = row["id"]
    cur = conn.execute(
        """
        SELECT interaction_count, last_contact_at, importance_score
        FROM person_stats WHERE person_id = ?
        """,
        (person_id,),
    )
    st = cur.fetchone()
    if st is None:
        cur = conn.execute(
            "SELECT COUNT(*) AS c, MAX(ts) AS last_ts FROM interactions WHERE person_id = ?",
            (person_id,),
        )
        r = cur.fetchone()
        count = r["c"] or 0
        if count == 0:
            return None
        last_ts = r["last_ts"]
        importance = min(1.0, (count / 10.0) + 0.1)
        return PersonStats(
            person_id=person_id,
            display_name=row["display_name"],
            interaction_count=count,
            last_contact_at=last_ts,
            importance_score=importance,
        )
    return PersonStats(
        person_id=person_id,
        display_name=row["display_name"],
        interaction_count=st["interaction_count"],
        last_contact_at=st["last_contact_at"],
        importance_score=st["importance_score"],
    )
