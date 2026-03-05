"""Person stats and interactions in SQLite. Use get_connection() for dict-like rows."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def get_connection(path: str | Path) -> sqlite3.Connection:
    """Return a connection with row_factory=Row so rows support row['col']."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@dataclass(frozen=True)
class PersonStats:
    person_id: int
    display_name: str
    interaction_count: int
    last_contact_at: datetime | None
    response_delay_avg_sec: float | None
    sentiment_avg: float | None
    importance_score: float


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    dt = dt.astimezone(UTC)
    return dt.isoformat().replace("+00:00", "Z")


def add_interaction(
    conn: sqlite3.Connection,
    *,
    person_id: int,
    source: str,
    direction: str,
    text: str,
    ts: datetime | None = None,
    meta: dict[str, Any] | None = None,
) -> int:
    if ts is None:
        ts = datetime.now(UTC)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    ts = ts.astimezone(UTC)

    meta_json = None
    if meta is not None:
        meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))

    cur = conn.execute(
        """
        INSERT INTO interactions (person_id, source, direction, text, ts, meta_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (person_id, source, direction, text, _to_iso(ts), meta_json),
    )
    conn.commit()
    return int(cur.lastrowid)


def rebuild_person_stats(conn: sqlite3.Connection, person_id: int) -> None:
    row = conn.execute(
        """
        SELECT p.id, p.display_name
        FROM person p
        WHERE p.id = ?
        """,
        (person_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"person not found: id={person_id}")

    count_row = conn.execute(
        "SELECT COUNT(1) AS c FROM interactions WHERE person_id = ?",
        (person_id,),
    ).fetchone()
    interaction_count = int(count_row["c"]) if count_row else 0

    last_row = conn.execute(
        """
        SELECT ts
        FROM interactions
        WHERE person_id = ?
        ORDER BY ts DESC
        LIMIT 1
        """,
        (person_id,),
    ).fetchone()
    last_contact_at = _parse_dt(last_row["ts"]) if last_row else None

    pairs = conn.execute(
        """
        SELECT direction, ts
        FROM interactions
        WHERE person_id = ?
        ORDER BY ts ASC
        """,
        (person_id,),
    ).fetchall()

    response_delays: list[float] = []
    last_in: datetime | None = None
    for r in pairs:
        d = r["direction"]
        ts = _parse_dt(r["ts"])
        if ts is None:
            continue
        if d == "in":
            last_in = ts
        elif d == "out" and last_in is not None:
            delta = (ts - last_in).total_seconds()
            if delta >= 0:
                response_delays.append(delta)
            last_in = None

    response_delay_avg_sec = (
        (sum(response_delays) / len(response_delays)) if response_delays else None
    )

    sent_row = conn.execute(
        "SELECT AVG(sentiment) AS s FROM interaction_features WHERE person_id = ?",
        (person_id,),
    ).fetchone()
    sentiment_avg = float(sent_row["s"]) if sent_row and sent_row["s"] is not None else None

    txt_row = conn.execute(
        "SELECT AVG(text_len) AS l FROM interaction_features WHERE person_id = ?",
        (person_id,),
    ).fetchone()
    avg_len = float(txt_row["l"]) if txt_row and txt_row["l"] is not None else 0.0

    now = datetime.now(UTC)
    recency_days = None
    if last_contact_at is not None:
        recency_days = max(0.0, (now - last_contact_at).total_seconds() / 86400.0)

    freq = min(1.0, interaction_count / 50.0)
    recency = 0.0 if recency_days is None else max(0.0, 1.0 - (recency_days / 14.0))
    length = min(1.0, avg_len / 280.0)
    sentiment = 0.5 if sentiment_avg is None else max(0.0, min(1.0, (sentiment_avg + 1.0) / 2.0))

    importance_score = 0.45 * freq + 0.35 * recency + 0.15 * length + 0.05 * sentiment

    conn.execute(
        """
        INSERT INTO person_stats (
            person_id,
            interaction_count,
            last_contact_at,
            response_delay_avg_sec,
            sentiment_avg,
            importance_score,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET
            interaction_count=excluded.interaction_count,
            last_contact_at=excluded.last_contact_at,
            response_delay_avg_sec=excluded.response_delay_avg_sec,
            sentiment_avg=excluded.sentiment_avg,
            importance_score=excluded.importance_score,
            updated_at=excluded.updated_at
        """,
        (
            person_id,
            interaction_count,
            _to_iso(last_contact_at),
            response_delay_avg_sec,
            sentiment_avg,
            importance_score,
            _to_iso(now),
        ),
    )
    conn.commit()


def get_person_stats(conn: sqlite3.Connection, person_id: int) -> PersonStats | None:
    row = conn.execute(
        """
        SELECT
          p.id AS person_id,
          p.display_name,
          s.interaction_count,
          s.last_contact_at,
          s.response_delay_avg_sec,
          s.sentiment_avg,
          s.importance_score
        FROM person p
        LEFT JOIN person_stats s ON s.person_id = p.id
        WHERE p.id = ?
        """,
        (person_id,),
    ).fetchone()
    if not row:
        return None

    return PersonStats(
        person_id=int(row["person_id"]),
        display_name=str(row["display_name"]),
        interaction_count=int(row["interaction_count"] or 0),
        last_contact_at=_parse_dt(row["last_contact_at"]),
        response_delay_avg_sec=(
            float(row["response_delay_avg_sec"]) if row["response_delay_avg_sec"] is not None else None
        ),
        sentiment_avg=float(row["sentiment_avg"]) if row["sentiment_avg"] is not None else None,
        importance_score=float(row["importance_score"] or 0.0),
    )


def find_person_by_name(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM person WHERE display_name = ?",
        (name,),
    ).fetchone()
    return int(row["id"]) if row else None


def ensure_features_row(
    conn: sqlite3.Connection,
    *,
    person_id: int,
    interaction_id: int,
    text: str,
    sentiment: float | None = None,
) -> None:
    text_len = len(text or "")
    conn.execute(
        """
        INSERT INTO interaction_features (interaction_id, person_id, text_len, sentiment)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(interaction_id) DO NOTHING
        """,
        (interaction_id, person_id, text_len, sentiment),
    )
    conn.commit()
