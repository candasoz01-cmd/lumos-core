"""
Kalıcı patch memory: tek SQLite dosyası (repo/.lumos/patch_memory.sqlite).

- Append-only: yalnızca INSERT; olaylar id ile sıralanır.
- Güncel durum: her (repo_root, rel_path) için son satır (max id).
- LRU sınırı: 50 aktif path; yeni path ile taşarsa en eski ts'li path invalidate edilir.
- Rollback uyumu: başarılı rollback sonrası ilgili path için invalidate satırı.

Runtime bayrakları (ör. _is_rollback) burada tutulmaz.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

_MAX_PATCH_MEMORY_PATHS = 50

_lock = threading.Lock()


def _db_path(repo_root: Path) -> Path:
    d = repo_root / ".lumos"
    d.mkdir(parents=True, exist_ok=True)
    return d / "patch_memory.sqlite"


def _connect(repo_root: Path) -> sqlite3.Connection:
    p = _db_path(repo_root)
    conn = sqlite3.connect(str(p), timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    _ensure_schema(conn)
    conn.commit()
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS patch_memory_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_root TEXT NOT NULL,
            rel_path TEXT NOT NULL,
            ts REAL NOT NULL,
            op TEXT NOT NULL CHECK (op IN ('record', 'invalidate')),
            prev_content BLOB
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pme_repo ON patch_memory_events(repo_root)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pme_repo_rel ON patch_memory_events(repo_root, rel_path)"
    )


def _normalize_repo_root(repo_root: Path | str | None) -> Path:
    if repo_root is not None:
        try:
            return Path(repo_root).resolve()
        except OSError:
            pass
    from task_engine.executors.patch_apply_executor import _repo_root

    return _repo_root()


def _row_to_entry(
    ts: float,
    prev_blob: bytes | None,
    rr: str,
) -> dict[str, Any]:
    prev: str | None
    if prev_blob is None:
        prev = None
    else:
        prev = prev_blob.decode("utf-8")
    return {
        "previous_content": prev,
        "timestamp": float(ts),
        "repo_root": rr,
    }


def get_entry(
    repo_relative_path: str,
    *,
    repo_root: Path | str | None = None,
) -> dict[str, Any] | None:
    """Son geçerli kayıt (invalidate sonrası None)."""
    rr = _normalize_repo_root(repo_root)
    rr_s = str(rr)
    rel = repo_relative_path.replace("\\", "/")
    with _lock:
        conn = _connect(rr)
        try:
            row = conn.execute(
                """
                SELECT op, ts, prev_content, repo_root FROM patch_memory_events
                WHERE repo_root = ? AND rel_path = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (rr_s, rel),
            ).fetchone()
            if row is None or row[0] != "record":
                return None
            stored_rr = str(row[3]) if row[3] is not None else rr_s
            return _row_to_entry(float(row[1]), row[2], stored_rr)
        finally:
            conn.close()


def has_active_paths(repo_root: Path | str | None = None) -> bool:
    rr = _normalize_repo_root(repo_root)
    rr_s = str(rr)
    with _lock:
        conn = _connect(rr)
        try:
            n = conn.execute(
                """
                SELECT COUNT(*) FROM patch_memory_events e
                WHERE e.id IN (
                    SELECT MAX(id) FROM patch_memory_events WHERE repo_root = ? GROUP BY rel_path
                )
                AND e.repo_root = ? AND e.op = 'record'
                """,
                (rr_s, rr_s),
            ).fetchone()
            return int(n[0] or 0) > 0
        finally:
            conn.close()


def get_last_record_for_rollback(
    repo_root: Path | str | None = None,
) -> tuple[str | None, dict[str, Any] | None]:
    """
    ROLLBACK_LAST / ROLLBACK_PREVIEW: en son kaydedilen patch (max ts) path + entry.
    """
    rr = _normalize_repo_root(repo_root)
    rr_s = str(rr)
    with _lock:
        conn = _connect(rr)
        try:
            row = conn.execute(
                """
                SELECT e.rel_path, e.ts, e.prev_content FROM patch_memory_events e
                WHERE e.id IN (
                    SELECT MAX(id) FROM patch_memory_events WHERE repo_root = ? GROUP BY rel_path
                )
                AND e.repo_root = ? AND e.op = 'record'
                ORDER BY e.ts DESC
                LIMIT 1
                """,
                (rr_s, rr_s),
            ).fetchone()
            if row is None:
                return None, None
            rel = str(row[0])
            entry = _row_to_entry(float(row[1]), row[2], rr_s)
            return rel, entry
        finally:
            conn.close()


def _append_invalidate(conn: sqlite3.Connection, rr_s: str, rel: str, ts: float) -> None:
    conn.execute(
        """
        INSERT INTO patch_memory_events (repo_root, rel_path, ts, op, prev_content)
        VALUES (?, ?, ?, 'invalidate', NULL)
        """,
        (rr_s, rel.replace("\\", "/"), ts),
    )


def _active_path_count(conn: sqlite3.Connection, rr_s: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) FROM patch_memory_events e
        WHERE e.id IN (
            SELECT MAX(id) FROM patch_memory_events WHERE repo_root = ? GROUP BY rel_path
        )
        AND e.repo_root = ? AND e.op = 'record'
        """,
        (rr_s, rr_s),
    ).fetchone()
    return int(row[0] or 0)


def _lru_path(conn: sqlite3.Connection, rr_s: str) -> str | None:
    row = conn.execute(
        """
        SELECT e.rel_path FROM patch_memory_events e
        WHERE e.id IN (
            SELECT MAX(id) FROM patch_memory_events WHERE repo_root = ? GROUP BY rel_path
        )
        AND e.repo_root = ? AND e.op = 'record'
        ORDER BY e.ts ASC
        LIMIT 1
        """,
        (rr_s, rr_s),
    ).fetchone()
    return None if row is None else str(row[0])


def record_patch_memory(
    rel: str,
    previous_content: str | None,
    *,
    repo_root: Path | str | None = None,
) -> None:
    """Yeni record satırı; 50 aktif path aşımında LRU invalidate."""
    rr = _normalize_repo_root(repo_root)
    rr_s = str(rr)
    rel_n = rel.replace("\\", "/")
    ts = time.time()
    blob: bytes | None
    if previous_content is None:
        blob = None
    else:
        blob = previous_content.encode("utf-8")

    with _lock:
        conn = _connect(rr)
        try:
            conn.execute(
                """
                INSERT INTO patch_memory_events (repo_root, rel_path, ts, op, prev_content)
                VALUES (?, ?, ?, 'record', ?)
                """,
                (rr_s, rel_n, ts, blob),
            )
            if _active_path_count(conn, rr_s) > _MAX_PATCH_MEMORY_PATHS:
                victim = _lru_path(conn, rr_s)
                if victim is not None:
                    _append_invalidate(conn, rr_s, victim, time.time())
            conn.commit()
        finally:
            conn.close()


def invalidate_path(rel: str, *, repo_root: Path | str | None = None) -> None:
    """Rollback sonrası veya önceki içerik yok senaryosu: path bellekten düşer."""
    rr = _normalize_repo_root(repo_root)
    rr_s = str(rr)
    rel_n = rel.replace("\\", "/")
    with _lock:
        conn = _connect(rr)
        try:
            _append_invalidate(conn, rr_s, rel_n, time.time())
            conn.commit()
        finally:
            conn.close()


def clear_for_repo(repo_root: Path | str | None = None) -> None:
    """Test / sıfırlama: bu repo için tüm olayları siler (append-only dışı bakım)."""
    rr = _normalize_repo_root(repo_root)
    rr_s = str(rr)
    with _lock:
        conn = _connect(rr)
        try:
            conn.execute("DELETE FROM patch_memory_events WHERE repo_root = ?", (rr_s,))
            conn.commit()
        finally:
            conn.close()
