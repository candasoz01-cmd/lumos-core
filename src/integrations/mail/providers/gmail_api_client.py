from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from integrations.mail.models import MailMessageSummary

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
ENV_GMAIL_SMOKE = "LUMOS_GMAIL_SMOKE"
ENV_GMAIL_SMOKE_ACCOUNT = "LUMOS_GMAIL_SMOKE_ACCOUNT"
_DEFAULT_TIMEOUT = 10.0


def is_gmail_smoke_enabled() -> bool:
    """Operatör-only live Gmail API gate — CI default kapalı."""
    return os.environ.get(ENV_GMAIL_SMOKE, "").strip().lower() in {"1", "true", "yes"}


def gmail_smoke_account_id() -> str:
    return os.environ.get(ENV_GMAIL_SMOKE_ACCOUNT, "").strip()


def extract_access_token(secret_value: str) -> str | None:
    """Vault secret — düz access token veya JSON ``access_token``."""
    raw = secret_value.strip()
    if not raw:
        return None
    if raw.startswith("{"):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            token = payload.get("access_token")
            if isinstance(token, str) and token.strip():
                return token.strip()
        return None
    return raw


def list_unread_summaries(
    access_token: str,
    *,
    limit: int = 10,
    timeout: float = _DEFAULT_TIMEOUT,
) -> list[MailMessageSummary]:
    """Gmail ``users.messages.list`` (q=is:unread) + metadata-only get — tam gövde yok."""
    cap = max(1, min(limit, 20))
    list_url = (
        f"{GMAIL_API_BASE}/users/me/messages?"
        + urlencode({"q": "is:unread", "maxResults": str(cap)})
    )
    list_payload = _gmail_get_json(list_url, access_token, timeout=timeout)
    message_refs = list_payload.get("messages") if isinstance(list_payload, dict) else None
    if not isinstance(message_refs, list) or not message_refs:
        return []

    summaries: list[MailMessageSummary] = []
    for ref in message_refs[:cap]:
        if not isinstance(ref, dict):
            continue
        msg_id = ref.get("id")
        if not isinstance(msg_id, str) or not msg_id:
            continue
        detail_url = (
            f"{GMAIL_API_BASE}/users/me/messages/{msg_id}?"
            + urlencode(
                {
                    "format": "metadata",
                    "metadataHeaders": ["Subject", "From", "Date"],
                },
                doseq=True,
            )
        )
        detail = _gmail_get_json(detail_url, access_token, timeout=timeout)
        summary = _message_to_summary(msg_id, detail)
        if summary is not None:
            summaries.append(summary)
    return summaries


def _gmail_get_json(url: str, access_token: str, *, timeout: float) -> dict[str, Any] | None:
    req = Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — operatör OAuth token
            if not (200 <= resp.status < 300):
                return None
            payload = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError, TimeoutError):
        return None
    return payload if isinstance(payload, dict) else None


def _message_to_summary(msg_id: str, detail: dict[str, Any] | None) -> MailMessageSummary | None:
    if not isinstance(detail, dict):
        return None
    headers = _header_map(detail)
    subject = _preview(headers.get("Subject", ""), max_len=120)
    from_addr = _preview(headers.get("From", ""), max_len=80)
    received_at = _received_at(detail, headers.get("Date", ""))
    return MailMessageSummary(
        message_id=msg_id,
        subject_preview=subject or "(no subject)",
        from_preview=from_addr or "(unknown sender)",
        received_at=received_at,
    )


def _header_map(detail: dict[str, Any]) -> dict[str, str]:
    payload = detail.get("payload")
    if not isinstance(payload, dict):
        return {}
    raw_headers = payload.get("headers")
    if not isinstance(raw_headers, list):
        return {}
    out: dict[str, str] = {}
    for item in raw_headers:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        if isinstance(name, str) and isinstance(value, str):
            out[name] = value
    return out


def _received_at(detail: dict[str, Any], date_header: str) -> str:
    internal = detail.get("internalDate")
    if isinstance(internal, str) and internal.isdigit():
        ms = int(internal)
        return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if date_header.strip():
        return _preview(date_header.strip(), max_len=64)
    return ""


def _preview(value: str, *, max_len: int) -> str:
    text = " ".join(value.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"
