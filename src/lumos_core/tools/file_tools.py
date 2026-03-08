"""
Minimal read-only file content tool for Lumos v1.
Read-only: no file modification. Only files under the project root (cwd) are readable.
No path traversal (../). Large files return a bounded preview. Binary or unsupported return a clear message.
"""
from __future__ import annotations

from pathlib import Path

# Phrases that indicate "read this/that file". Path can follow the phrase or be in context.
# Order: more specific first. If phrase matches, the remainder of the message is treated as path
# (strip), or use current_file from context if no remainder.
_FILE_READ_PATTERNS: list[tuple[str, str]] = [
    ("read file ", "read file "),
    ("read this file", "read this file"),
    ("dosya içeriğini ver ", "dosya içeriğini ver "),
    ("dosya içeriğini ver", "dosya içeriğini ver"),
    ("bu dosyada ne yazıyor ", "bu dosyada ne yazıyor "),
    ("bu dosyada ne yazıyor", "bu dosyada ne yazıyor"),
    ("bu dosyayı oku ", "bu dosyayı oku "),
    ("bu dosyayı oku", "bu dosyayı oku"),
    ("şu dosyayı göster ", "şu dosyayı göster "),
    ("şu dosyayı göster", "şu dosyayı göster"),
    ("bu dosyayı göster ", "bu dosyayı göster "),
    ("bu dosyayı göster", "bu dosyayı göster"),
]

# Known binary extensions (read-only: we refuse to return content)
_BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp",
    ".pdf", ".zip", ".tar", ".gz", ".xz", ".zst", ".rar", ".7z",
    ".pyc", ".so", ".dll", ".dylib", ".exe", ".woff", ".woff2",
    ".mp3", ".mp4", ".wav", ".ogg", ".webm", ".mov",
})

_MAX_PREVIEW_CHARS = 8_000  # bounded preview for large files
_PREVIEW_TRUNCATE_SUFFIX = "\n\n... (dosya büyük; önizleme kısaltıldı)"
_MAX_OUTPUT_LEN = 12_000  # cap total tool output (preview + header)
_OUTPUT_TRUNCATE_SUFFIX = "\n... (çıktı kısaltıldı)"

_MSG_MISSING = "Lumos: Dosya bulunamadı."
_MSG_BINARY = "Lumos: Bu dosya türü (ikili/ metin dışı) desteklenmiyor; sadece metin dosyaları okunabilir."
_MSG_NOT_FILE = "Lumos: Bu bir dosya değil veya okunamıyor."
_MSG_WHICH_FILE = "Lumos: Hangi dosyayı okuyayım? Dosya adını veya yolunu yazın (örn. README.md)."
_MSG_PERMISSION = "Lumos: Dosya okuma izni yok."
_MSG_ERROR = "Lumos: Dosya okunamadı."


def _cap_output(text: str, max_len: int = _MAX_OUTPUT_LEN, suffix: str = _OUTPUT_TRUNCATE_SUFFIX) -> str:
    if not text or len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + suffix


def _resolve_path(cwd: Path, path_str: str) -> Path | None:
    """Resolve path relative to cwd (project root). Return None if path escapes cwd (e.g. ..)."""
    path_str = (path_str or "").strip()
    if not path_str:
        return None
    try:
        resolved = (cwd / path_str).resolve()
        # Ensure resolved is under cwd (no path traversal)
        resolved.relative_to(cwd.resolve())
        return resolved
    except (ValueError, RuntimeError):
        return None


def _is_likely_binary(path: Path, first_chunk: bytes) -> bool:
    if path.suffix.lower() in _BINARY_EXTENSIONS:
        return True
    if b"\x00" in first_chunk:
        return True
    return False


def _read_file_safe(cwd: Path, path_str: str) -> str:
    """
    Read text file under cwd. Return content (or bounded preview) or user-facing error string.
    No path traversal; binary/unsupported return clear message.
    """
    resolved = _resolve_path(cwd, path_str)
    if resolved is None:
        return _MSG_MISSING
    if not resolved.exists():
        return _MSG_MISSING
    if not resolved.is_file():
        return _MSG_NOT_FILE
    try:
        with open(resolved, "rb") as f:
            first_chunk = f.read(8192)
        if _is_likely_binary(resolved, first_chunk):
            return _MSG_BINARY
    except PermissionError:
        return _MSG_PERMISSION
    except OSError:
        return _MSG_ERROR

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(_MAX_PREVIEW_CHARS + 1)
        if len(content) > _MAX_PREVIEW_CHARS:
            content = content[:_MAX_PREVIEW_CHARS].rstrip() + _PREVIEW_TRUNCATE_SUFFIX
        header = f"Dosya: {resolved.name}\n\n"
        return _cap_output(header + content)
    except UnicodeDecodeError:
        return _MSG_BINARY
    except PermissionError:
        return _MSG_PERMISSION
    except OSError:
        return _MSG_ERROR


def _extract_file_path(message: str, current_file: str | None) -> tuple[str | None, bool]:
    """
    If message matches a file-read intent, return (path_to_read, True).
    Path comes from the rest of the message after the phrase, or current_file.
    If matched but no path available, return (None, True). If no match, return (None, False).
    """
    msg = (message or "").strip()
    if not msg:
        return (None, False)
    lower = msg.lower()
    for _, key in _FILE_READ_PATTERNS:
        if key not in lower:
            continue
        idx = lower.index(key)
        after = msg[idx + len(key) :].strip()
        if after:
            return (after, True)
        if current_file and current_file.strip():
            return (current_file.strip(), True)
        return (None, True)  # matched but no path
    return (None, False)


def try_handle_read_file(
    message: str,
    cwd: Path | None = None,
    current_file: str | None = None,
) -> str | None:
    """
    If the message matches a read-file intent, read the file and return the result string.
    Otherwise return None (caller should route to provider).
    Read-only: path is resolved under cwd (project root) only; no path traversal. Binary/large handled as specified.
    """
    path_to_read, matched = _extract_file_path(message, current_file)
    if not matched:
        return None
    if path_to_read is None:
        return _MSG_WHICH_FILE
    base = cwd if cwd is not None else Path.cwd()
    return _read_file_safe(base, path_to_read)
