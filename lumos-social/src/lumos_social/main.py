"""Argparse CLI: status, person add/list, context, tg."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lumos_social.db.context_repo import (
    add_interaction,
    ensure_features_row,
    find_person_by_name,
    get_person_stats,
    rebuild_person_stats,
)
from lumos_social.db.person_repo import add_person, list_people
from lumos_social.db.sqlite import DbConfig, connect, init_db


@dataclass(frozen=True)
class AppConfig:
    db_path: Path


def default_config() -> AppConfig:
    return AppConfig(db_path=Path(".data") / "lumos_social.db")


def parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    v = ts.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="lumos_social")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_status = subparsers.add_parser("status")
    p_status.add_argument("--db", default=None)

    p_person = subparsers.add_parser("person")
    p_person.add_argument("sub", choices=["add", "list"])
    p_person.add_argument("name", nargs="?", default=None)
    p_person.add_argument("--db", default=None)

    p_tg = subparsers.add_parser("tg")
    p_tg.add_argument(
        "sub",
        choices=["auth", "follow", "sources", "enable", "disable", "run"],
    )
    p_tg.add_argument("peer", nargs="?", default=None)
    p_tg.add_argument("--db", default=None)

    p_ctx = subparsers.add_parser("context")
    p_ctx.add_argument("sub", choices=["ingest", "report"])
    p_ctx.add_argument("name")
    p_ctx.add_argument("text", nargs="?", default=None)
    p_ctx.add_argument("--db", default=None)
    p_ctx.add_argument("--source", default="telegram")
    p_ctx.add_argument("--direction", default="in", choices=["in", "out"])
    p_ctx.add_argument("--ts", default=None)
    p_ctx.add_argument("--sentiment", default=None)

    args = parser.parse_args(argv)

    cfg = default_config()
    if getattr(args, "db", None):
        cfg = AppConfig(db_path=Path(args.db))

    conn = connect(DbConfig(path=cfg.db_path))
    init_db(conn)

    if args.cmd == "status":
        print(f"ok db={cfg.db_path}")
        return 0

    if args.cmd == "person":
        if args.sub == "add":
            if not args.name:
                print('Missing NAME. Example: python -m lumos_social person add "Kando"')
                return 2
            p = add_person(conn, args.name)
            print(f"added: id={p.id} name={p.display_name}")
            return 0

        if args.sub == "list":
            people = list_people(conn)
            if not people:
                print("no people")
                return 0
            for p in people:
                print(f"{p.id}\t{p.display_name}\t{p.created_at}")
            return 0

        print(f"Unknown subcommand: {args.sub}")
        return 2

    if args.cmd == "tg":
        from lumos_social.telegram.cli import _tg_cmd

        return _tg_cmd(args, db_path=str(cfg.db_path))

    if args.cmd == "context":
        person_id = find_person_by_name(conn, args.name)
        if person_id is None:
            p = add_person(conn, args.name)
            person_id = p.id

        if args.sub == "ingest":
            if not args.text:
                print(
                    'Missing TEXT. Example: python -m lumos_social context ingest "Kando" "Merhaba"'
                )
                return 2

            ts = parse_ts(args.ts)
            sentiment = float(args.sentiment) if args.sentiment is not None else None

            interaction_id = add_interaction(
                conn,
                person_id=person_id,
                source=args.source,
                direction=args.direction,
                text=args.text,
                ts=ts,
            )
            ensure_features_row(
                conn,
                person_id=person_id,
                interaction_id=interaction_id,
                text=args.text,
                sentiment=sentiment,
            )
            rebuild_person_stats(conn, person_id)
            print(f"ingested: person_id={person_id} interaction_id={interaction_id}")
            return 0

        if args.sub == "report":
            stats = get_person_stats(conn, person_id)
            if stats is None:
                print("no stats")
                return 0
            print(f"name={stats.display_name}")
            print(f"interaction_count={stats.interaction_count}")
            print(f"last_contact_at={stats.last_contact_at}")
            print(f"response_delay_avg_sec={stats.response_delay_avg_sec}")
            print(f"sentiment_avg={stats.sentiment_avg}")
            print(f"importance_score={stats.importance_score:.4f}")
            return 0

        print(f"Unknown subcommand: {args.sub}")
        return 2

    print(f"Unknown command: {args.cmd}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
