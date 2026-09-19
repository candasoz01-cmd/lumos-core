"""In-process OAuth 2.1 AS for Alexa+ MCP account linking.

Contest-period local identity, not a production IdP. No dynamic client
registration. Two tiers match the Alexa+ MCP Toolkit:

- ``client_credentials`` + HTTP Basic → service token (initialize / tools/list)
- ``authorization_code`` + PKCE S256 → user token (tools/call)
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

SCOPE_SERVICE = "mcp:service"
SCOPE_TOOLS = "mcp:tools"
GRANT_CLIENT_CREDENTIALS = "client_credentials"
GRANT_AUTHORIZATION_CODE = "authorization_code"
GRANT_REFRESH_TOKEN = "refresh_token"

KIND_SERVICE = "service"
KIND_USER = "user"
KIND_LOCAL = "local"

_TOKEN_TTL_S = 3600
_CODE_TTL_S = 300


def s256_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def canonical_resource(public_url: str) -> str:
    return public_url.rstrip("/") + "/mcp"


def issuer_url(public_url: str) -> str:
    return public_url.rstrip("/")


def parse_basic_client(header: str | None) -> tuple[str, str] | None:
    if not header:
        return None
    scheme, _, rest = header.partition(" ")
    if scheme.lower() != "basic" or not rest.strip():
        return None
    try:
        decoded = base64.b64decode(rest.strip(), validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    client_id, sep, secret = decoded.partition(":")
    if not sep:
        return None
    return client_id, secret


@dataclass
class AccessToken:
    token: str
    kind: str
    client_id: str
    resource: str
    scope: str
    expires_at: float


@dataclass
class AuthCode:
    code: str
    client_id: str
    redirect_uri: str
    resource: str
    scope: str
    challenge: str
    expires_at: float


@dataclass
class RefreshRecord:
    token: str
    client_id: str
    resource: str
    scope: str


@dataclass
class AuthServer:
    public_url: str
    client_id: str
    client_secret: str
    redirect_uris: frozenset[str] = field(default_factory=frozenset)
    now: Any = time.time
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _access: dict[str, AccessToken] = field(default_factory=dict)
    _codes: dict[str, AuthCode] = field(default_factory=dict)
    _refresh: dict[str, RefreshRecord] = field(default_factory=dict)

    @property
    def issuer(self) -> str:
        return issuer_url(self.public_url)

    @property
    def resource(self) -> str:
        return canonical_resource(self.public_url)

    def authorization_server_metadata(self) -> dict[str, Any]:
        base = self.issuer
        return {
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "grant_types_supported": [
                GRANT_AUTHORIZATION_CODE,
                GRANT_CLIENT_CREDENTIALS,
                GRANT_REFRESH_TOKEN,
            ],
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
            ],
            "scopes_supported": [SCOPE_SERVICE, SCOPE_TOOLS],
            "registration_endpoint_supported": False,
        }

    def protected_resource_metadata(self) -> dict[str, Any]:
        return {
            "resource": self.resource,
            "authorization_servers": [self.issuer],
            "scopes_supported": [SCOPE_TOOLS],
            "bearer_methods_supported": ["header"],
        }

    def lookup(self, token: str) -> AccessToken | None:
        with self._lock:
            record = self._access.get(token)
            if record is None:
                return None
            if record.expires_at <= self.now():
                self._access.pop(token, None)
                return None
            return record

    def authorize(self, params: dict[str, str]) -> tuple[int, str | None, dict[str, Any] | None]:
        if params.get("response_type") != "code":
            return 400, None, {"error": "unsupported_response_type"}
        if params.get("client_id") != self.client_id:
            return 400, None, {"error": "invalid_client"}
        redirect = params.get("redirect_uri") or ""
        if redirect not in self.redirect_uris:
            return 400, None, {"error": "invalid_redirect_uri"}
        if params.get("code_challenge_method") != "S256":
            return 400, None, {"error": "invalid_request", "error_description": "S256 required"}
        challenge = params.get("code_challenge") or ""
        if len(challenge) < 43:
            return 400, None, {"error": "invalid_request", "error_description": "code_challenge"}
        resource = params.get("resource") or ""
        if resource != self.resource:
            return 400, None, {"error": "invalid_target"}
        scope = params.get("scope") or SCOPE_TOOLS
        if SCOPE_TOOLS not in scope.split():
            return 400, None, {"error": "invalid_scope"}
        code = secrets.token_urlsafe(32)
        record = AuthCode(
            code=code,
            client_id=self.client_id,
            redirect_uri=redirect,
            resource=resource,
            scope=SCOPE_TOOLS,
            challenge=challenge,
            expires_at=self.now() + _CODE_TTL_S,
        )
        with self._lock:
            self._codes[code] = record
        query = {"code": code}
        if params.get("state"):
            query["state"] = params["state"]
        location = _append_query(redirect, query)
        return 302, location, None

    def token(
        self,
        form: dict[str, str],
        basic: tuple[str, str] | None,
    ) -> tuple[int, dict[str, Any]]:
        client_id, client_secret = self._client_auth(form, basic)
        if client_id != self.client_id or not secrets.compare_digest(client_secret, self.client_secret):
            return 401, {"error": "invalid_client"}
        grant = form.get("grant_type")
        if grant == GRANT_CLIENT_CREDENTIALS:
            return self._client_credentials(form, client_id)
        if grant == GRANT_AUTHORIZATION_CODE:
            return self._authorization_code(form, client_id)
        if grant == GRANT_REFRESH_TOKEN:
            return self._refresh_grant(form, client_id)
        return 400, {"error": "unsupported_grant_type"}

    def _client_auth(self, form: dict[str, str], basic: tuple[str, str] | None) -> tuple[str, str]:
        if basic is not None:
            return basic
        return form.get("client_id") or "", form.get("client_secret") or ""

    def _client_credentials(self, form: dict[str, str], client_id: str) -> tuple[int, dict[str, Any]]:
        resource = form.get("resource") or ""
        if resource != self.resource:
            return 400, {"error": "invalid_target"}
        scope = form.get("scope") or SCOPE_SERVICE
        if scope != SCOPE_SERVICE:
            return 400, {"error": "invalid_scope"}
        return 200, self._issue(KIND_SERVICE, client_id, resource, SCOPE_SERVICE, refresh=False)

    def _authorization_code(self, form: dict[str, str], client_id: str) -> tuple[int, dict[str, Any]]:
        code = form.get("code") or ""
        verifier = form.get("code_verifier") or ""
        redirect = form.get("redirect_uri") or ""
        resource = form.get("resource") or ""
        with self._lock:
            record = self._codes.pop(code, None)
        if record is None or record.expires_at <= self.now():
            return 400, {"error": "invalid_grant"}
        if record.client_id != client_id or record.redirect_uri != redirect:
            return 400, {"error": "invalid_grant"}
        if resource != record.resource or resource != self.resource:
            return 400, {"error": "invalid_target"}
        if s256_challenge(verifier) != record.challenge:
            return 400, {"error": "invalid_grant"}
        return 200, self._issue(KIND_USER, client_id, resource, record.scope, refresh=True)

    def _refresh_grant(self, form: dict[str, str], client_id: str) -> tuple[int, dict[str, Any]]:
        presented = form.get("refresh_token") or ""
        resource = form.get("resource") or ""
        with self._lock:
            record = self._refresh.pop(presented, None)
        if record is None or record.client_id != client_id:
            return 400, {"error": "invalid_grant"}
        if resource and resource != record.resource:
            return 400, {"error": "invalid_target"}
        return 200, self._issue(KIND_USER, client_id, record.resource, record.scope, refresh=True)

    def _issue(
        self,
        kind: str,
        client_id: str,
        resource: str,
        scope: str,
        *,
        refresh: bool,
    ) -> dict[str, Any]:
        access = secrets.token_urlsafe(32)
        record = AccessToken(
            token=access,
            kind=kind,
            client_id=client_id,
            resource=resource,
            scope=scope,
            expires_at=self.now() + _TOKEN_TTL_S,
        )
        payload: dict[str, Any] = {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": _TOKEN_TTL_S,
            "scope": scope,
            "resource": resource,
        }
        with self._lock:
            self._access[access] = record
            if refresh:
                refresh_token = secrets.token_urlsafe(32)
                self._refresh[refresh_token] = RefreshRecord(
                    token=refresh_token,
                    client_id=client_id,
                    resource=resource,
                    scope=scope,
                )
                payload["refresh_token"] = refresh_token
        return payload


def _append_query(url: str, extra: dict[str, str]) -> str:
    parts = urlsplit(url)
    query = parts.query
    encoded = urlencode(extra)
    merged = f"{query}&{encoded}" if query else encoded
    return urlunsplit((parts.scheme, parts.netloc, parts.path, merged, parts.fragment))
