"""Context engine: interactions, features, person stats (SQLite)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lumos_social.db.context_repo import (
    add_interaction,
    ensure_features_row,
    get_person_stats,
    rebuild_person_stats,
)
from lumos_social.db.person_repo import add_person
from lumos_social.db.sqlite import DbConfig, connect, init_db


def test_context_engine_builds_stats(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    conn = connect(DbConfig(path=db_path))
    init_db(conn)

    p = add_person(conn, "Kando")

    t1 = datetime(2026, 3, 3, 20, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 3, 3, 20, 10, 0, tzinfo=UTC)

    i1 = add_interaction(
        conn,
        person_id=p.id,
        source="telegram",
        direction="in",
        text="Merhaba kanki",
        ts=t1,
    )
    ensure_features_row(
        conn, person_id=p.id, interaction_id=i1, text="Merhaba kanki", sentiment=0.2
    )

    i2 = add_interaction(
        conn,
        person_id=p.id,
        source="telegram",
        direction="out",
        text="Selam!",
        ts=t2,
    )
    ensure_features_row(
        conn, person_id=p.id, interaction_id=i2, text="Selam!", sentiment=0.1
    )

    rebuild_person_stats(conn, p.id)
    s = get_person_stats(conn, p.id)
    assert s is not None
    assert s.interaction_count == 2
    assert s.last_contact_at is not None
    assert s.response_delay_avg_sec is not None
    assert 0.0 <= s.importance_score <= 1.0
