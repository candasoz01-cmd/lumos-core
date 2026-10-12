"""Central (shared) backend for Lumos Board task claims.

Why this exists
---------------
``TaskClaimStore`` keeps ``claims.json`` under each clone's git common dir and
serialises writers with ``flock``. That lock is only as wide as one machine's
filesystem: a cloud agent, a Cursor agent and the founder's Mac each had their
own board and could not see each other's claims (2026-10-12: two agents wrote
the same PR branch at once).

``CentralClaimStore`` keeps exactly the same claim rules (conflicts, queue,
delegation, override, expiry, audit) — it *is* a ``TaskClaimStore`` — and only
replaces where the state lives: one git ref on the shared remote
(``refs/heads/claude/lumos-board`` by default) holding ``claims.json`` and
``claim_events.jsonl``.

Atomicity
---------
Every transaction is: fetch the ref → apply the unchanged in-memory rules →
write a commit whose parent is the fetched commit → plain (non-force) push.
The remote accepts the push only if the ref still points at the parent, so of
two agents racing on the same base exactly one wins; the loser's push is
rejected as non-fast-forward, its in-memory result is discarded and the whole
operation is re-run against the new state, where it now sees the winner's
claim and gets ``SCOPE_CONFLICT`` / ``DUPLICATE_TASK``.

Fail-closed
-----------
If the remote cannot be read or written for any reason other than losing the
race, the operation raises ``CentralStoreUnavailable`` (a ``ClaimError``). It
never falls back to a local lock. Local mode exists only when the caller asks
for it explicitly (``--store`` / ``LUMOS_BOARD_DIR``).

The ref is never force-pushed by this module; its history is the audit trail.
"""

from __future__ import annotations

import fcntl
import json
import os
import random
import re
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from lumos_board.task_claim import (
    CLAIM_EVENT_SCHEMA,
    CLAIM_STORE_SCHEMA,
    ClaimError,
    ClaimResult,
    ClaimStatus,
    ClaimStoreCorrupt,
    DelegationVerifier,
    OverrideApprovalVerifier,
    TaskClaim,
    TaskClaimStore,
    _find_conflicts,
    _format_time,
)

DEFAULT_REF = "refs/heads/claude/lumos-board"
STATE_FILE = "claims.json"
EVENTS_FILE = "claim_events.jsonl"
# The board ref is a branch (the only ref namespace every agent can push), so
# its commits carry a vercel.json that turns preview deployments off for them.
_BOARD_VERCEL_JSON = '{"git": {"deploymentEnabled": false}}\n'
_BOARD_README = (
    "Lumos Board central claim store. Written only by "
    "`python -m lumos_board.claim_cli`; never edit or force-push by hand.\n"
)
_COMMITTER_NAME = "lumos-board"
_COMMITTER_EMAIL = "lumos-board@users.noreply.github.com"
_MAX_ERROR_TEXT = 300
# Claim ids are uuid4 strings minted by TaskClaimStore. Anything else on the
# shared board (e.g. a hand-pushed "$(cmd)") is treated as corruption so it
# never reaches hooks, trailers or CI output.
_CLAIM_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


class CentralStoreUnavailable(ClaimError):
    """The shared board could not be read or written. Never fall back to local."""


class _CasLost(Exception):
    """Another writer advanced the ref first; the transaction must be re-run."""


@dataclass(frozen=True)
class ImportReport:
    imported: tuple[str, ...]
    already_present: tuple[str, ...]
    skipped_closed: tuple[str, ...]
    conflicts: tuple[dict[str, object], ...]
    needs_reclaim: tuple[dict[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "imported": list(self.imported),
            "already_present": list(self.already_present),
            "skipped_closed": list(self.skipped_closed),
            "conflicts": list(self.conflicts),
            "needs_reclaim": list(self.needs_reclaim),
        }


def parse_state_text(text: str) -> list[TaskClaim]:
    """Same validation as ``TaskClaimStore._read_state`` for a text blob."""
    try:
        payload = json.loads(text)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ClaimStoreCorrupt("claim deposu okunamıyor") from exc
    if not isinstance(payload, dict) or payload.get("schema") != CLAIM_STORE_SCHEMA:
        raise ClaimStoreCorrupt("claim deposu şeması geçersiz")
    values = payload.get("claims")
    if not isinstance(values, list):
        raise ClaimStoreCorrupt("claim listesi geçersiz")
    claims = [TaskClaim.from_dict(value) for value in values]
    for claim in claims:
        if not _CLAIM_ID.fullmatch(claim.claim_id) or (
            claim.parent_claim_id is not None and not _CLAIM_ID.fullmatch(claim.parent_claim_id)
        ):
            raise ClaimStoreCorrupt("claim kimliği geçersiz")
    return claims


def serialize_state(claims: Sequence[TaskClaim]) -> str:
    """Byte-identical to ``TaskClaimStore._write_state`` output."""
    payload = {"schema": CLAIM_STORE_SCHEMA, "claims": [claim.to_dict() for claim in claims]}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"


def _trim(text: str) -> str:
    text = " ".join((text or "").split())
    return text[:_MAX_ERROR_TEXT]


class CentralClaimStore(TaskClaimStore):
    """``TaskClaimStore`` whose state lives on one shared git ref (CAS by push)."""

    def __init__(
        self,
        *,
        remote: str,
        cache_dir: Path,
        ref: str = DEFAULT_REF,
        clock: Callable[[], datetime] | None = None,
        override_verifier: OverrideApprovalVerifier | None = None,
        delegation_verifier: DelegationVerifier | None = None,
        max_attempts: int = 12,
        git_timeout: float = 60.0,
    ) -> None:
        if not isinstance(remote, str) or not remote.strip():
            raise CentralStoreUnavailable("merkezi pano remote'u yapılandırılmamış")
        if not ref.startswith("refs/heads/"):
            raise ClaimError("merkezi pano ref'i refs/heads/ altında olmalı")
        self.cache_dir = Path(cache_dir)
        # The mirror is a read-only copy for wall_observer / agent_status.
        super().__init__(
            self.cache_dir / "mirror",
            clock=clock,
            override_verifier=override_verifier,
            delegation_verifier=delegation_verifier,
        )
        self.remote = remote.strip()
        self.ref = ref
        self._git_dir = self.cache_dir / "repo.git"
        self._tracking_ref = "refs/lumos-board/remote"
        self._max_attempts = max(1, int(max_attempts))
        self._git_timeout = git_timeout
        self._last_base: str | None = None

    # -- public API: every operation is one CAS transaction, re-run on loss --

    def claim(self, **kwargs: Any) -> ClaimResult:  # type: ignore[override]
        return self._transact(super().claim, **kwargs)

    def heartbeat(self, claim_id: str, *, owner: str, ttl_seconds: int = 1800) -> TaskClaim:
        return self._transact(super().heartbeat, claim_id, owner=owner, ttl_seconds=ttl_seconds)

    def release(self, claim_id: str, *, owner: str) -> TaskClaim:
        return self._transact(super().release, claim_id, owner=owner)

    def attach_pr(self, claim_id: str, *, owner: str, pr_ref: str) -> TaskClaim:
        return self._transact(super().attach_pr, claim_id, owner=owner, pr_ref=pr_ref)

    def list_claims(self, *, include_closed: bool = False) -> tuple[TaskClaim, ...]:
        return self._transact(super().list_claims, include_closed=include_closed)

    @property
    def last_base(self) -> str | None:
        """Commit of the board state the last successful transaction ended on."""
        return self._last_base

    def import_local(self, source_dir: Path, *, actor: str) -> ImportReport:
        """Copy open claims of a local board into the central one (source untouched).

        Claims keep their ids, owners and lease times. An open local claim that
        collides with a central one is NOT imported and is reported instead —
        the central board stays the single truth, nothing is silently merged.

        Delegated (child) claims are never imported: their ``parent_claim_id``
        is only meaningful after ``DelegationVerifier`` checked a signed token,
        which cannot be re-verified from a local file. An unverified parent
        pointer would let a writer bypass the parent's scope lock, so such
        claims are reported as ``needs_reclaim`` and must be re-claimed with a
        fresh delegation token.
        """
        source = Path(source_dir) / STATE_FILE
        if not source.exists():
            return ImportReport((), (), (), ())
        try:
            text = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise ClaimStoreCorrupt("yerel claim deposu okunamıyor") from exc
        try:
            local_claims = sorted(parse_state_text(text), key=lambda c: (c.started_at, c.claim_id))
        except ClaimStoreCorrupt as exc:
            raise ClaimStoreCorrupt(f"yerel claim deposu geçersiz: {exc}") from exc
        return self._transact(self._import_claims, local_claims, actor=actor)

    def _import_claims(self, local_claims: Sequence[TaskClaim], *, actor: str) -> ImportReport:
        imported: list[str] = []
        present: list[str] = []
        closed: list[str] = []
        conflicts: list[dict[str, object]] = []
        reclaim: list[dict[str, object]] = []
        with self._locked_state() as claims:
            now = self._now()
            self._expire_stale(claims, now)
            known = {claim.claim_id for claim in claims}
            for item in local_claims:
                if item.claim_id in known:
                    present.append(item.claim_id)
                    continue
                if item.status not in {ClaimStatus.ACTIVE, ClaimStatus.QUEUED} or (
                    item.status is ClaimStatus.ACTIVE and item.expires_at <= now
                ):
                    closed.append(item.claim_id)
                    continue
                if item.parent_claim_id is not None:
                    reclaim.append(
                        {
                            "claim_id": item.claim_id,
                            "task_id": item.task_id,
                            "owner": item.owner,
                            "reason": "delegation_not_reverifiable",
                        }
                    )
                    continue
                blockers = _find_conflicts(
                    claims,
                    task_id=item.task_id,
                    repo=item.repo,
                    scopes=item.scopes,
                    parent_claim_id=item.parent_claim_id,
                )
                if blockers:
                    conflicts.append(
                        {
                            "claim_id": item.claim_id,
                            "task_id": item.task_id,
                            "owner": item.owner,
                            "blocked_by": [b.claim_id for b in blockers],
                        }
                    )
                    continue
                claims.append(item)
                known.add(item.claim_id)
                imported.append(item.claim_id)
                self._audit(
                    "CLAIM_IMPORTED",
                    item,
                    actor=actor,
                    at=now,
                    details={"source": "local_board", "status": item.status.value},
                )
            self._close_orphaned_children(claims, now)
        return ImportReport(
            tuple(imported), tuple(present), tuple(closed), tuple(conflicts), tuple(reclaim)
        )

    # -- transaction machinery --

    def _transact(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        for attempt in range(self._max_attempts):
            try:
                return fn(*args, **kwargs)
            except _CasLost:
                delay = min(1.0, 0.05 * (2**attempt)) * (0.5 + random.random())
                time.sleep(delay)
        raise CentralStoreUnavailable("merkezi pano meşgul: eşzamanlı yazma denemeleri tükendi")

    @contextmanager
    def _locked_state(self) -> Iterator[list[TaskClaim]]:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                base, state_text, events_text = self._fetch()
                claims = parse_state_text(state_text) if state_text is not None else []
                original = serialize_state(claims) if state_text is not None else None
                self._pending_events = []
                try:
                    yield claims
                except Exception:
                    self._pending_events = []
                    raise
                new_state = serialize_state(claims)
                if new_state == original and not self._pending_events:
                    self._last_base = base
                    self._write_mirror(new_state, events_text)
                    return
                new_events = events_text + "".join(
                    json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
                    for event in self._pending_events
                )
                commit = self._commit(new_state, new_events, base, self._pending_events)
                self._push(commit)
                self._pending_events = []
                self._last_base = commit
                self._write_mirror(new_state, new_events)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _flush_audit(self) -> None:  # events travel inside the board commit
        self._pending_events = []

    # -- git plumbing --

    def _git(self, *args: str, input_text: str | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        full_env = dict(os.environ)
        full_env["GIT_TERMINAL_PROMPT"] = "0"
        full_env["GIT_DIR"] = str(self._git_dir)
        if env:
            full_env.update(env)
        try:
            return subprocess.run(
                ["git", *args],
                input=input_text,
                capture_output=True,
                text=True,
                env=full_env,
                timeout=self._git_timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CentralStoreUnavailable(f"merkezi pano erişilemiyor: {_trim(str(exc))}") from exc

    def _ensure_repo(self) -> None:
        if (self._git_dir / "HEAD").exists():
            return
        self._git_dir.mkdir(parents=True, exist_ok=True)
        result = self._git("init", "--bare", "-q")
        if result.returncode != 0:
            raise CentralStoreUnavailable(f"pano önbelleği kurulamadı: {_trim(result.stderr)}")

    def _fetch(self) -> tuple[str | None, str | None, str]:
        self._ensure_repo()
        listing = self._git("ls-remote", "--", self.remote, self.ref)
        if listing.returncode != 0:
            raise CentralStoreUnavailable(f"merkezi pano okunamadı: {_trim(listing.stderr)}")
        if not listing.stdout.strip():
            return None, None, ""
        fetched = self._git(
            "fetch", "--no-tags", "-q", "--", self.remote, f"+{self.ref}:{self._tracking_ref}"
        )
        if fetched.returncode != 0:
            raise CentralStoreUnavailable(f"merkezi pano okunamadı: {_trim(fetched.stderr)}")
        base = self._git("rev-parse", "--verify", f"{self._tracking_ref}^{{commit}}")
        if base.returncode != 0:
            raise CentralStoreUnavailable("merkezi pano ref'i çözümlenemedi")
        sha = base.stdout.strip()
        state = self._git("cat-file", "blob", f"{sha}:{STATE_FILE}")
        if state.returncode != 0:
            raise ClaimStoreCorrupt("merkezi panoda claims.json yok")
        events = self._git("cat-file", "blob", f"{sha}:{EVENTS_FILE}")
        return sha, state.stdout, events.stdout if events.returncode == 0 else ""

    def _blob(self, text: str) -> str:
        result = self._git("hash-object", "-w", "--stdin", input_text=text)
        if result.returncode != 0:
            raise CentralStoreUnavailable("pano blob'u yazılamadı")
        return result.stdout.strip()

    def _commit(
        self,
        state_text: str,
        events_text: str,
        base: str | None,
        events: Sequence[dict[str, object]],
    ) -> str:
        entries = [
            ("README.md", self._blob(_BOARD_README)),
            (EVENTS_FILE, self._blob(events_text)),
            (STATE_FILE, self._blob(state_text)),
            ("vercel.json", self._blob(_BOARD_VERCEL_JSON)),
        ]
        tree_input = "".join(f"100644 blob {sha}\t{name}\n" for name, sha in sorted(entries))
        tree = self._git("mktree", input_text=tree_input)
        if tree.returncode != 0:
            raise CentralStoreUnavailable("pano ağacı yazılamadı")
        summary = "; ".join(
            f"{event.get('event')} {event.get('task_id')} by {event.get('actor')}" for event in events
        ) or "state refresh"
        message = f"lumos-board: {summary}"[:500] + "\n"
        args = ["commit-tree", tree.stdout.strip()]
        if base:
            args += ["-p", base]
        stamp = _format_time(self._now())
        commit = self._git(
            *args,
            input_text=message,
            env={
                "GIT_AUTHOR_NAME": _COMMITTER_NAME,
                "GIT_AUTHOR_EMAIL": _COMMITTER_EMAIL,
                "GIT_COMMITTER_NAME": _COMMITTER_NAME,
                "GIT_COMMITTER_EMAIL": _COMMITTER_EMAIL,
                "GIT_AUTHOR_DATE": stamp,
                "GIT_COMMITTER_DATE": stamp,
            },
        )
        if commit.returncode != 0:
            raise CentralStoreUnavailable("pano commit'i yazılamadı")
        return commit.stdout.strip()

    def _push(self, commit: str) -> None:
        # Plain push, never --force: the remote enforces "ref still at parent".
        result = self._git("push", "--porcelain", "--", self.remote, f"{commit}:{self.ref}")
        if result.returncode == 0:
            return
        combined = f"{result.stdout}\n{result.stderr}".lower()
        lost_markers = ("[rejected]", "non-fast-forward", "fetch first", "stale info", "cannot lock ref")
        if any(marker in combined for marker in lost_markers):
            raise _CasLost()
        raise CentralStoreUnavailable(f"merkezi panoya yazılamadı: {_trim(result.stderr or result.stdout)}")

    def _write_mirror(self, state_text: str, events_text: str) -> None:
        for name, text in ((STATE_FILE, state_text), (EVENTS_FILE, events_text)):
            fd, temporary = tempfile.mkstemp(prefix=f"{name}.", suffix=".tmp", dir=self.store_dir)
            path = Path(temporary)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(text)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(path, self.store_dir / name)
            finally:
                path.unlink(missing_ok=True)


__all__ = [
    "CLAIM_EVENT_SCHEMA",
    "DEFAULT_REF",
    "CentralClaimStore",
    "CentralStoreUnavailable",
    "ImportReport",
    "parse_state_text",
    "serialize_state",
]
