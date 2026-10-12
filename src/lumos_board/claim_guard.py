"""Commit-bound claim attestations for the KA-003 claim-guard CI check.

A later claim record cannot authorize an earlier commit: the HMAC payload
must live in that commit's message and cover that commit's paths, with
issued_at at or before the committer timestamp.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

from lumos_board.task_claim import (
    ClaimError,
    _b64url_decode,
    _b64url_encode,
    _clean_text,
    _format_time,
    _normalize_scopes,
    _parse_time,
    _required_text,
    _scopes_within,
)
from lumos_board.write_gate import WriteGate

ATTESTATION_SCHEMA = "lumos.claim_commit_attestation.v1"
ATTESTATION_TRAILER = "Lumos-Claim-Attestation"
VERIFICATION_METHOD = "hmac-sha256"
_CLOCK_SKEW = timedelta(seconds=60)

REASON_OK = "CLAIM_GUARD_OK"
REASON_UNCONFIGURED = "CLAIM_GUARD_UNCONFIGURED"
REASON_EMPTY = "CLAIM_GUARD_EMPTY_RANGE"
REASON_MISSING = "CLAIM_GUARD_MISSING_ATTESTATION"
REASON_UNAUTHORIZED = "CLAIM_GUARD_UNAUTHORIZED"
REASON_TIME = "CLAIM_GUARD_ISSUED_AFTER_COMMIT"
REASON_PARENT = "CLAIM_GUARD_PARENT_MISMATCH"
REASON_PATHS = "CLAIM_GUARD_PATHS_MISMATCH"
REASON_SCOPE = "CLAIM_GUARD_SCOPE_DENIED"


@dataclass(frozen=True)
class CommitVerdict:
    commit: str
    allowed: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {"commit": self.commit, "allowed": self.allowed, "reason": self.reason}


@dataclass(frozen=True)
class RangeVerdict:
    allowed: bool
    reason: str
    commits: tuple[CommitVerdict, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "commits": [item.to_dict() for item in self.commits],
        }


class ClaimGuard:
    def __init__(self, *, secret: str | None) -> None:
        self._secret = (secret or "").encode("utf-8")

    def configured(self) -> bool:
        return len(self._secret) >= 32

    def attest(
        self,
        *,
        write_gate: WriteGate,
        token: str,
        owner: str,
        paths: Sequence[str],
        parent_sha: str,
        claim_id: str,
        task_id: str,
        scopes: Sequence[str],
        issued_at: datetime | None = None,
    ) -> str:
        if not self.configured():
            raise ClaimError("claim-guard için LUMOS_WRITE_GATE_SECRET (en az 32 byte) gerekli")
        decision = write_gate.check(token=token, owner=owner, paths=paths)
        if not decision.allowed:
            raise ClaimError(f"yazma yetkisi yok: {decision.reason}")
        issued = issued_at or datetime.now(timezone.utc)
        payload = {
            "schema": ATTESTATION_SCHEMA,
            "claim_id": _clean_text(claim_id, "claim_id"),
            "task_id": _clean_text(task_id, "task_id"),
            "owner": _clean_text(owner, "owner"),
            "scopes": list(_normalize_scopes(scopes)),
            "paths": list(_normalize_scopes(paths)),
            "parent_sha": _clean_text(parent_sha, "parent_sha"),
            "issued_at": _format_time(issued),
            "verification_method": VERIFICATION_METHOD,
        }
        return self._sign(payload)

    def verify_range(self, repo: Path, *, base: str, head: str) -> RangeVerdict:
        if not self.configured():
            return RangeVerdict(False, REASON_UNCONFIGURED, ())
        commits = _rev_list(repo, base, head)
        if not commits:
            return RangeVerdict(False, REASON_EMPTY, ())
        verdicts: list[CommitVerdict] = []
        for sha in commits:
            verdicts.append(self._verify_commit(repo, sha))
        failed = next((item for item in verdicts if not item.allowed), None)
        if failed is not None:
            return RangeVerdict(False, failed.reason, tuple(verdicts))
        return RangeVerdict(True, REASON_OK, tuple(verdicts))

    def _verify_commit(self, repo: Path, sha: str) -> CommitVerdict:
        token = _trailer(repo, sha)
        if token is None:
            return CommitVerdict(sha, False, REASON_MISSING)
        try:
            payload = self._open(token)
            issued_at = _parse_time(_required_text(payload, "issued_at"))
            committer = _committer_time(repo, sha)
            if issued_at - _CLOCK_SKEW > committer:
                return CommitVerdict(sha, False, REASON_TIME)
            parent = _parent_sha(repo, sha)
            if _required_text(payload, "parent_sha") != parent:
                return CommitVerdict(sha, False, REASON_PARENT)
            attested_paths = payload.get("paths")
            if not isinstance(attested_paths, list) or not all(isinstance(p, str) for p in attested_paths):
                return CommitVerdict(sha, False, REASON_UNAUTHORIZED)
            changed = _changed_paths(repo, sha)
            if tuple(_normalize_scopes(attested_paths)) != changed:
                return CommitVerdict(sha, False, REASON_PATHS)
            scopes = payload.get("scopes")
            if not isinstance(scopes, list) or not all(isinstance(p, str) for p in scopes):
                return CommitVerdict(sha, False, REASON_UNAUTHORIZED)
            if not _scopes_within(changed, _normalize_scopes(scopes)):
                return CommitVerdict(sha, False, REASON_SCOPE)
        except ClaimError:
            return CommitVerdict(sha, False, REASON_UNAUTHORIZED)
        return CommitVerdict(sha, True, REASON_OK)

    def _sign(self, payload: dict[str, object]) -> str:
        payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        signature = hmac.new(self._secret, payload_bytes, hashlib.sha256).digest()
        return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"

    def _open(self, token: str) -> dict[str, object]:
        try:
            encoded_payload, encoded_signature = _clean_text(token, "attestation").split(".", 1)
            payload_bytes = _b64url_decode(encoded_payload)
            signature = _b64url_decode(encoded_signature)
            expected = hmac.new(self._secret, payload_bytes, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected):
                raise ClaimError("claim attestation imzası geçersiz")
            payload = json.loads(payload_bytes)
        except ClaimError:
            raise
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError, KeyError) as exc:
            raise ClaimError("claim attestation geçersiz") from exc
        if not isinstance(payload, dict) or payload.get("schema") != ATTESTATION_SCHEMA:
            raise ClaimError("claim attestation şeması geçersiz")
        if payload.get("verification_method") != VERIFICATION_METHOD:
            raise ClaimError("claim attestation yöntemi geçersiz")
        return payload


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ClaimError(result.stderr.strip() or "git komutu başarısız")
    return result.stdout


def _rev_list(repo: Path, base: str, head: str) -> tuple[str, ...]:
    out = _git(repo, "rev-list", "--reverse", "--no-merges", f"{base}..{head}")
    return tuple(line.strip() for line in out.splitlines() if line.strip())


def _trailer(repo: Path, sha: str) -> str | None:
    message = _git(repo, "log", "-1", "--format=%B", sha)
    prefix = f"{ATTESTATION_TRAILER}: "
    for line in message.splitlines():
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            return value or None
    return None


def _committer_time(repo: Path, sha: str) -> datetime:
    raw = _git(repo, "log", "-1", "--format=%cI", sha).strip()
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parent_sha(repo: Path, sha: str) -> str:
    out = _git(repo, "rev-list", "--parents", "-n", "1", sha).strip().split()
    if len(out) < 2:
        return "0" * 40
    return out[1]


def _changed_paths(repo: Path, sha: str) -> tuple[str, ...]:
    raw = subprocess.run(
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-z", "--no-renames", "-r", sha],
        check=True,
        capture_output=True,
    )
    parts = [p.decode("utf-8") for p in raw.stdout.split(b"\0") if p]
    if not parts:
        raise ClaimError("commit dosya listesi boş")
    return _normalize_scopes(parts)
