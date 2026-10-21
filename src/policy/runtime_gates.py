"""Staging runtime forces the human gates on.

Local and internal runs stay opt-in so the demo default does not change.
Staging is explicit: ``LUMOS_RUNTIME_ENV=staging`` (or ``stage``), or
Vercel's preview environment (``VERCEL_ENV=preview``). In that runtime the
confirmation layer and the task-execution grant cannot be switched off.
"""
from __future__ import annotations

import os

_STAGING_RUNTIME = frozenset({"staging", "stage"})


def is_staging_runtime() -> bool:
    runtime = (os.environ.get("LUMOS_RUNTIME_ENV") or "").strip().lower()
    vercel = (os.environ.get("VERCEL_ENV") or "").strip().lower()
    return runtime in _STAGING_RUNTIME or vercel == "preview"
