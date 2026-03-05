from pathlib import Path

from lumos_social.db.sqlite import DbConfig, connect, init_db
from lumos_social.db.person_repo import add_person, list_people


def test_add_and_list_people(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = connect(DbConfig(path=db_path))
    init_db(conn)

    add_person(conn, "Kando")
    add_person(conn, "LumosUser")

    people = list_people(conn)
    assert [p.display_name for p in people] == ["Kando", "LumosUser"]
