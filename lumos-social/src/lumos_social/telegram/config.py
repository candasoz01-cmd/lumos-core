from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TgConfig:
    api_id: int
    api_hash: str
    phone: str | None = None
    session_path: str = ".data/telegram.session"

    @staticmethod
    def from_env() -> TgConfig:
        api_id_raw = os.getenv("LUMOS_TG_API_ID", "").strip()
        api_hash = os.getenv("LUMOS_TG_API_HASH", "").strip()
        phone = os.getenv("LUMOS_TG_PHONE", "").strip() or None
        session_path = os.getenv("LUMOS_TG_SESSION", "").strip() or ".data/telegram.session"

        if not api_id_raw.isdigit():
            raise ValueError("LUMOS_TG_API_ID missing/invalid (must be int)")
        if not api_hash:
            raise ValueError("LUMOS_TG_API_HASH missing")

        return TgConfig(
            api_id=int(api_id_raw),
            api_hash=api_hash,
            phone=phone,
            session_path=session_path,
        )
