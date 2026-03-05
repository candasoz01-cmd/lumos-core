"""Run Telethon client: connect, handle new messages, optional EventBus publish."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from telethon import TelegramClient, events

from lumos_social.core.bus import EventBus
from lumos_social.core.events import Event
from lumos_social.db.sqlite import DbConfig, connect, init_db
from lumos_social.db.tg_repo import init_tg_tables, list_sources, save_message
from lumos_social.telegram.config import TgConfig

logger = logging.getLogger(__name__)


def _safe_str(x: Any) -> str | None:
    if x is None:
        return None
    s = str(x)
    return s if s else None


def _client(config: TgConfig) -> TelegramClient:
    return TelegramClient(
        config.session_path,
        config.api_id,
        config.api_hash,
    )


async def run_telegram_listener(
    cfg: TgConfig, *, db_path: str, bus: EventBus
) -> int:
    conn = connect(DbConfig(path=Path(db_path)))
    init_db(conn)
    init_tg_tables(conn)

    sources = [s for s in list_sources(conn) if s.enabled]
    if not sources:
        print(
            'no tg sources. add one: python -m lumos_social tg follow "@username"'
        )
        return 0

    peers = [s.peer for s in sources]
    print("tg: listening (read-only) for:", ", ".join(peers))

    client = _client(cfg)

    await client.start(phone=cfg.phone)

    tracked = set(peers)

    @client.on(events.NewMessage)
    async def handler(event: events.NewMessage.Event) -> None:
        try:
            chat = await event.get_chat()
            sender = await event.get_sender()
            chat_id = getattr(chat, "id", None)
            sender_id = getattr(sender, "id", None)

            peer_key = None
            uname = getattr(chat, "username", None)
            if uname:
                u = "@" + str(uname)
                if u in tracked:
                    peer_key = u

            if peer_key is None and chat_id is not None:
                s_id = str(chat_id)
                if s_id in tracked:
                    peer_key = s_id

            if peer_key is None:
                return

            msg = event.message
            payload = {
                "source": "telegram",
                "peer": peer_key,
                "chat_id": chat_id,
                "message_id": getattr(msg, "id", None),
                "sender_id": sender_id,
                "text": _safe_str(getattr(msg, "message", None)),
                "date": _safe_str(getattr(msg, "date", None)),
            }

            raw = None
            try:
                raw = json.dumps(msg.to_dict(), ensure_ascii=False, default=str)
            except Exception:
                raw = None

            save_message(
                conn,
                source_peer=peer_key,
                chat_id=chat_id,
                message_id=payload["message_id"],
                sender_id=sender_id,
                text=payload["text"],
                raw_json=raw,
            )

            bus.publish(Event(kind="telegram.message", payload=payload))
        except Exception as e:
            bus.publish(
                Event(kind="telegram.error", payload={"error": str(e)})
            )

    await client.run_until_disconnected()
    return 0


async def run(
    config: TgConfig,
    *,
    bus: EventBus | None = None,
) -> None:
    """Start Telethon client, run until disconnected. Optionally publish incoming messages to bus."""
    client = _client(config)

    if bus is not None:

        @client.on(events.NewMessage(incoming=True))
        async def on_message(event: events.NewMessage.Event) -> None:
            try:
                payload = {
                    "text": event.raw_text or "",
                    "chat_id": (
                        getattr(event.chat_id, "value", event.chat_id)
                        if event.chat_id
                        else None
                    ),
                    "message_id": event.id,
                    "sender_id": event.sender_id,
                    "peer": str(event.chat_id) if event.chat_id else None,
                }
                from lumos_social.core.events import incoming_message_event

                bus.publish(
                    incoming_message_event(payload=payload, source="telegram")
                )
            except Exception as e:
                logger.exception("on_message: %s", e)

    await client.start(phone=config.phone)
    try:
        await client.run_until_disconnected()
    finally:
        await client.disconnect()
