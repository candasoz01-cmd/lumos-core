from dataclasses import dataclass, field
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

    def add(self, note: MemoryNote) -> None:
        if not self._is_unlocked:
            return
        if not self.enabled:
            return
        if note.created_at is None:
            note.created_at = time.time()
        self.notes.append(note)
        self._save_to_store()

