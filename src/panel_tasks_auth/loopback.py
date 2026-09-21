"""Loopback panel-tasks kimliği: mint, exchange, Bearer doğrulama, revoke/rotate.

HTTP bağlama `panel_tasks_server._require_auth` üzerinden `authenticate` çağırır.
Köprü ile aynı başlıklar: X-Kando-Token veya Authorization: Bearer.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass

MAX_TOKEN_BYTES = 512
EXCHANGE_TTL_S = 60
SESSION_TTL_S = 15 * 60
RATE_WINDOW_S = 60
RATE_MAX_EVENTS = 30
_BEARER = re.compile(r"^Bearer\s+(\S+)\s*$", re.IGNORECASE)


class AuthError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def pkce_verifier() -> str:
    return secrets.token_urlsafe(32)


def pkce_challenge_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def _looks_like_token(value: str) -> bool:
    if not value or len(value.encode("utf-8")) > MAX_TOKEN_BYTES:
        return False
    return True


def extract_presented_token(headers: dict[str, str]) -> str:
    folded = {str(k).lower(): str(v) for k, v in headers.items()}
    raw = (folded.get("x-kando-token") or "").strip()
    auth = (folded.get("authorization") or "").strip()
    match = _BEARER.match(auth)
    if match:
        raw = match.group(1).strip() or raw
    if len(raw.encode("utf-8")) > MAX_TOKEN_BYTES:
        raise AuthError("too_large")
    return raw


@dataclass
class _Exchange:
    code_digest: bytes
    challenge: str
    expires_at: float
    used: bool = False


@dataclass
class _Session:
    token_digest: bytes
    expires_at: float
    revoked: bool = False


class PanelTasksAuth:
    """Fail-closed store: boş sır ile mint/authenticate yok."""

    def __init__(
        self,
        *,
        secret: str,
        now: Callable[[], float] | None = None,
        exchange_ttl_s: int = EXCHANGE_TTL_S,
        session_ttl_s: int = SESSION_TTL_S,
        rate_max: int = RATE_MAX_EVENTS,
        rate_window_s: int = RATE_WINDOW_S,
    ) -> None:
        self._secret = (secret or "").strip()
        self._now = now or time.time
        self._exchange_ttl_s = exchange_ttl_s
        self._session_ttl_s = session_ttl_s
        self._rate_max = rate_max
        self._rate_window_s = rate_window_s
        self._exchanges: dict[bytes, _Exchange] = {}
        self._sessions: dict[bytes, _Session] = {}
        self._service: dict[bytes, _Session] = {}
        self._rate: dict[str, list[float]] = {}

    def _require_secret(self) -> None:
        if not self._secret:
            raise AuthError("missing_secret")

    def _touch_rate(self, key: str) -> None:
        now = self._now()
        bucket = [t for t in self._rate.get(key, []) if now - t < self._rate_window_s]
        if len(bucket) >= self._rate_max:
            self._rate[key] = bucket
            raise AuthError("rate_limited")
        bucket.append(now)
        self._rate[key] = bucket

    def mint_exchange_code(self, *, code_challenge: str, rate_key: str = "local") -> str:
        self._require_secret()
        self._touch_rate(f"mint:{rate_key}")
        challenge = (code_challenge or "").strip()
        if not challenge or not _looks_like_token(challenge):
            raise AuthError("too_large")
        code = secrets.token_urlsafe(32)
        digest = _digest(code)
        self._exchanges[digest] = _Exchange(
            code_digest=digest,
            challenge=challenge,
            expires_at=self._now() + self._exchange_ttl_s,
        )
        return code

    def exchange(self, *, code: str, code_verifier: str, rate_key: str = "local") -> str:
        self._require_secret()
        self._touch_rate(f"ex:{rate_key}")
        if not _looks_like_token(code) or not _looks_like_token(code_verifier):
            raise AuthError("too_large")
        rec = self._exchanges.get(_digest(code))
        if rec is None:
            raise AuthError("invalid_token")
        if rec.used:
            raise AuthError("replay")
        if self._now() >= rec.expires_at:
            raise AuthError("invalid_token")
        if not hmac.compare_digest(pkce_challenge_s256(code_verifier), rec.challenge):
            raise AuthError("pkce_mismatch")
        rec.used = True
        return self._mint_session()

    def mint_service_token(self, *, rate_key: str = "local") -> str:
        """CLI/E2E; tarayıcıya gömülmez."""
        self._require_secret()
        self._touch_rate(f"svc:{rate_key}")
        token = secrets.token_urlsafe(32)
        digest = _digest(token)
        self._service[digest] = _Session(
            token_digest=digest,
            expires_at=self._now() + self._session_ttl_s,
        )
        return token

    def authenticate(self, headers: dict[str, str]) -> str:
        self._require_secret()
        presented = extract_presented_token(headers)
        if not presented:
            raise AuthError("invalid_token")
        secret = self._secret
        presented_b = presented.encode("utf-8")
        secret_b = secret.encode("utf-8")
        if len(presented_b) == len(secret_b) and hmac.compare_digest(presented_b, secret_b):
            return "ok"
        digest = _digest(presented)
        rec = self._sessions.get(digest) or self._service.get(digest)
        if rec is None or rec.revoked or self._now() >= rec.expires_at:
            raise AuthError("invalid_token")
        return "ok"

    def revoke(self, token: str) -> None:
        self._require_secret()
        digest = _digest(token)
        rec = self._sessions.get(digest) or self._service.get(digest)
        if rec is None:
            raise AuthError("invalid_token")
        rec.revoked = True

    def rotate(self, token: str) -> str:
        self._require_secret()
        self.revoke(token)
        return self._mint_session()

    def _mint_session(self) -> str:
        token = secrets.token_urlsafe(32)
        digest = _digest(token)
        self._sessions[digest] = _Session(
            token_digest=digest,
            expires_at=self._now() + self._session_ttl_s,
        )
        return token
