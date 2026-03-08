from __future__ import annotations

import sys

from lumos_social.db.sqlite import DbConfig, connect, default_db_path, init_db
from lumos_social.db.person_repo import add_person, list_people


def _usage() -> None:
    print("Usage:")
    print("  python -m lumos_social status")
    print("  python -m lumos_social run")
    print('  python -m lumos_social person add "NAME"')
    print("  python -m lumos_social person list")


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

    print(f"Unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
