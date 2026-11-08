"""Head-bound production attestation. The token lives outside the commit.

A commit message cannot carry that commit's own SHA: the SHA is a hash of
the message. This attestation therefore binds ``head_sha`` in an HMAC whose
carrier is a check run, not a trailer. The signing secret never enters the
token, the check-run body, or the command output.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from lumos_board.central_store import STATE_FILE, parse_state_text
from lumos_board.task_claim import (
    ClaimError,
    ClaimStatus,
    TaskClaim,
    _b64url_decode,
    _b64url_encode,
    _clean_text,
    _format_time,
    _required_text,
)

HEAD_SCHEMA = "lumos.claim_head_attestation.v1"
CHECK_NAME = "write-attest-sign"
ENVIRONMENT_NAME = "lumos-write-gate"
CLAIM_TRAILER = "Lumos-Claim"
# The sign job fetches this ref before the CLI runs. The CLI only reads it.
SIGN_BOARD_REF = "refs/remotes/origin/claude/lumos-board"

REASON_OK = "HEAD_ATTEST_OK"
REASON_UNCONFIGURED = "HEAD_ATTEST_UNCONFIGURED"
REASON_TRIGGER = "HEAD_ATTEST_UNAUTHORIZED_TRIGGER"
REASON_PR_CODE = "HEAD_ATTEST_PR_CODE_REFUSED"
REASON_MISMATCH = "HEAD_ATTEST_CLAIM_MISMATCH"
REASON_EXPIRED = "HEAD_ATTEST_CLAIM_EXPIRED"
REASON_INACTIVE = "HEAD_ATTEST_CLAIM_INACTIVE"
REASON_SHA = "HEAD_ATTEST_SHA_MISMATCH"
REASON_UNAUTHORIZED = "HEAD_ATTEST_UNAUTHORIZED"


@dataclass(frozen=True)
class HeadVerdict:
    allowed: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {"allowed": self.allowed, "reason": self.reason}


def authorize_dispatch(*, event_name: str, ref: str, code_sha: str, main_sha: str) -> None:
    """Refuse every trigger except a main-ref dispatch running main's code."""
    if event_name != "workflow_dispatch" or ref != "refs/heads/main":
        raise ClaimError(REASON_TRIGGER)
    if not _sha(code_sha) or not _sha(main_sha) or code_sha != main_sha:
        raise ClaimError(REASON_PR_CODE)


def sign_head(
    *,
    secret: str | None,
    head_sha: str,
    claim: TaskClaim,
    trailer_claim_ids: tuple[str, ...],
    actor: str,
    now: datetime | None = None,
) -> str:
    if not _configured(secret):
        raise ClaimError(REASON_UNCONFIGURED)
    _require_active(claim, now or datetime.now(timezone.utc))
    if not _sha(head_sha):
        raise ClaimError(REASON_SHA)
    if trailer_claim_ids != (claim.claim_id,):
        raise ClaimError(REASON_MISMATCH)
    actor_text = _clean_text(actor, "actor")
    payload = {
        "schema": HEAD_SCHEMA,
        "head_sha": head_sha,
        "claim_id": claim.claim_id,
        "task_id": claim.task_id,
        "scopes": list(claim.scopes),
        "actor": actor_text,
        "issued_at": _format_time(now or datetime.now(timezone.utc)),
    }
    return _sign(secret or "", payload)


def verify_head(
    *,
    secret: str | None,
    token: str,
    head_sha: str,
    claim: TaskClaim,
    trailer_claim_ids: tuple[str, ...],
    now: datetime | None = None,
) -> HeadVerdict:
    if not _configured(secret):
        return HeadVerdict(False, REASON_UNCONFIGURED)
    try:
        payload = _open(secret or "", token)
    except ClaimError:
        return HeadVerdict(False, REASON_UNAUTHORIZED)
    if payload.get("head_sha") != head_sha:
        return HeadVerdict(False, REASON_SHA)
    if payload.get("claim_id") != claim.claim_id:
        return HeadVerdict(False, REASON_MISMATCH)
    if payload.get("task_id") != claim.task_id:
        return HeadVerdict(False, REASON_MISMATCH)
    if payload.get("scopes") != list(claim.scopes):
        return HeadVerdict(False, REASON_MISMATCH)
    try:
        _require_active(claim, now or datetime.now(timezone.utc))
    except ClaimError as exc:
        return HeadVerdict(False, str(exc))
    if trailer_claim_ids != (claim.claim_id,):
        return HeadVerdict(False, REASON_MISMATCH)
    return HeadVerdict(True, REASON_OK)


def check_run_body(*, attestation: str, head_sha: str) -> dict[str, object]:
    if not _sha(head_sha):
        raise ClaimError(REASON_SHA)
    return {
        "name": CHECK_NAME,
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": "success",
        "output": {"title": "Head attestation", "summary": attestation},
    }


def trailer_claim_ids_from_message(message: str) -> tuple[str, ...]:
    prefix = f"{CLAIM_TRAILER}: "
    return tuple(line[len(prefix) :].strip() for line in message.splitlines() if line.startswith(prefix))


def trailer_claim_ids(repo: Path, sha: str) -> tuple[str, ...]:
    return trailer_claim_ids_from_message(_git(repo, "log", "-1", "--format=%B", sha))


def _require_active(claim: TaskClaim, now: datetime) -> None:
    status = claim.status
    if status is ClaimStatus.ACTIVE and claim.expires_at <= now:
        status = ClaimStatus.EXPIRED
    if status is ClaimStatus.EXPIRED:
        raise ClaimError(REASON_EXPIRED)
    if status is not ClaimStatus.ACTIVE:
        raise ClaimError(REASON_INACTIVE)


def _configured(secret: str | None) -> bool:
    return len(secret or "") >= 32


def _sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def _sign(secret: str, payload: dict[str, object]) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return f"{_b64url_encode(body)}.{_b64url_encode(signature)}"


def _open(secret: str, token: str) -> dict[str, object]:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        body = _b64url_decode(encoded_payload)
        signature = _b64url_decode(encoded_signature)
        expected = hmac.new(secret.encode(), body, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ClaimError(REASON_UNAUTHORIZED)
        payload = json.loads(body)
    except ClaimError:
        raise
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClaimError(REASON_UNAUTHORIZED) from exc
    if not isinstance(payload, dict) or payload.get("schema") != HEAD_SCHEMA:
        raise ClaimError(REASON_UNAUTHORIZED)
    _required_text(payload, "head_sha")
    _required_text(payload, "claim_id")
    _required_text(payload, "task_id")
    _required_text(payload, "actor")
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


def _read_sign_claim(repo: Path, claim_id: str) -> TaskClaim:
    """Read one claim from the already-fetched board ref.

    ``git show`` only. No fetch, no ``list_claims``, no expire, no promote,
    no push. A stored ACTIVE lease with ``expires_at <= now`` stays ACTIVE
    in the file; ``sign_head`` treats that lease as expired and refuses.
    """
    text = _git(repo, "show", f"{SIGN_BOARD_REF}:{STATE_FILE}")
    claim = next((item for item in parse_state_text(text) if item.claim_id == claim_id), None)
    if claim is None:
        raise ClaimError(REASON_MISMATCH)
    return claim


def _cli_sign(argv: list[str]) -> int:
    authorize_dispatch(
        event_name=_arg(argv, "event-name"),
        ref=_arg(argv, "ref"),
        code_sha=_arg(argv, "code-sha"),
        main_sha=_arg(argv, "main-sha"),
    )
    head_sha = _arg(argv, "head-sha")
    claim_id = _arg(argv, "claim-id")
    repo = Path(_arg(argv, "repo") or ".")
    claim = _read_sign_claim(repo, claim_id)
    message_file = _arg(argv, "message-file")
    trailers = (
        trailer_claim_ids_from_message(Path(message_file).read_text(encoding="utf-8"))
        if message_file
        else trailer_claim_ids(repo, head_sha)
    )
    token = sign_head(
        secret=os.environ.get("LUMOS_WRITE_GATE_SECRET"),
        head_sha=head_sha,
        claim=claim,
        trailer_claim_ids=trailers,
        actor=_arg(argv, "actor"),
    )
    sys.stdout.write(
        json.dumps(
            {
                "attestation": token,
                "head_sha": head_sha,
                "claim_id": claim.claim_id,
                "task_id": claim.task_id,
                "actor": _arg(argv, "actor"),
            },
            sort_keys=True,
        )
        + "\n"
    )
    verdict = verify_head(
        secret=os.environ.get("LUMOS_WRITE_GATE_SECRET"),
        token=token,
        head_sha=head_sha,
        claim=claim,
        trailer_claim_ids=trailers,
    )
    if not verdict.allowed:
        raise ClaimError(verdict.reason)
    return 0


def _cli_publish(argv: list[str]) -> int:
    path = Path(_arg(argv, "file"))
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ClaimError(REASON_UNAUTHORIZED)
    body = check_run_body(
        attestation=_required_text(loaded, "attestation"),
        head_sha=_required_text(loaded, "head_sha"),
    )
    sys.stdout.write(json.dumps(body, sort_keys=True) + "\n")
    return 0


def _arg(argv: list[str], name: str) -> str:
    token = f"--{name}"
    for index, item in enumerate(argv):
        if item == token and index + 1 < len(argv):
            return argv[index + 1]
        if item.startswith(f"{token}="):
            return item.split("=", 1)[1]
    return ""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if any(item == "--secret" or item.startswith("--secret=") for item in argv):
        sys.stderr.write(REASON_UNAUTHORIZED + "\n")
        return 2
    try:
        command = argv[0] if argv else ""
        if command == "sign":
            return _cli_sign(argv[1:])
        if command == "publish-body":
            return _cli_publish(argv[1:])
    except ClaimError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    sys.stderr.write("usage: python -m lumos_board.head_attestation sign|publish-body\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
