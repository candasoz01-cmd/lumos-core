from __future__ import annotations

import sys

from lumos_social.db.sqlite import DbConfig, connect, default_db_path, init_db
from lumos_social.db.person_repo import add_person, list_people
from lumos_social.db.context_repo import (
    ingest as context_ingest,
    report as context_report,
)


def _usage() -> None:
    print("Usage:")
    print("  python -m lumos_social status")
    print("  python -m lumos_social run")
    print('  python -m lumos_social person add "NAME"')
    print("  python -m lumos_social person list")
    print('  python -m lumos_social context ingest "NAME" "MESSAGE" [--ts ISO_TS]')
    print('  python -m lumos_social context report "NAME"')


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] in {"-h", "--help", "help"}:
        _usage()
        return 0

    cmd = args[0]

    if cmd == "status":
        print("env: dev")
        print("mode: INFO")
        print("connector: mock")
        print("health: ok=True fetch_count=0")
        return 0

    if cmd == "run":
        print("Mock connector çalışıyor...")
        print("Event: incoming_message (demo)")
        return 0

    if cmd == "tg":
        from lumos_social.telegram.cli import _tg_cmd

        return _tg_cmd(args)

    if cmd == "person":
        if len(args) < 2:
            _usage()
            return 2

        sub = args[1]
        cfg = DbConfig(path=default_db_path())
        conn = connect(cfg)
        init_db(conn)

        if sub == "add":
            if len(args) < 3:
                print(
                    'Missing NAME. Example: python -m lumos_social person add "Kando"'
                )
                return 2
            name = args[2]
            p = add_person(conn, name)
            print(f"added: id={p.id} name={p.display_name}")
            return 0

        if sub == "list":
            people = list_people(conn)
            if not people:
                print("no people")
                return 0
            for p in people:
                print(f"{p.id}\t{p.display_name}\t{p.created_at}")
            return 0

        print(f"Unknown subcommand: {sub}")
        return 2

    if cmd == "context":
        if len(args) < 2:
            _usage()
            return 2
        sub = args[1]
        cfg = DbConfig(path=default_db_path())
        conn = connect(cfg)
        init_db(conn)

        if sub == "ingest":
            if len(args) < 4:
                print(
                    'Missing NAME or MESSAGE. Example: python -m lumos_social context ingest "Kando" "Merhaba" --ts "2026-03-03T20:30:00Z"'
                )
                return 2
            name = args[2]
            message = args[3]
            ts = _parse_ts(args)
            context_ingest(conn, name, message, ts)
            print(f"ingested: person={name} ts={ts}")
            return 0

        if sub == "report":
            if len(args) < 3:
                print(
                    'Missing NAME. Example: python -m lumos_social context report "Kando"'
                )
                return 2
            name = args[2]
            stats = context_report(conn, name)
            if stats is None:
                print(f"no data for: {name}")
                return 0
            print(f"person: {stats.display_name} (id={stats.person_id})")
            print(f"  interactions: {stats.interaction_count}")
            print(f"  last_contact: {stats.last_contact_at or '-'}")
            print(f"  importance_score: {stats.importance_score:.2f}")
            return 0

        print(f"Unknown subcommand: {sub}")
        return 2

    print(f"Unknown command: {cmd}")
    return 1


def _parse_ts(args: list[str]) -> str:
    from datetime import datetime, timezone

    for i, a in enumerate(args):
        if a == "--ts" and i + 1 < len(args):
            return args[i + 1]
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
