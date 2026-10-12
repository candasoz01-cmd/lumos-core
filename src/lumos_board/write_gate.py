"""KA-003 write authorization: HMAC identity + ACTIVE claim before write."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from lumos_board.task_claim import (
    ClaimError,
    ClaimStatus,
    TaskClaim,
    TaskClaimStore,
    _b64url_decode,
    _b64url_encode,
    _clean_text,
    _format_time,
    _normalize_scopes,
    _parse_time,
    _required_text,
    _scopes_within,
)

WRITE_TOKEN_SCHEMA = "lumos.write_credential.v1"
WRITE_CREDENTIAL_STORE_SCHEMA = "lumos.write_credential_store.v1"
WRITE_VERIFICATION_METHOD = "hmac-sha256"

REASON_ALLOWED = "WRITE_ALLOWED"
REASON_UNCONFIGURED = "WRITE_GATE_UNCONFIGURED"
REASON_NO_CREDENTIAL = "WRITE_NO_CREDENTIAL"
REASON_UNAUTHORIZED = "WRITE_UNAUTHORIZED"
REASON_IDENTITY = "WRITE_IDENTITY_MISMATCH"
REASON_NO_CLAIM = "WRITE_NO_CLAIM"
REASON_SCOPE = "WRITE_SCOPE_DENIED"
REASON_CONSUMED = "WRITE_TOKEN_CONSUMED"


@dataclass(frozen=True)
class WriteDecision:
    allowed: bool
    reason: str
    claim_id: str | None = None
    credential_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "claim_id": self.claim_id,
            "credential_id": self.credential_id,
        }


class WriteGate:
    """Issue and check write credentials bound to an ACTIVE KA-002 claim."""

    def __init__(self, claims: TaskClaimStore, *, secret: str | None) -> None:
        self._claims = claims
        self._secret = (secret or "").encode("utf-8")
        self._path = claims.store_dir / "write_credentials.json"

    def configured(self) -> bool:
        return len(self._secret) >= 32

    def issue(self, claim: TaskClaim) -> str:
        if not self.configured():
            raise ClaimError("yazma kapısı için LUMOS_WRITE_GATE_SECRET (en az 32 byte) gerekli")
        if claim.status is not ClaimStatus.ACTIVE:
            raise ClaimError("yazma jetonu yalnız ACTIVE claim için basılır")
        now = datetime.now(timezone.utc)
        payload = {
            "schema": WRITE_TOKEN_SCHEMA,
            "credential_id": str(uuid.uuid4()),
            "claim_id": claim.claim_id,
            "owner": claim.owner,
            "issued_at": _format_time(now),
            "expires_at": _format_time(claim.expires_at),
            "verification_method": WRITE_VERIFICATION_METHOD,
        }
        payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        signature = hmac.new(self._secret, payload_bytes, hashlib.sha256).digest()
        token = f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"
        records = self._read_records()
        records[claim.claim_id] = {
            "schema": WRITE_CREDENTIAL_STORE_SCHEMA,
            "claim_id": claim.claim_id,
            "credential_id": payload["credential_id"],
            "owner": claim.owner,
            "status": "issued",
            "token_hash": hashlib.sha256(token.encode("ascii")).hexdigest(),
            "issued_at": payload["issued_at"],
        }
        self._write_records(records)
        return token

    def revoke(self, claim_id: str) -> None:
        records = self._read_records()
        if claim_id in records:
            del records[claim_id]
            self._write_records(records)

    def check(
        self,
        *,
        token: str | None,
        owner: str,
        paths: Sequence[str],
        consume: bool = False,
    ) -> WriteDecision:
        if not self.configured():
            return WriteDecision(False, REASON_UNCONFIGURED)
        if not token or not str(token).strip():
            return WriteDecision(False, REASON_NO_CREDENTIAL)
        try:
            owner = _clean_text(owner, "owner")
            normalized_paths = _normalize_scopes(paths)
            claim_id, token_owner, credential_id = self._verify_token(token)
        except ClaimError:
            return WriteDecision(False, REASON_UNAUTHORIZED)
        if token_owner != owner:
            return WriteDecision(False, REASON_IDENTITY, claim_id, credential_id)
        records = self._read_records()
        stored = records.get(claim_id)
        if not isinstance(stored, dict):
            return WriteDecision(False, REASON_NO_CREDENTIAL, claim_id, credential_id)
        if stored.get("status") == "consumed":
            return WriteDecision(False, REASON_CONSUMED, claim_id, credential_id)
        expected_hash = stored.get("token_hash")
        actual_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        if not isinstance(expected_hash, str) or not hmac.compare_digest(expected_hash, actual_hash):
            return WriteDecision(False, REASON_UNAUTHORIZED, claim_id, credential_id)
        stored_cred = stored.get("credential_id")
        if isinstance(stored_cred, str) and stored_cred != credential_id:
            return WriteDecision(False, REASON_UNAUTHORIZED, claim_id, credential_id)
        claim = next(
            (
                item
                for item in self._claims.list_claims(include_closed=False)
                if item.claim_id == claim_id
            ),
            None,
        )
        if claim is None or claim.status is not ClaimStatus.ACTIVE:
            return WriteDecision(False, REASON_NO_CLAIM, claim_id, credential_id)
        if claim.owner != owner:
            return WriteDecision(False, REASON_IDENTITY, claim_id, credential_id)
        if not _scopes_within(normalized_paths, claim.scopes):
            return WriteDecision(False, REASON_SCOPE, claim_id, credential_id)
        if consume:
            stored["status"] = "consumed"
            stored["consumed_at"] = _format_time(datetime.now(timezone.utc))
            records[claim_id] = stored
            self._write_records(records)
        return WriteDecision(True, REASON_ALLOWED, claim_id, credential_id)

    def _verify_token(self, token: str) -> tuple[str, str, str]:
        try:
            encoded_payload, encoded_signature = _clean_text(token, "write_token").split(".", 1)
            payload_bytes = _b64url_decode(encoded_payload)
            signature = _b64url_decode(encoded_signature)
            expected = hmac.new(self._secret, payload_bytes, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected):
                raise ClaimError("yazma jetonu imzası geçersiz")
            payload = json.loads(payload_bytes)
            if not isinstance(payload, dict) or payload.get("schema") != WRITE_TOKEN_SCHEMA:
                raise ClaimError("yazma jetonu şeması geçersiz")
            if payload.get("verification_method") != WRITE_VERIFICATION_METHOD:
                raise ClaimError("yazma doğrulama yöntemi geçersiz")
            expires_at = _parse_time(_required_text(payload, "expires_at"))
            issued_at = _parse_time(_required_text(payload, "issued_at"))
            now = datetime.now(timezone.utc)
            if issued_at > now or expires_at <= now:
                raise ClaimError("yazma jetonu süresi geçersiz")
            return (
                _required_text(payload, "claim_id"),
                _required_text(payload, "owner"),
                _required_text(payload, "credential_id"),
            )
        except ClaimError:
            raise
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError, KeyError) as exc:
            raise ClaimError("yazma jetonu geçersiz") from exc

    def _read_records(self) -> dict[str, object]:
        if not self._path.is_file():
            return {}
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ClaimError("yazma kimlik deposu okunamıyor") from exc
        if not isinstance(payload, dict) or payload.get("schema") != WRITE_CREDENTIAL_STORE_SCHEMA:
            raise ClaimError("yazma kimlik deposu şeması geçersiz")
        records = payload.get("records")
        if not isinstance(records, dict):
            raise ClaimError("yazma kimlik kayıtları geçersiz")
        return dict(records)

    def _write_records(self, records: dict[str, object]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": WRITE_CREDENTIAL_STORE_SCHEMA, "records": records}
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
