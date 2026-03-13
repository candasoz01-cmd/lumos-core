"""
Workspace sözleşmesi: sabit trash hedefi ve kalıcı silme yasağı.
Silinen/taşınan öğeler için yalnızca bu path kullanılır; sistem başka çöp dizini üretmez.
Kalıcı silme yalnızca kullanıcı kararı (açık komut) ile; otomatik purge yok.

Çekirdek overwrite yasağı (sandbox hazırlığı): Çekirdek state path'leri tek kaynak;
sandbox açıldığında bu path'lere doğrudan yazma yasak guard'ında kullanılır.
"""
from __future__ import annotations

from pathlib import Path

# Sözleşme: tek çöp dizin adı; yeni trash/deleted vb. eklenmez.
LUMOS_TRASH_DIRNAME = "trash"

# Çekirdek state path isimleri (.lumos altında; overwrite yasağı referansı).
# Sandbox/kopya yazarken bu path'lere doğrudan yazılmaz; sadece tanımlı yazıcılar yazar.
CORE_STATE_PATH_NAMES = (
    "tasks.json",
    "config",
    "config.json",
    "logs",
    "trash",
    "aliases.json",
    "notes.enc.json",
)


def trash_path(base_dir: Path | str) -> Path:
    """Çalışma köküne göre tek geçerli trash dizinini döndürür."""
    return Path(base_dir) / LUMOS_TRASH_DIRNAME


def alias_file_path(base_dir: Path | str) -> Path:
    """
    aliases.json için sözleşmedeki tek çekirdek path.
    Çekirdek state listesi ve sandbox guard'ı ile hizalı tutulur.
    """
    return Path(base_dir) / "aliases.json"


def save_aliases_json(
    base_dir: Path | str,
    aliases: dict[str, str],
    *,
    is_sandbox_mode: bool = False,
) -> None:
    """
    aliases.json yazımı için merkezi sink.

    - Path: alias_file_path(base_dir)
    - Guard: allow_write_to_core(live_base_dir=base_dir, target_path=alias_file_path)
      is_sandbox_mode=True iken canlı çekirdek path'e yazmayı reddeder.
    - is_sandbox_mode varsayılan False olduğu için mevcut davranış korunur.
    """
    path = alias_file_path(base_dir)
    if not allow_write_to_core(base_dir, path, is_sandbox_mode=is_sandbox_mode):
        raise CoreWriteForbidden(
            "Sandbox modunda canlı çekirdek aliases.json path'ine yazma yasak",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    # JSON içeriği güvenlik için dışarıda hazırlanır; burada yalnızca side-effect sink bulunur.
    import json  # yerel import: workspace_contract yüzeyini dar tutmak için

    path.write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")


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


def is_core_state_path(base_dir: Path | str, candidate_path: Path | str) -> bool:
    """
    Verilen path, çekirdek state path'lerinden biri mi?
    Sandbox açıldığında: bu path'e sandbox/kopya yazıcısıyla yazılmaz; sadece tanımlı canlı yazıcılar yazar.
    base_dir: çalışma kökü (örn. .lumos).
    candidate_path: kontrol edilen dosya/dizin (mutlak veya base_dir'e göre).
    """
    base = Path(base_dir).resolve()
    candidate = Path(candidate_path).resolve()
    try:
        rel = candidate.relative_to(base)
    except ValueError:
        return False
    parts = rel.parts
    if not parts:
        return False
    # Üst seviye dosya/dizin: CORE_STATE_PATH_NAMES ile eşleşme
    if len(parts) == 1 and parts[0] in CORE_STATE_PATH_NAMES:
        return True
    # tasks/tasks.json (TaskStore)
    if len(parts) == 2 and parts[0] == "tasks" and parts[1] == "tasks.json":
        return True
    # config/, logs/, trash/ altındaki her şey çekirdek state
    if parts[0] in ("config", "logs", "trash"):
        return True
    return False


def allow_write_to_core(
    live_base_dir: Path | str,
    target_path: Path | str,
    is_sandbox_mode: bool,
) -> bool:
    """
    Sandbox modunda canlı çekirdek state path'e yazmayı reddet.
    is_sandbox_mode=False ise her zaman True (mevcut davranış).
    is_sandbox_mode=True ise: target_path live_base_dir altında ve çekirdek state ise False.
    """
    if not is_sandbox_mode:
        return True
    live = Path(live_base_dir).resolve()
    target = Path(target_path).resolve()
    try:
        target.relative_to(live)
    except ValueError:
        return True  # hedef canlı base altında değil, izin ver
    if is_core_state_path(live, target):
        return False
    return True


class CoreWriteForbidden(Exception):
    """Sandbox modunda canlı çekirdek state path'e yazma girişimi."""
