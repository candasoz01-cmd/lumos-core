from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from enum import StrEnum

from integrations.mail.providers.gmail_oauth import GMAIL_OAUTH_SCOPE_READONLY, GMAIL_OAUTH_SCOPES_DAR_V1
from integrations.mail.vault_credential import VaultCredentialRef, mail_read_credential_ref

# Public-safe route template — gerçek redirect URI private operatör katmanında.
GMAIL_OAUTH_CALLBACK_PATH_PATTERN = "/integrations/mail/oauth/gmail/callback"

# OAuth callback hata kodları — HTTP handler bu PR'da yok; contract sabitleri.
OAUTH_CALLBACK_ERROR_INVALID_STATE = "invalid_oauth_state"
OAUTH_CALLBACK_ERROR_MISSING_CODE = "missing_authorization_code"
OAUTH_CALLBACK_ERROR_PROVIDER_ERROR = "oauth_provider_error"
OAUTH_CALLBACK_ERROR_UNKNOWN_ACCOUNT = "unknown_account_id"
OAUTH_CALLBACK_ERROR_MALFORMED_STATE = "malformed_oauth_state"
OAUTH_CALLBACK_ERROR_ACCOUNT_ID_REQUIRED = "account_id_required"

# Vault ref şeması — mail_read_credential_ref ile aynı.
MAIL_READ_VAULT_REF_PREFIX = "mail-read:"


class OAuthCallbackPhase(StrEnum):
    """OAuth akış fazları — authorize → callback → vault_write → complete."""

    AUTHORIZE = "authorize"
    CALLBACK = "callback"
    VAULT_WRITE = "vault_write"
    COMPLETE = "complete"


class OAuthCallbackStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True)
class OAuthCallbackQuery:
    """Google redirect query — secret/token alanı yok."""

    code: str | None = None
    state: str | None = None
    error: str | None = None
    error_description: str | None = None


@dataclass(frozen=True)
class OAuthCallbackStatePayload:
    """CSRF/state taşıyıcı — yalnızca account_id + oturum + nonce; secret yok."""

    account_id: str
    session_id: str
    nonce: str


@dataclass(frozen=True)
class OAuthCallbackResult:
    """Callback değerlendirme sonucu — vault ref türetimi contract ile hizalı."""

    status: OAuthCallbackStatus
    phase: OAuthCallbackPhase
    account_id: str
    vault_ref: VaultCredentialRef | None = None
    error_code: str | None = None
    scopes: frozenset[str] = GMAIL_OAUTH_SCOPES_DAR_V1

    @classmethod
    def success(cls, *, account_id: str, phase: OAuthCallbackPhase) -> OAuthCallbackResult:
        ref = mail_read_credential_ref(account_id)
        return cls(
            status=OAuthCallbackStatus.SUCCESS,
            phase=phase,
            account_id=account_id,
            vault_ref=ref,
        )

    @classmethod
    def error(
        cls,
        *,
        error_code: str,
        phase: OAuthCallbackPhase = OAuthCallbackPhase.CALLBACK,
        account_id: str = "",
    ) -> OAuthCallbackResult:
        return cls(
            status=OAuthCallbackStatus.ERROR,
            phase=phase,
            account_id=account_id,
            error_code=error_code,
        )


def mail_read_vault_ref_id(account_id: str) -> str:
    """Vault ref_id — `mail-read:{account_id}`; bkz. vault_credential.mail_read_credential_ref."""
    return f"{MAIL_READ_VAULT_REF_PREFIX}{account_id}"


def parse_oauth_callback_query(params: dict[str, str]) -> OAuthCallbackQuery:
    """Query dict → OAuthCallbackQuery; bilinmeyen anahtarlar yok sayılır."""
    return OAuthCallbackQuery(
        code=_optional_str(params.get("code")),
        state=_optional_str(params.get("state")),
        error=_optional_str(params.get("error")),
        error_description=_optional_str(params.get("error_description")),
    )


def encode_oauth_state(payload: OAuthCallbackStatePayload) -> str:
    """State string — base64url JSON; client secret veya token içermez."""
    raw = json.dumps(
        {
            "account_id": payload.account_id,
            "session_id": payload.session_id,
            "nonce": payload.nonce,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_oauth_state(state: str) -> OAuthCallbackStatePayload | None:
    """State decode; malformed → None."""
    if not state.strip():
        return None
    padded = state + "=" * (-len(state) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    account_id = data.get("account_id")
    session_id = data.get("session_id")
    nonce = data.get("nonce")
    if not all(isinstance(v, str) and v.strip() for v in (account_id, session_id, nonce)):
        return None
    return OAuthCallbackStatePayload(
        account_id=account_id.strip(),
        session_id=session_id.strip(),
        nonce=nonce.strip(),
    )


def evaluate_oauth_callback(
    query: OAuthCallbackQuery,
    *,
    expected_session_id: str,
    known_account_ids: frozenset[str] | None = None,
) -> OAuthCallbackResult:
    """Callback query doğrulama — ağ/token exchange yok; yalnız contract kuralları."""
    if query.error:
        return OAuthCallbackResult.error(
            error_code=OAUTH_CALLBACK_ERROR_PROVIDER_ERROR,
            phase=OAuthCallbackPhase.CALLBACK,
        )

    if not query.state:
        return OAuthCallbackResult.error(error_code=OAUTH_CALLBACK_ERROR_INVALID_STATE)

    payload = decode_oauth_state(query.state)
    if payload is None:
        return OAuthCallbackResult.error(error_code=OAUTH_CALLBACK_ERROR_MALFORMED_STATE)

    if payload.session_id != expected_session_id:
        return OAuthCallbackResult.error(error_code=OAUTH_CALLBACK_ERROR_INVALID_STATE)

    account_id = payload.account_id
    if not account_id:
        return OAuthCallbackResult.error(error_code=OAUTH_CALLBACK_ERROR_ACCOUNT_ID_REQUIRED)

    if known_account_ids is not None and account_id not in known_account_ids:
        return OAuthCallbackResult.error(
            error_code=OAUTH_CALLBACK_ERROR_UNKNOWN_ACCOUNT,
            account_id=account_id,
        )

    if not query.code:
        return OAuthCallbackResult.error(
            error_code=OAUTH_CALLBACK_ERROR_MISSING_CODE,
            account_id=account_id,
        )

    return OAuthCallbackResult.success(
        account_id=account_id,
        phase=OAuthCallbackPhase.VAULT_WRITE,
    )


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


__all__ = [
    "GMAIL_OAUTH_CALLBACK_PATH_PATTERN",
    "GMAIL_OAUTH_SCOPE_READONLY",
    "MAIL_READ_VAULT_REF_PREFIX",
    "OAuthCallbackPhase",
    "OAuthCallbackQuery",
    "OAuthCallbackResult",
    "OAuthCallbackStatePayload",
    "OAuthCallbackStatus",
    "OAUTH_CALLBACK_ERROR_ACCOUNT_ID_REQUIRED",
    "OAUTH_CALLBACK_ERROR_INVALID_STATE",
    "OAUTH_CALLBACK_ERROR_MALFORMED_STATE",
    "OAUTH_CALLBACK_ERROR_MISSING_CODE",
    "OAUTH_CALLBACK_ERROR_PROVIDER_ERROR",
    "OAUTH_CALLBACK_ERROR_UNKNOWN_ACCOUNT",
    "decode_oauth_state",
    "encode_oauth_state",
    "evaluate_oauth_callback",
    "mail_read_vault_ref_id",
    "parse_oauth_callback_query",
]
