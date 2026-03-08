"""
Minimal read-only project structure tool for Lumos.
Scans the repository under the current working directory and builds a simple codebase map.
Read-only: no file modification, no code execution. Stays inside project root; output capped.
"""
from __future__ import annotations

import re
from pathlib import Path

# Phrases that indicate "scan project / show project structure".
_PROJECT_SCAN_PATTERNS = (
    "projeyi tara",
    "proje yapısını göster",
    "proje yapısı",
    "scan project",
    "show project structure",
    "project structure",
    "repo yapısı nedir",
    "repo yapısı",
    "kod yapısı",
)

# Directories to skip when scanning (read-only safety and noise reduction).
_IGNORE_DIRS = frozenset({
    ".git", "__pycache__", ".venv", "node_modules", ".tox", "dist", "build",
    ".pytest_cache", ".ruff_cache", ".ipynb_checkpoints",
})

# Known binary extensions: do not read for hints; still list in tree.
_BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp",
    ".pdf", ".zip", ".tar", ".gz", ".xz", ".pyc", ".so", ".dll",
    ".woff", ".woff2", ".mp3", ".mp4", ".wav", ".ogg", ".webm",
})

# Small text file types we try to extract a purpose hint from.
_HINT_EXTENSIONS = frozenset({".py", ".md", ".txt"})
_MAX_DEPTH = 6
_MAX_OUTPUT_LEN = 8_000
_MAX_HINT_FILES = 80
_MAX_FILE_SIZE_FOR_HINT = 50_000  # bytes
_HINT_READ_BYTES = 2_000  # first N bytes to look for docstring/comment
_TRUNCATE_SUFFIX = "\n\n... (çıktı kısaltıldı)"
_MSG_NOT_AVAILABLE = "Lumos: Proje yapısı taranamadı."
_MSG_PERMISSION = "Lumos: Bu klasör için listeleme izni yok."


def _cap_output(text: str, max_len: int = _MAX_OUTPUT_LEN, suffix: str = _TRUNCATE_SUFFIX) -> str:
    if not text or len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + suffix


def _should_ignore_dir(name: str) -> bool:
    if name in _IGNORE_DIRS:
        return True
    if name.endswith(".egg-info"):
        return True
    return False


def _build_tree_and_paths(
    root: Path, max_depth: int
) -> tuple[list[str], set[str]]:
    """
    Build (tree_lines, relative_file_paths). Respects max_depth and ignored dirs.
    relative_file_paths are posix strings like "src/lumos_core/cli.py" for hint collection.
    """
    lines: list[str] = []
    file_paths: set[str] = set()
    root_resolved = root.resolve()
    prefix = root.name + "/" if root.name else ""

    def walk(dir_path: Path, depth: int, indent: str, rel_prefix: str) -> None:
        if depth > max_depth:
            return
        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return
        for p in items:
            try:
                # Resolve p so symlinks (e.g. /tmp -> /private/tmp on macOS) don't break relative_to
                rel = p.resolve().relative_to(root_resolved)
                rel_str = rel.as_posix()
            except ValueError:
                continue
            name = p.name
            if p.is_dir():
                if _should_ignore_dir(name):
                    continue
                lines.append(f"{indent}{name}/")
                walk(p, depth + 1, indent + "  ", rel_str + "/")
            else:
                # Omit known binary files from tree (read-only; no content to show)
                if p.suffix.lower() in _BINARY_EXTENSIONS:
                    continue
                lines.append(f"{indent}{name}")
                file_paths.add(rel_str)

    walk(root, 0, "  ", "")
    tree_lines = [prefix.rstrip("/") or "."] + lines if lines else [prefix.rstrip("/") or ".", "  (boş)"]
    return tree_lines, file_paths


def _extract_hint(content: str, path: Path) -> str | None:
    """
    Extract a short purpose hint from file content (first lines).
    Prefer module docstring, then first comment block or first line.
    """
    content = (content or "").strip()
    if not content:
        return None
    first = content[:_HINT_READ_BYTES]
    # Module docstring (triple-quoted)
    for q in ('"""', "'''"):
        m = re.search(re.escape(q) + r"(.*?)" + re.escape(q), first, re.DOTALL)
        if m:
            hint = m.group(1).strip().split("\n")[0].strip()
            if hint and len(hint) < 120:
                return hint[:100] + ("..." if len(hint) > 100 else "")
    # First line that looks like a comment
    for line in first.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            hint = line.lstrip("#").strip()
            if hint and len(hint) < 120:
                return hint[:100] + ("..." if len(hint) > 100 else "")
        if line.startswith("<!--") or line.startswith("/*"):
            continue
        # First non-empty, non-shebang line (e.g. markdown title)
        if not line.startswith("#!"):
            return line[:80] + ("..." if len(line) > 80 else "") if line else None
    return None


def _collect_hints(root: Path, tree_entries: set[str], max_files: int) -> list[tuple[str, str]]:
    """
    For paths that appear in the tree and are small text files, collect (display_name, hint).
    tree_entries: set of relative path strings like "lumos_core/cli.py", "tests/test_file.py".
    """
    hints: list[tuple[str, str]] = []
    root_resolved = root.resolve()
    for rel_str in sorted(tree_entries):
        if len(hints) >= max_files:
            break
        p = root_resolved / rel_str
        if not p.is_file():
            continue
        if p.suffix.lower() not in _HINT_EXTENSIONS:
            continue
        if p.suffix.lower() in _BINARY_EXTENSIONS:
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > _MAX_FILE_SIZE_FOR_HINT or size == 0:
            continue
        try:
            raw = p.read_bytes()
            if b"\x00" in raw[:4096]:
                continue
            content = raw.decode("utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        hint = _extract_hint(content, p)
        if hint:
            display = rel_str
            hints.append((display, hint))
    return hints


def _run_project_scan(cwd: Path) -> str:
    """
    Scan project under cwd: build tree (depth-limited, ignored dirs), then optional hints for small text files.
    Read-only; output capped. Never executes code or modifies files.
    """
    try:
        if not cwd.is_dir():
            return _MSG_NOT_AVAILABLE
        tree_lines, file_paths = _build_tree_and_paths(cwd, _MAX_DEPTH)
        hints = _collect_hints(cwd, file_paths, _MAX_HINT_FILES)
        out = "project structure:\n\n" + "\n".join(tree_lines)
        if hints:
            out += "\n\n"
            for name, hint in hints[: _MAX_HINT_FILES]:
                out += f"{name} → {hint}\n"
        return _cap_output(out)
    except PermissionError:
        return _MSG_PERMISSION
    except Exception:
        return _MSG_NOT_AVAILABLE


def try_handle_project_structure(message: str, cwd: Path | None = None) -> str | None:
    """
    If the message matches a project-scan intent, scan the project and return the result string.
    Otherwise return None. Read-only; stays inside cwd (project root); output capped.
    """
    msg = (message or "").strip()
    if not msg:
        return None
    lower = msg.lower()
    if not any(p in lower for p in _PROJECT_SCAN_PATTERNS):
        return None
    base = cwd if cwd is not None else Path.cwd()
    return _run_project_scan(base)
