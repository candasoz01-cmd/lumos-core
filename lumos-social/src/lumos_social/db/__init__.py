"""DB: sqlite config, person repo, context repo, tg repo."""

from lumos_social.db.context_repo import (
    add_interaction,
    ensure_features_row,
    find_person_by_name,
    get_person_stats,
    rebuild_person_stats,
)
from lumos_social.db.person_repo import Person, add_person, list_people
from lumos_social.db.sqlite import DbConfig, connect, init_db
from lumos_social.db.tg_repo import (
    TgSource,
    add_source,
    init_tg_tables,
    list_sources,
    save_message,
    set_source_enabled,
)

__all__ = [
    "DbConfig",
    "Person",
    "TgSource",
    "add_interaction",
    "add_source",
    "add_person",
    "connect",
    "ensure_features_row",
    "find_person_by_name",
    "get_person_stats",
    "init_db",
    "init_tg_tables",
    "list_people",
    "list_sources",
    "rebuild_person_stats",
    "save_message",
    "set_source_enabled",
]
