from dataclasses import dataclass, field
import os
import time
from typing import List, Optional

from context.context import Context
from memory.schema import MemoryNote
from memory.secure_store import SecureNotesStore
# manages memory state


@dataclass
class Memory:
    enabled: bool = True
    notes: List[MemoryNote] = field(default_factory=list)
    store: Optional[SecureNotesStore] = None
    root_key: Optional[bytes] = None
    _is_unlocked: bool = field(default=False, repr=False)

    def attach_store(self, store: SecureNotesStore, root_key: bytes) -> None:
        self.store = store
        self.root_key = root_key
        self._is_unlocked = True
        self._load_from_store()

    def _load_from_store(self) -> None:
        if not self.store or not self.root_key:
            return
        try:
            raw = self.store.load(self.root_key)
        except Exception:
            return
        loaded: List[MemoryNote] = []
        for d in raw:
            try:
                loaded.append(MemoryNote(**d))
            except Exception:
                continue
        self.notes = loaded

    def _save_to_store(self) -> None:
        if not self.store or not self.root_key:
            return
        try:
            self.store.save(self.root_key, self.notes)
        except Exception:
            pass

    def device_lock(self) -> None:
        self.root_key = None
        self._is_unlocked = False

    def cleanup(self) -> None:
        now = time.time()
        kept: List[MemoryNote] = []
        changed = False
        for n in self.notes:
            if n.ttl_seconds is None:
                kept.append(n)
                continue
            if n.created_at is None:
                n.created_at = now
                kept.append(n)
                changed = True
                continue
            if (now - n.created_at) <= n.ttl_seconds:
                kept.append(n)
        if len(kept) != len(self.notes):
            changed = True
        self.notes = kept
        if changed:
            self._save_to_store()

    def enrich(self, ctx: Context) -> Context:
        self.cleanup()
        ctx.memory_note_count = len(self.notes)
        return ctx

    def delete_all(self) -> int:
        """Clear local notes; verify an attached store before returning a count.

        Locked returns zero without writing. Without a store, only RAM is cleared.
        Store errors propagate; failed verification raises RuntimeError. On failure
        RAM is retained, but disk may have changed: no retry or rollback is attempted.
        Read-back confirms the current store contents, not crash durability or erasure
        of backups. The count is the number of local notes cleared by this call.
        """
        if not self._is_unlocked:
            return 0
        removed = len(self.notes)
        if self.store is not None:
            if not self.root_key:
                raise RuntimeError("Memory deletion requires the store key")
            self.store.save(self.root_key, [])
            if self.store.load(self.root_key, strict=True) != []:
                raise RuntimeError("Memory deletion could not be verified")
        self.notes = []
        return removed

    def add(self, note: MemoryNote) -> None:
        if not self._is_unlocked:
            return
        if not self.enabled:
            return
        if note.created_at is None:
            note.created_at = time.time()
        if note.ttl_seconds is None:
            note.ttl_seconds = _default_ttl_seconds()
        self.notes.append(note)
        self._save_to_store()


def _default_ttl_seconds() -> Optional[int]:
    raw = (os.environ.get("LUMOS_MEMORY_TTL_SECONDS") or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None
