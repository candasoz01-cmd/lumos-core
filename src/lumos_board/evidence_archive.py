"""Wall evidence archive: the authorized writer stores, the observer only reads back.

A manifest field that says the copy was saved is not verification. The observer
re-reads source and archive bytes and compares scope, size, SHA-256, and the
task / report / commit / run-attempt binding. It does not write.

GitHub retention is never assumed to be 80 or 90 days. Known workflow
retention and an object's own expires_at are combined; unknown policy stays
UNKNOWN. This module does not delete the archive and does not block GitHub's
own cleanup.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

from lumos_board.evidence_policy import EvidencePolicy, deletion_blockers
from lumos_board.founder_approval import FounderApprovalStore

SCHEMA = "lumos.wall.evidence_archive.v1"
DEFAULT_REMOTE = "https://github.com/candasoz01-cmd/lumos-wall-evidence.git"
DELETION_GATE = "evidence_archive"
DELETION_ACTION = "delete_source"
DEFAULT_RETRY_MARGIN = timedelta(hours=24)
DEFAULT_CHECKPOINT_INTERVAL = timedelta(minutes=15)
ENV_DIR = "LUMOS_WALL_EVIDENCE_DIR"
ENV_REMOTE = "LUMOS_WALL_EVIDENCE_REMOTE"
ENV_INTERVAL = "LUMOS_EVIDENCE_CHECKPOINT_SECONDS"

_SECRET_CONTENT = re.compile(
    r"(-----BEGIN [^-]*PRIVATE KEY-----"
    r"|\b(?:api[_ -]?key|token|secret|password)\s*[:=]\s*\S+"
    r"|\bBearer\s+[A-Za-z0-9._~+/=-]+)",
    re.IGNORECASE,
)
_SECRET_NAMES = {"id_rsa", "id_ed25519", "credentials.json", "secrets.json"}
_REPORT_ID = re.compile(r"[^A-Za-z0-9._-]+")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Timezone-aware timestamp required")
    return value.astimezone(timezone.utc)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_GRAFT_FILE"] = os.devnull
    return env


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "--no-replace-objects", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
        env=_git_env(),
    )


def head_commit(repo: Path) -> str:
    try:
        return _git(repo, "rev-parse", "HEAD").stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def secret_path(relative: str) -> bool:
    name = PurePosixPath(relative).name.lower()
    if name.startswith(".env") or name.endswith((".pem", ".key", ".p12", ".pfx")):
        return True
    return name in _SECRET_NAMES


def secret_bytes(data: bytes) -> bool:
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        return False
    return _SECRET_CONTENT.search(text) is not None


def safe_report_id(value: str) -> str:
    cleaned = _REPORT_ID.sub("-", str(value or "").strip()).strip(".-")
    if not cleaned:
        raise ValueError("report_id required")
    return cleaned[:120]


def workflow_retention_days(workflow_path: Path) -> int | None:
    """Smallest retention-days declared in a workflow. Absence is unknown, not 90."""
    try:
        text = Path(workflow_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    found = [int(match) for match in re.findall(r"retention-days:\s*(\d+)", text)]
    return min(found) if found else None


def transfer_window(
    *,
    now: datetime,
    policy_days: int | None,
    object_expires_at: datetime | None,
    retry_margin: timedelta = DEFAULT_RETRY_MARGIN,
) -> dict[str, object]:
    """Earliest deletion minus retry margin. Never invents an 80/90-day policy."""
    now = _utc(now)
    if retry_margin < timedelta(0):
        raise ValueError("retry_margin must be non-negative")
    deadlines: list[tuple[str, datetime]] = []
    if policy_days is not None:
        if policy_days < 0:
            raise ValueError("policy_days must be non-negative")
        deadlines.append(("policy", now + timedelta(days=policy_days)))
    if object_expires_at is not None:
        deadlines.append(("expires_at", _utc(object_expires_at)))
    if not deadlines:
        return {
            "status": "RETENTION_UNKNOWN",
            "deadline": None,
            "complete_by": None,
            "source": None,
            "fixed_80_90_assumed": False,
        }
    source, deadline = min(deadlines, key=lambda item: item[1])
    complete_by = deadline - retry_margin
    status = "IN_WINDOW" if now <= complete_by else "RETENTION_TOO_SHORT"
    return {
        "status": status,
        "deadline": deadline.isoformat(),
        "complete_by": complete_by.isoformat(),
        "source": source,
        "fixed_80_90_assumed": False,
    }


def _worktree_paths(repo: Path) -> list[str]:
    try:
        out = _git(repo, "status", "--porcelain", "-z", "--untracked-files=all").stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    paths: list[str] = []
    fields = out.split("\0")
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if len(entry) < 4:
            continue
        status, relative = entry[:2], entry[3:]
        if "R" in status or "C" in status:
            # Rename/copy: the next NUL field is the origin path and has no status prefix.
            origin = fields[index] if index < len(fields) else ""
            index += 1
            if "R" in status and origin:
                paths.append(origin)  # renamed away: the old name is now a deletion
        if relative and not relative.endswith("/"):
            paths.append(relative)
    return paths


def _scope(repo: Path, extra: list[str] | None) -> list[str]:
    seen: list[str] = []
    for relative in [*_worktree_paths(repo), *(extra or [])]:
        relative = relative.replace("\\", "/").lstrip("/")
        if not relative or relative.startswith(".git/") or relative in seen:
            continue
        seen.append(relative)
    return seen


def _tracked_in_head(repo: Path, relative: str) -> bool:
    return _git(repo, "cat-file", "-e", f"HEAD:{relative}", check=False).returncode == 0


def _deleted_in_head(repo: Path, relative: str) -> bool:
    """Prove a file deletion against this commit's first parent, not arbitrary history."""
    commit = head_commit(repo)
    current = _git(
        repo, "--literal-pathspecs", "ls-tree", "-z", commit, "--", relative, check=False,
    )
    # An unreadable tree is not evidence that a path is absent.
    if current.returncode != 0 or current.stdout:
        return False
    previous = _git(repo, "cat-file", "-t", f"{commit}^:{relative}", check=False)
    # Missing parent/history and paths that were directories are not file evidence.
    return previous.returncode == 0 and previous.stdout.strip() == "blob"


def _read_file(repo: Path, relative: str) -> tuple[str, bytes | None]:
    root = Path(repo).resolve()
    if PurePosixPath(relative).is_absolute():
        return "outside_repo", None
    # Look for links BEFORE resolving: resolve() follows them, so the check would never fire.
    current = root
    for part in PurePosixPath(relative).parts:
        if part == "..":
            return "outside_repo", None
        current = current / part
        if current.is_symlink():
            return "symlink", None
    path = current.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return "outside_repo", None
    if not path.is_file():
        # Accept worktree deletions and file deletions proved by the delivery commit.
        if not path.exists() and (
            _tracked_in_head(root, relative) or _deleted_in_head(root, relative)
        ):
            return "deleted", None
        return "missing", None
    try:
        return "ok", path.read_bytes()
    except OSError:
        return "unreadable", None


def archive_dir_for(archive: Path, report_id: str) -> Path:
    """`archive_report` writes <archive>/<report_id>/manifest.json. Accept the root or that directory."""
    archive = Path(archive)
    nested = archive / safe_report_id(report_id)
    if (nested / "manifest.json").is_file():
        return nested
    if (archive / "manifest.json").is_file():
        return archive
    return nested


def _record(path: Path, payload: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def archive_report(
    repo: Path,
    archive_root: Path,
    *,
    task_id: str,
    report_id: str,
    report_kind: str,
    run_attempt: str,
    report: dict | None = None,
    extra_paths: list[str] | None = None,
    now: datetime | None = None,
    policy_days: int | None = None,
    object_expires_at: datetime | None = None,
    retry_margin: timedelta = DEFAULT_RETRY_MARGIN,
) -> dict[str, object]:
    """Writer. Copies non-secret worktree bytes. Does not mark them verified."""
    if report_kind not in {"interim", "delivery"}:
        raise ValueError("report_kind must be interim or delivery")
    repo = Path(repo).resolve()
    archive_root = Path(archive_root).resolve()
    now = _utc(now or utc_now())
    report_key = safe_report_id(report_id)
    window = transfer_window(
        now=now,
        policy_days=policy_days,
        object_expires_at=object_expires_at,
        retry_margin=retry_margin,
    )
    destination = archive_root / report_key
    if destination.exists():
        raise FileExistsError("archive report already exists; corrections are new events")
    files: list[dict[str, object]] = []
    excluded: list[dict[str, str]] = []
    payloads = destination / "payload"
    for relative in _scope(repo, extra_paths):
        reason, data = _read_file(repo, relative)
        if reason != "ok" or data is None:
            excluded.append({"path": relative, "reason": reason})
            continue
        if secret_path(relative) or secret_bytes(data):
            excluded.append({"path": relative, "reason": "secret"})
            continue
        digest = sha256_bytes(data)
        _write_bytes(payloads / digest, data)
        files.append({"path": relative, "size": len(data), "sha256": digest})
    commit = head_commit(repo)
    manifest = {
        "schema": SCHEMA,
        "task_id": str(task_id or "UNKNOWN"),
        "report_id": report_key,
        "report_kind": report_kind,
        "commit": commit,
        "run_attempt": str(run_attempt or "UNKNOWN"),
        "recorded_at": now.isoformat(),
        "declared_saved": True,
        "files": files,
        "excluded": excluded,
        "retention": EvidencePolicy().record_terms(now, kind="audit", severity="unknown"),
        "github_retention": window,
        "fixed_80_90_assumed": False,
    }
    if report is not None:
        _record(destination / "report.json", _redacted_report(report))
    _record(destination / "manifest.json", manifest)
    if window["status"] == "RETENTION_TOO_SHORT":
        return _stopped(destination, "RETENTION_TOO_SHORT", manifest)
    verdict = observe_archive(
        repo,
        destination,
        expect={
            "task_id": manifest["task_id"],
            "report_id": report_key,
            "commit": commit,
            "run_attempt": manifest["run_attempt"],
        },
    )
    _touch_checkpoint(archive_root, now)
    return verdict


def _redacted_report(report: dict) -> dict:
    def walk(value):
        if isinstance(value, str):
            return _SECRET_CONTENT.sub("[redacted]", value)
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {str(key): walk(item) for key, item in value.items()}
        return value

    redacted = walk(report)
    return redacted if isinstance(redacted, dict) else {"value": redacted}


def _touch_checkpoint(archive_root: Path, now: datetime) -> None:
    stamp = archive_root / "last_checkpoint_at"
    stamp.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp.write_text(now.isoformat() + "\n", encoding="utf-8")


def checkpoint_due(
    archive_root: Path,
    *,
    now: datetime | None = None,
    interval: timedelta = DEFAULT_CHECKPOINT_INTERVAL,
) -> bool:
    now = _utc(now or utc_now())
    stamp = Path(archive_root) / "last_checkpoint_at"
    try:
        last = _utc(datetime.fromisoformat(stamp.read_text(encoding="utf-8").strip()))
    except (OSError, UnicodeError, ValueError):
        return True
    return now - last >= interval


def observe_archive(repo: Path, archive_dir: Path, *, expect: dict[str, str]) -> dict[str, object]:
    """Read-only. Compares source bytes with archive bytes. Writes nothing."""
    repo = Path(repo).resolve()
    archive_dir = Path(archive_dir).resolve()
    before = _snapshot(archive_dir)
    try:
        verdict = _observe(repo, archive_dir, expect)
    finally:
        if _snapshot(archive_dir) != before:
            raise RuntimeError("observer wrote to the archive")
    return verdict


def _snapshot(root: Path) -> tuple:
    if not root.exists():
        return ()
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            rows.append((str(path.relative_to(root)), path.stat().st_size, sha256_bytes(path.read_bytes())))
    return tuple(rows)


def _observe(repo: Path, archive_dir: Path, expect: dict[str, str]) -> dict[str, object]:
    manifest_path = archive_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _stopped(archive_dir, "ARCHIVE_MISSING", {})
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        return _stopped(archive_dir, "ARCHIVE_CORRUPT", manifest if isinstance(manifest, dict) else {})
    if manifest.get("report_id") != expect.get("report_id"):
        return _stopped(archive_dir, "WRONG_REPORT", manifest)
    for key in ("task_id", "commit", "run_attempt"):
        if str(manifest.get(key)) != str(expect.get(key)):
            return _stopped(archive_dir, "RELATION_MISMATCH", manifest)
    if manifest.get("commit") != "UNKNOWN" and head_commit(repo) != manifest.get("commit"):
        return _stopped(archive_dir, "SOURCE_CHANGED", manifest)
    files = manifest.get("files")
    excluded = manifest.get("excluded") or []
    if not isinstance(files, list) or not isinstance(excluded, list):
        return _stopped(archive_dir, "ARCHIVE_CORRUPT", manifest)
    for item in excluded:
        reason = item.get("reason") if isinstance(item, dict) else None
        if reason == "secret":
            continue
        if reason in {"symlink", "deleted"}:
            # The observer checks the exclusion itself instead of trusting the manifest.
            if _read_file(repo, str(item.get("path") or ""))[0] != reason:
                return _stopped(archive_dir, "SOURCE_CHANGED", manifest)
            continue
        return _stopped(archive_dir, "SCOPE_INCOMPLETE", manifest)
    checked: list[dict[str, object]] = []
    for entry in files:
        if not isinstance(entry, dict):
            return _stopped(archive_dir, "ARCHIVE_CORRUPT", manifest)
        relative = str(entry.get("path") or "")
        expected_hash = str(entry.get("sha256") or "")
        expected_size = entry.get("size")
        reason, data = _read_file(repo, relative)
        if reason == "missing" or data is None:
            return _stopped(archive_dir, "SOURCE_MISSING", manifest)
        actual = sha256_bytes(data)
        if actual != expected_hash or len(data) != expected_size:
            return _stopped(archive_dir, "SOURCE_CHANGED", manifest)
        payload = archive_dir / "payload" / expected_hash
        try:
            archived = payload.read_bytes()
        except OSError:
            return _stopped(archive_dir, "ARCHIVE_MISSING", manifest)
        if sha256_bytes(archived) != expected_hash or len(archived) != expected_size or archived != data:
            return _stopped(archive_dir, "ARCHIVE_CORRUPT", manifest)
        checked.append({"path": relative, "size": len(data), "sha256": actual})
    return {
        "schema": SCHEMA,
        "status": "VERIFIED",
        "verified": True,
        "scope_complete": True,
        "declared_saved_ignored": True,
        "archive": str(archive_dir),
        "task_id": manifest.get("task_id"),
        "report_id": manifest.get("report_id"),
        "commit": manifest.get("commit"),
        "run_attempt": manifest.get("run_attempt"),
        "files": checked,
        "excluded": list(manifest.get("excluded") or []),
        "github_retention": manifest.get("github_retention"),
    }


def _stopped(archive_dir: Path, status: str, manifest: dict) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "status": status,
        "verified": False,
        "scope_complete": False,
        "declared_saved_ignored": True,
        "archive": str(archive_dir),
        "task_id": manifest.get("task_id"),
        "report_id": manifest.get("report_id"),
        "commit": manifest.get("commit"),
        "run_attempt": manifest.get("run_attempt"),
        "files": [],
        "excluded": list(manifest.get("excluded") or []),
        "github_retention": manifest.get("github_retention"),
    }


def probe_remote(remote: str) -> dict[str, object]:
    """Read-only reachability. Does not create the remote or push."""
    shown = _redact_remote(remote)
    try:
        subprocess.run(
            ["git", "ls-remote", remote],
            check=True,
            capture_output=True,
            text=True,
            env=_git_env(),
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"")
        if isinstance(detail, bytes):
            detail = detail.decode(errors="replace")
        status = "REMOTE_FORBIDDEN" if "Authentication" in str(detail) or "403" in str(detail) else "REMOTE_UNREACHABLE"
        return {"reachable": False, "verified": False, "status": status, "remote": shown}
    return {"reachable": True, "verified": False, "status": "REACHABLE_NOT_VERIFIED", "remote": shown}


def _redact_remote(remote: str) -> str:
    if "@" in remote and "://" in remote:
        scheme, rest = remote.split("://", 1)
        return scheme + "://[redacted]@" + rest.split("@", 1)[1]
    return remote


def publish_and_read_back(
    repo: Path,
    package: Path,
    remote: str,
    readback: Path,
    *,
    report_id: str,
    expect: dict[str, str],
) -> dict[str, object]:
    """Writer pushes one new commit, then a separate clone is read by the observer."""
    probe = probe_remote(remote)
    if not probe["reachable"]:
        return probe
    report_key = safe_report_id(report_id)
    work = Path(readback).parent / (report_key + "-writer")
    if work.exists() or Path(readback).exists():
        raise FileExistsError("readback paths must be new")
    try:
        subprocess.run(
            ["git", "clone", remote, str(work)],
            check=True,
            capture_output=True,
            text=True,
            env=_git_env(),
        )
    except subprocess.CalledProcessError:
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(mode=0o700, parents=True)
        _git(work, "init", "-b", "evidence")
        _git(work, "remote", "add", "origin", remote)
    event = work / "events" / report_key
    if event.exists():
        return {"reachable": True, "verified": False, "status": "REMOTE_EVENT_EXISTS", "remote": probe["remote"]}
    shutil.copytree(package, event)
    _git(work, "add", "--", f"events/{report_key}")
    _git(
        work,
        "-c",
        "user.name=lumos-evidence",
        "-c",
        "user.email=evidence@lumos.invalid",
        "commit",
        "-m",
        f"evidence {report_key}",
    )
    pushed = _git(work, "push", "origin", "HEAD:refs/heads/evidence", check=False)
    if pushed.returncode != 0:
        return {
            "reachable": True,
            "verified": False,
            "status": "REMOTE_WRITE_FAILED",
            "remote": probe["remote"],
            "detail": (pushed.stderr or pushed.stdout)[:300],
        }
    subprocess.run(
        ["git", "clone", "--branch", "evidence", remote, str(readback)],
        check=True,
        capture_output=True,
        text=True,
        env=_git_env(),
    )
    return observe_archive(repo, Path(readback) / "events" / report_key, expect=expect)


def inventory(archive_root: Path, *, now: datetime | None = None, horizon: timedelta = timedelta(days=7)) -> dict:
    """Separate held, near-expiry, and lost records. Lost evidence is not recovered."""
    now = _utc(now or utc_now())
    held: list[str] = []
    near: list[str] = []
    lost: list[str] = []
    root = Path(archive_root)
    if root.is_dir():
        for manifest_path in sorted(root.rglob("manifest.json")):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                lost.append(str(manifest_path.parent.name))
                continue
            report_id = str(manifest.get("report_id") or manifest_path.parent.name)
            missing = False
            for entry in manifest.get("files") or []:
                digest = str(entry.get("sha256") or "")
                payload = manifest_path.parent / "payload" / digest
                try:
                    data = payload.read_bytes()
                except OSError:
                    missing = True
                    break
                if sha256_bytes(data) != digest or len(data) != entry.get("size"):
                    missing = True
                    break
            if missing:
                lost.append(report_id)
                continue
            expires = _expires(manifest)
            if expires is not None and expires - now <= horizon:
                near.append(report_id)
            else:
                held.append(report_id)
    return {"held": held, "near_expiry": near, "lost": lost, "recovered_from_lost": []}


def _expires(manifest: dict) -> datetime | None:
    window = manifest.get("github_retention") or {}
    raw = window.get("deadline")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return _utc(datetime.fromisoformat(raw))
    except ValueError:
        return None


def source_deletion_decision(
    store: FounderApprovalStore,
    *,
    task: str,
    head_sha: str,
    verification: dict,
    terms: dict | None,
    at: datetime,
    archive_dir: Path,
) -> dict[str, object]:
    """Existing founder gate plus retention blockers. Does not delete."""
    reasons: list[str] = []
    if verification.get("status") != "VERIFIED" or verification.get("verified") is not True:
        reasons.append("ARCHIVE_NOT_VERIFIED")
    if verification.get("scope_complete") is not True:
        reasons.append("SCOPE_INCOMPLETE")
    if not _archive_still_matches(archive_dir, verification):
        reasons.append("ARCHIVE_COPY_MISSING")
    approval = store.check(task=task, gate=DELETION_GATE, action=DELETION_ACTION, head_sha=head_sha)
    if terms is None:
        reasons.append("INVALID_RETENTION_RECORD")
    else:
        reasons.extend(
            deletion_blockers(
                terms,
                at=at,
                exact_scope_approval_verified=approval is not None,
                investigation_open=False,
            )
        )
    return {"allowed": not reasons, "reasons": reasons, "archive_retained": True}


def execute_source_deletion(
    repo: Path,
    paths: list[str],
    decision: dict,
    *,
    archive_dir: Path,
    verification: dict,
) -> dict[str, object]:
    """Authorized executor only. Refuses unless decision.allowed. Never deletes the archive."""
    if decision.get("allowed") is not True or decision.get("archive_retained") is not True:
        raise PermissionError("source deletion refused: " + ",".join(decision.get("reasons") or ["NOT_ALLOWED"]))
    allowed = {
        str(entry.get("path")): str(entry.get("sha256"))
        for entry in verification.get("files") or []
        if isinstance(entry, dict)
    }
    before = _snapshot(Path(archive_dir))
    removed: list[str] = []
    root = Path(repo).resolve()
    for relative in paths:
        reason, data = _read_file(root, relative)
        if reason != "ok" or data is None or allowed.get(relative) != sha256_bytes(data):
            raise PermissionError("refusing to delete a path outside the verified file scope")
        (root / relative).unlink()
        removed.append(relative)
    if _snapshot(Path(archive_dir)) != before:
        raise RuntimeError("archive copy changed during source deletion")
    return {"deleted_source": removed, "archive_retained": True}


def _archive_still_matches(archive_dir: Path, verification: dict) -> bool:
    for entry in verification.get("files") or []:
        payload = Path(archive_dir) / "payload" / str(entry.get("sha256"))
        try:
            data = payload.read_bytes()
        except OSError:
            return False
        if sha256_bytes(data) != entry.get("sha256") or len(data) != entry.get("size"):
            return False
    return verification.get("status") == "VERIFIED"


def archive_required() -> bool:
    return bool(os.environ.get(ENV_DIR) or os.environ.get(ENV_REMOTE))


def bind_report(report: dict, *, repo: Path, job_id: str, kind: str = "delivery") -> dict:
    """Attach archive verification to a report. Unconfigured archives do not count as verified."""
    report = dict(report)
    destination = os.environ.get(ENV_DIR, "").strip()
    if not destination:
        report["evidence"] = {
            "schema": SCHEMA,
            "verified": False,
            "required": False,
            "status": "ARCHIVE_NOT_CONFIGURED",
        }
        return report
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT") or "local"
    try:
        verdict = archive_report(
            repo,
            Path(destination),
            task_id=str(report.get("task") or job_id),
            report_id=f"{job_id}-{kind}",
            report_kind=kind,
            run_attempt=attempt,
            report=report,
            extra_paths=list(report.get("changed_files") or []),
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        verdict = {"schema": SCHEMA, "verified": False, "status": "EVIDENCE_BIND_FAILED", "detail": str(exc)[:200]}
    verdict["required"] = True
    report["evidence"] = verdict
    if not verdict.get("verified"):
        if report.get("status") == "ok":
            report["status"] = "partial"
        errors = list(report.get("errors") or [])
        errors.append("evidence_unverified")
        report["errors"] = errors
    return report


def checkpoint_phase(*, repo: Path, job_id: str, phase: str) -> dict | None:
    """Periodic interim copy between reports. No-op until an archive directory is configured."""
    if not archive_required():
        return None
    destination = os.environ.get(ENV_DIR, "").strip()
    if not destination:
        return {"verified": False, "required": True, "status": "REMOTE_ONLY_NOT_A_LOCAL_CHECKPOINT"}
    raw = os.environ.get(ENV_INTERVAL, "").strip()
    interval = DEFAULT_CHECKPOINT_INTERVAL
    if raw:
        interval = timedelta(seconds=max(0, int(raw)))
    root = Path(destination)
    if not checkpoint_due(root, interval=interval):
        return {"status": "NOT_DUE", "verified": False, "required": True}
    return archive_report(
        repo,
        root,
        task_id=job_id,
        report_id=f"{job_id}-{phase}",
        report_kind="interim",
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT") or "local",
    )
