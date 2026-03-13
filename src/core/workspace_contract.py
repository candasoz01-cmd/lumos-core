"""
Workspace sözleşmesi: sabit trash hedefi ve kalıcı silme yasağı.
Silinen/taşınan öğeler için yalnızca bu path kullanılır; sistem başka çöp dizini üretmez.
Kalıcı silme yalnızca kullanıcı kararı (açık komut) ile; otomatik purge yok.
"""
from __future__ import annotations

from pathlib import Path

# Sözleşme: tek çöp dizin adı; yeni trash/deleted vb. eklenmez.
LUMOS_TRASH_DIRNAME = "trash"


def trash_path(base_dir: Path | str) -> Path:
    """Çalışma köküne göre tek geçerli trash dizinini döndürür."""
    return Path(base_dir) / LUMOS_TRASH_DIRNAME


def is_allowed_trash_path(base_dir: Path | str, path: Path | str) -> bool:
    """
    Verilen path, sözleşmedeki tek trash hedefi mi?
    Silinen/taşınan öğe yalnızca bu path'e gidebilir; başka çöp dizini kullanılamaz.
    """
    base = Path(base_dir).resolve()
    candidate = Path(path).resolve()
    return candidate == base / LUMOS_TRASH_DIRNAME


def may_perform_permanent_delete(user_initiated: bool) -> bool:
    """
    Kalıcı silme yalnızca kullanıcı açık komutu ile.
    user_initiated=True ise (açık kullanıcı kararı) izin verilir; aksi halde asla.
    """
    return user_initiated
