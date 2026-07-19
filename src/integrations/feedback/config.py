from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


SLACK_ALLOWED_CHANNEL_IDS_ENV = "LUMOS_FEEDBACK_SLACK_ALLOWED_CHANNEL_IDS"
_SLACK_CHANNEL_ID_PATTERN = re.compile(r"^[CG][A-Z0-9]+$")


def is_slack_channel_id(value: str) -> bool:
    return bool(_SLACK_CHANNEL_ID_PATTERN.fullmatch(value))


@dataclass(frozen=True)
class FeedbackHubConfig:
    slack_allowed_channel_ids: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_env(cls) -> FeedbackHubConfig:
        raw = os.environ.get(SLACK_ALLOWED_CHANNEL_IDS_ENV, "")
        values = frozenset(item.strip() for item in raw.split(",") if item.strip())
        return cls(slack_allowed_channel_ids=values)

    @property
    def invalid_slack_channel_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                channel_id
                for channel_id in self.slack_allowed_channel_ids
                if not is_slack_channel_id(channel_id)
            ),
        )

    @property
    def slack_configured(self) -> bool:
        return bool(self.slack_allowed_channel_ids) and not self.invalid_slack_channel_ids

    def slack_status(self) -> dict[str, object]:
        if self.slack_configured:
            return {
                "provider": "slack",
                "status": "configured",
                "delivery_mode": "inbound_webhook",
                "polling_enabled": False,
                "allowed_channel_count": len(self.slack_allowed_channel_ids),
            }

        missing = [] if self.slack_allowed_channel_ids else [SLACK_ALLOWED_CHANNEL_IDS_ENV]
        return {
            "provider": "slack",
            "status": "awaiting_configuration",
            "delivery_mode": "inbound_webhook",
            "polling_enabled": False,
            "missing_configuration": missing,
            "invalid_configuration": list(self.invalid_slack_channel_ids),
        }
