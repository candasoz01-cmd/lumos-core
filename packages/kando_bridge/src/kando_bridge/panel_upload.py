"""POST /panel/upload — panel dosya yükleme (v1: yalnız attach).

Sözleşme (PANEL-UPLOAD-HANDLER-01):
- Canonical uç **yalnız** ``/panel/upload``.
- v1 kapsamı: doğrula → canonical sandbox upload sink'ine **atomik** yaz →
  metadata döndür. Özetleme, OCR, model analizi ve ``intent=analyze``
  **kapsam dışıdır**.
- Dosya asla repo köküne veya ``.lumos/`` çekirdeğine yazılmaz; hedef daima
  ``<repo>/workspace/uploads/<YYYY-MM-DD>/`` altıdır.
- Aynı SHA-256 yeniden gelirse **fiziksel kopya oluşturulmaz**; mevcut kayıt
  döndürülür ve audit'e ``duplicate`` olarak yazılır.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from kando_bridge.transcribe import _extract_multipart_field  # multipart deseni tek yerde

UPLOAD_FIELD = "file"
UPLOAD_MAX_BYTES_DEFAULT = 10 * 1024 * 1024
UPLOAD_DIR_NAME = "uploads"

# İzinli tipler: uzantı → alternatif imzalar. Her imza (offset, beklenen)
# çiftlerinden oluşur ve **tüm çiftler** eşleşmelidir; alternatiflerden biri
# tutması yeter. Boş demet = yalnız uzantı kontrolü (düz metin biçimleri).
# Content-Type'a tek başına güvenilmez; uzantı + magic byte birlikte bakılır.
_Signature = tuple[tuple[int, bytes], ...]
_ALLOWED: dict[str, tuple[_Signature, ...]] = {
    ".txt": (),
    ".md": (),
    ".json": (),
    ".csv": (),
    ".pdf": ((((0, b"%PDF-")),),),
    ".png": (((0, b"\x89PNG\r\n\x1a\n"),),),
    ".jpg": (((0, b"\xff\xd8\xff"),),),
    ".jpeg": (((0, b"\xff\xd8\xff"),),),
    # WebP = RIFF konteyneri + 8. offset'te "WEBP"; yalnız RIFF bakmak WAV gibi
    # diğer RIFF türlerinin .webp adıyla geçmesine izin verirdi.
    ".webp": (((0, b"RIFF"), (8, b"WEBP")),),
    ".gif": (((0, b"GIF87a"),), ((0, b"GIF89a"),)),
}


def _signature_matches(signature: _Signature, data: bytes) -> bool:
    return all(data[off : off + len(expected)] == expected for off, expected in signature)

_MIME_BY_EXT = {
    ".txt": "text/plain", ".md": "text/markdown", ".json": "application/json",
    ".csv": "text/csv", ".pdf": "application/pdf", ".png": "image/png",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".gif": "image/gif",
}

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def upload_max_bytes() -> int:
    """Boyut sınırı env ile ayarlanabilir; kodda sabit değildir."""
    raw = str(os.environ.get("LUMOS_PANEL_UPLOAD_MAX_BYTES", "")).strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return UPLOAD_MAX_BYTES_DEFAULT


def upload_enabled() -> bool:
    return str(os.environ.get("LUMOS_PANEL_UPLOAD_ENABLED", "1")).strip().lower() not in {
        "0", "false", "no", "off",
    }


def sanitize_filename(raw: str | None) -> str:
    """Path traversal, null byte ve aşırı uzunluğa karşı ad temizleme."""
    name = (raw or "").replace("\\", "/").split("/")[-1]
    name = name.replace("\x00", "").strip()
    name = _SAFE_NAME_RE.sub("_", name).strip("._") or "dosya"
    return name[:96]


def _extension(name: str) -> str:
    return ("." + name.rsplit(".", 1)[1].lower()) if "." in name[1:] else ""


def validate_media(name: str, data: bytes) -> tuple[str | None, str | None]:
    """(mime, hata) — uzantı allowlist'i + magic byte doğrulaması."""
    ext = _extension(name)
    if ext not in _ALLOWED:
        return None, "unsupported_media_type"
    signatures = _ALLOWED[ext]
    if signatures and not any(_signature_matches(sig, data) for sig in signatures):
        # Beyan edilen uzantı ile gerçek içerik uyuşmuyor.
        return None, "unsupported_media_type"
    return _MIME_BY_EXT.get(ext, "application/octet-stream"), None


def uploads_dir(repo_root: Path, *, day: str | None = None) -> Path:
    """Canonical sandbox upload sink'i: <repo>/workspace/uploads/<gün>/."""
    stamp = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (Path(repo_root) / "workspace" / UPLOAD_DIR_NAME / stamp).resolve()


def _find_existing(root: Path, digest: str) -> Path | None:
    """Aynı SHA-256 daha önce yazılmış mı (gün dizinleri boyunca)."""
    base = (Path(root) / "workspace" / UPLOAD_DIR_NAME).resolve()
    if not base.is_dir():
        return None
    prefix = digest[:16] + "-"
    try:
        for day_dir in sorted(base.iterdir()):
            if not day_dir.is_dir():
                continue
            for item in day_dir.iterdir():
                if item.is_file() and item.name.startswith(prefix):
                    return item
    except OSError:
        return None
    return None


def _atomic_write(target: Path, data: bytes) -> None:
    """tmp'ye yaz → fsync → os.replace. Hata halinde kısmi dosya bırakmaz."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".upload-", dir=target.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)


def _audit(repo_root: Path, target: Path, decision: str, reason: str) -> None:
    """Guard kararını audit'e yaz. Dosya içeriği ve tam yol log'a taşınmaz."""
    try:
        import sys

        src = str((Path(repo_root) / "src").resolve())
        if src not in sys.path:
            sys.path.insert(0, src)
        from core.guard_audit import GuardEvent, record_guard_event

        record_guard_event(
            GuardEvent(
                action="write",
                decision=decision,
                path=target,
                sandbox_mode=False,
                reason=reason,
                caller="panel_upload",
            )
        )
    except Exception:
        # Audit yazımı asıl akışı bozmaz.
        pass


def handle_panel_upload_request(
    content_type: str | None,
    raw: bytes,
    *,
    repo_root: Path,
    content_length: int | None = None,
) -> tuple[int, dict]:
    """Panel dosya yükleme isteğini doğrular ve sandbox sink'ine yazar."""
    if not upload_enabled():
        return 403, {"ok": False, "error": "upload_disabled",
                     "message": "Dosya yükleme şu an kapalı."}

    limit = upload_max_bytes()
    declared = content_length if content_length is not None else len(raw)
    if declared > limit:
        return 413, {"ok": False, "error": "file_too_large", "limit_bytes": limit,
                     "message": "Dosya boyutu sınırı aşıldı."}

    if (content_type or "").split(";")[0].strip().lower() != "multipart/form-data":
        return 400, {"ok": False, "error": "invalid_multipart",
                     "message": "Dosya multipart/form-data ile gönderilmeli."}

    data, filename_hint = _extract_multipart_field(content_type, raw, UPLOAD_FIELD)
    if data is None:
        return 400, {"ok": False, "error": "file_required",
                     "message": "Dosya gerekli."}
    if not data:
        return 400, {"ok": False, "error": "empty_file",
                     "message": "Dosya boş."}
    if len(data) > limit:
        return 413, {"ok": False, "error": "file_too_large", "limit_bytes": limit,
                     "message": "Dosya boyutu sınırı aşıldı."}

    name = sanitize_filename(filename_hint)
    mime, media_error = validate_media(name, data)
    if media_error:
        return 415, {"ok": False, "error": media_error,
                     "allowed": sorted(_ALLOWED),
                     "message": "Bu dosya türü desteklenmiyor."}

    digest = hashlib.sha256(data).hexdigest()

    # Aynı içerik daha önce yazıldıysa fiziksel kopya oluşturulmaz.
    existing = _find_existing(repo_root, digest)
    if existing is not None:
        _audit(repo_root, existing, "allow", "duplicate")
        return 200, {
            "ok": True,
            "duplicate": True,
            "file": _metadata(existing, repo_root, name=existing.name,
                              size=len(data), mime=mime, digest=digest),
            "approval": None,
        }

    target = uploads_dir(repo_root) / f"{digest[:16]}-{name}"
    # Sandbox sınırı: hedef daima workspace/uploads altında olmalı.
    ws = (Path(repo_root) / "workspace").resolve()
    try:
        target.relative_to(ws)
    except ValueError:
        _audit(repo_root, target, "deny", "outside_workspace")
        return 403, {"ok": False, "error": "path_outside_workspace",
                     "message": "Hedef çalışma alanı dışında."}

    try:
        _atomic_write(target, data)
    except OSError:
        _audit(repo_root, target, "deny", "write_failed")
        return 507, {"ok": False, "error": "sandbox_quota_exceeded",
                     "message": "Dosya kaydedilemedi."}

    _audit(repo_root, target, "allow", "stored")
    return 200, {
        "ok": True,
        "duplicate": False,
        "file": _metadata(target, repo_root, name=name, size=len(data),
                          mime=mime, digest=digest),
        "approval": None,
    }


def _metadata(target: Path, repo_root: Path, *, name: str, size: int,
              mime: str | None, digest: str) -> dict:
    """Yanıt metadata'sı — mutlak yol sızdırılmaz, repo-göreli yol verilir."""
    try:
        rel = str(target.relative_to(Path(repo_root).resolve()))
    except ValueError:
        rel = target.name
    return {
        "name": name,
        "size": size,
        "mime": mime,
        "sha256": digest,
        "stored_as": target.name,
        "sandbox_path": rel,
    }
