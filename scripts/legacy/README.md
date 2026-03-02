# Legacy scripts (deprecated)

These scripts were used for one-off patches during presence lifecycle refactors.
They are **deprecated**; the logic is now in the main codebase (`src/security/presence_lock.py`, `src/main.py`).

- `patch_presence_stopped_clean.py` – ensured `presence_stopped` only when not silent and was_running (now in presence_lock.py)
- `patch_eof_and_silent_stop.py` – EOF handling and silent stop (now in main.py / presence_lock.py)
- `patch_presence_lifecycle.py` – lifecycle logging (now in presence_lock.py)

Do not run these; use `make check` and `scripts/smoke_presence.sh` for validation.
