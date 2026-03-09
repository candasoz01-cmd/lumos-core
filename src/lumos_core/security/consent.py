"""User consent gate. No persistence until consent is granted."""

from __future__ import annotations

import json
from pathlib import Path

_CONSENT_FILENAME = "consent.json"


def _lumos_dir() -> Path:
    """Same base_dir logic as __main__ and interactive_cli: src/.lumos or .lumos."""
    p = Path("src/.lumos")
    if p.exists():
        return p
    return Path(".lumos")


def _consent_path(base_dir: Path | None = None) -> Path:
    base = base_dir if base_dir is not None else _lumos_dir()
    return Path(base) / _CONSENT_FILENAME


def has_user_consent(base_dir: Path | None = None) -> bool:
    """Return True only if user has granted persistence consent.
    Reads from base_dir/consent.json (default: _lumos_dir()).
    """
    path = _consent_path(base_dir)
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return bool(data.get("granted"))
    except Exception:
        return False


def save_consent(base_dir: Path | None = None) -> None:
    """Write consent to base_dir/consent.json. Creates directory if needed."""
    base = base_dir if base_dir is not None else _lumos_dir()
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    path = base / _CONSENT_FILENAME
    path.write_text(json.dumps({"granted": True}, ensure_ascii=False), encoding="utf-8")


def ask_and_persist_consent_if_needed(base_dir: Path | None = None) -> None:
    """If consent not granted, prompt once. On 'e' (evet) write consent and return.
    On EOF (non-interactive) do nothing. Idempotent: if already consented, no prompt.
    """
    if has_user_consent(base_dir):
        return
    prompt = "Verileri kaydetmemi ister misin? (e/h): "
    try:
        reply = input(prompt).strip().lower()
    except EOFError:
        return
    if reply in ("e", "evet", "y", "yes", "ok", "tamam"):
        save_consent(base_dir)
