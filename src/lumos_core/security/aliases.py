import json
from pathlib import Path


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


def save_aliases(base_dir: str, aliases: dict[str, str]) -> None:
    try:
        p = _alias_path(base_dir)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")
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
