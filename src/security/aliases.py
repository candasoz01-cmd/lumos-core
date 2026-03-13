import json
from pathlib import Path

from core.workspace_contract import CoreWriteForbidden, save_aliases_json

def _alias_path(base_dir: str) -> Path:
    return Path(base_dir) / "aliases.json"


def load_aliases(base_dir: str) -> dict[str, str]:
    try:
        p = _alias_path(base_dir)
        if not p.exists():
            return {}
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return {str(k).strip(): str(v).strip() for k, v in data.items()}
    except Exception:
        return {}


def save_aliases(
    base_dir: str,
    aliases: dict[str, str],
    *,
    is_sandbox_mode: bool = False,
) -> None:
    try:
        # aliases.json yazımı merkezi sink üzerinden yapılır.
        # is_sandbox_mode main'deki tek kaynaktan iletilir; varsayılan False davranışı korunur.
        save_aliases_json(base_dir, aliases, is_sandbox_mode=is_sandbox_mode)
    except CoreWriteForbidden:
        raise
    except Exception:
        pass


def apply_alias(cmd: str, aliases: dict[str, str] | None) -> str:
    aliases = aliases if aliases is not None else {}
    cmd = (cmd or "").strip()
    if not cmd:
        return cmd
    parts = cmd.split()
    head = parts[0].lower()
    if head in aliases:
        repl = str(aliases[head]).strip()
        tail = " ".join(parts[1:]).strip()
        return (repl + (" " + tail if tail else "")).strip()
    return cmd
