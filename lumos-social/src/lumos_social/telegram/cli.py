"""TG CLI: auth, follow, sources, enable, disable, run."""

from __future__ import annotations

import asyncio
from pathlib import Path

from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event
from lumos_social.db.sqlite import DbConfig, connect, init_db
from lumos_social.db.tg_repo import (
    add_source,
    init_tg_tables,
    list_sources,
    set_source_enabled,
)
from lumos_social.telegram.config import TgConfig


def _db_path() -> str:
    return ".data/lumos_social.db"


def _bus() -> EventBus:
    bus = EventBus()

    def printer(evt: Event) -> None:
        if evt.kind == "telegram.message":
            p = evt.payload
            txt = (p.get("text") or "").replace("\n", " ")
            if len(txt) > 140:
                txt = txt[:140] + "…"
            print(f'tg msg peer={p.get("peer")} chat_id={p.get("chat_id")} text="{txt}"')
        elif evt.kind == "telegram.error":
            print("tg error:", evt.payload.get("error"))

    bus.subscribe(printer)
    return bus


def _tg_cmd(args: object, db_path: str | None = None) -> int:
    """args: parsed namespace with .sub, .peer (optional), .db (optional)."""
    sub = getattr(args, "sub", None)
    if not sub:
        print(
            "Missing subcommand. Use: auth | follow | sources | enable | disable | run"
        )
        return 2

    path_str = db_path or getattr(args, "db", None) or _db_path()

    conn = connect(DbConfig(path=Path(path_str)))
    init_db(conn)
    init_tg_tables(conn)

    if sub == "auth":
        cfg = TgConfig.from_env()

        async def _auth() -> None:
            from telethon import TelegramClient

            client = TelegramClient(
                cfg.session_path, cfg.api_id, cfg.api_hash
            )
            await client.start(phone=cfg.phone)
            me = await client.get_me()
            print(
                "authorized as:",
                getattr(me, "username", None) or getattr(me, "id", None),
            )
            await client.disconnect()

        asyncio.run(_auth())
        return 0

    if sub == "follow":
        peer = (getattr(args, "peer", None) or "").strip()
        if not peer:
            print(
                'Missing PEER. Example: python -m lumos_social tg follow "@username"'
            )
            return 2
        s = add_source(conn, peer)
        print(f"followed: id={s.id} peer={s.peer}")
        return 0

    if sub == "sources":
        srcs = list_sources(conn)
        if not srcs:
            print("no sources")
            return 0
        for s in srcs:
            print(
                f"{s.id}\t{s.peer}\t{'on' if s.enabled else 'off'}\t{s.created_at}"
            )
        return 0

    if sub in ("enable", "disable"):
        peer = (getattr(args, "peer", None) or "").strip()
        if not peer:
            print(
                'Missing PEER. Example: python -m lumos_social tg disable "@username"'
            )
            return 2
        set_source_enabled(conn, peer, enabled=(sub == "enable"))
        print(f"{sub}d: {peer}")
        return 0

    if sub == "run":
        from lumos_social.telegram.runner import run_telegram_listener

        cfg = TgConfig.from_env()
        bus = _bus()
        return asyncio.run(
            run_telegram_listener(cfg, db_path=path_str, bus=bus)
        )

    print(f"Unknown subcommand: {sub}")
    return 2
