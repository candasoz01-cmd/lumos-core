"""
Workspace sözleşmesi: sabit trash hedefi ve kalıcı silme yasağı.
Silinen/taşınan öğeler için yalnızca bu path kullanılır; sistem başka çöp dizini üretmez.
Kalıcı silme yalnızca kullanıcı kararı (açık komut) ile; otomatik purge yok.

Çekirdek overwrite yasağı (sandbox hazırlığı): Çekirdek state path'leri tek kaynak;
sandbox açıldığında bu path'lere doğrudan yazma yasak guard'ında kullanılır.
"""
from __future__ import annotations

from pathlib import Path

from core.guard_audit import GuardEvent, record_guard_event

# Sözleşme: tek çöp dizin adı; yeni trash/deleted vb. eklenmez.
LUMOS_TRASH_DIRNAME = "trash"

# Sandbox hedef dizini: sandbox modunda yazım hedefi tek bu alt dizin; yeni sandbox2 vb. eklenmez.
# writing_base_dir(live_base, is_sandbox_mode=True) == live_base / LUMOS_SANDBOX_DIRNAME.
LUMOS_SANDBOX_DIRNAME = "sandbox"

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
    "presence.json",
    "identity.json",
    "keystore.json",
)


def trash_path(base_dir: Path | str) -> Path:
    """Çalışma köküne göre tek geçerli trash dizinini döndürür."""
    return Path(base_dir) / LUMOS_TRASH_DIRNAME


def sandbox_base_path(live_base_dir: Path | str) -> Path:
    """
    Canlı çalışma köküne göre tek sandbox kök path.
    Sandbox modunda yazım hedefi bu base altındadır; canlı çekirdek path'e yazılmaz (allow_write_to_core).
    Dönüş her zaman resolve edilir (platform tutarlılığı: örn. macOS /var vs /private/var).
    """
    return Path(live_base_dir).resolve() / LUMOS_SANDBOX_DIRNAME


def writing_base_dir(live_base_dir: Path | str, is_sandbox_mode: bool) -> Path:
    """
    Yazım hedefi base: sandbox kapalıyken canlı base, açıkken sandbox base.
    Tek kaynak; sistem keyfi hedef seçemez. Canlı çekirdek koruması allow_write_to_core ile aynen kalır.
    Dönüş her zaman resolve edilir (platform tutarlılığı).
    """
    if is_sandbox_mode:
        return sandbox_base_path(live_base_dir)
    return Path(live_base_dir).resolve()


def alias_file_path(base_dir: Path | str) -> Path:
    """
    aliases.json için sözleşmedeki tek çekirdek path.
    Çekirdek state listesi ve sandbox guard'ı ile hizalı tutulur.
    """
    return Path(base_dir) / "aliases.json"


def notes_file_path(base_dir: Path | str) -> Path:
    """
    notes.enc.json için sözleşmedeki tek çekirdek path.
    Çekirdek state listesi ve sandbox guard'ı ile hizalı tutulur.
    """
    return Path(base_dir) / "notes.enc.json"


def presence_cfg_path(base_dir: Path | str) -> Path:
    """
    presence.json için sözleşmedeki tek çekirdek path.
    Çekirdek state listesi ve sandbox guard'ı ile hizalı tutulur.
    """
    return Path(base_dir) / "presence.json"


def identity_file_path(base_dir: Path | str) -> Path:
    """
    identity.json için sözleşmedeki tek çekirdek path.
    Çekirdek state listesi ve sandbox guard'ı ile hizalı tutulur.
    """
    return Path(base_dir) / "identity.json"


def keystore_file_path(base_dir: Path | str) -> Path:
    """
    keystore.json için sözleşmedeki tek çekirdek path.
    Çekirdek state listesi ve sandbox guard'ı ile hizalı tutulur.
    """
    return Path(base_dir) / "keystore.json"


def config_file_path(base_dir: Path | str) -> Path:
    """
    config.json için sözleşmedeki tek path.
    Çekirdek state listesi ve sandbox guard'ı ile hizalı tutulur.
    """
    return Path(base_dir) / "config.json"


def logs_dir_path(base_dir: Path | str) -> Path:
    """
    logs dizini için sözleşmedeki tek path.
    Çekirdek state listesi ve sandbox guard'ı ile hizalı tutulur.
    """
    return Path(base_dir) / "logs"


def logs_file_path(base_dir: Path | str) -> Path:
    """
    Ana log dosyası (log.txt) için sözleşmedeki path.
    Çekirdek state listesi ve sandbox guard'ı ile hizalı tutulur.
    """
    return logs_dir_path(base_dir) / "log.txt"


def append_log_line(
    base_dir: Path | str,
    line: str,
    *,
    is_sandbox_mode: bool = False,
) -> None:
    """
    logs/log.txt için satır ekleme sink'i.

    - Path: logs_file_path(base_dir)
    - Guard: allow_write_to_core(live_base_dir=base_dir, target_path=logs_file_path)
      is_sandbox_mode=True iken canlı çekirdek path'e yazmayı reddeder.
    - is_sandbox_mode varsayılan False olduğu için mevcut davranış korunur.
    """
    path = logs_file_path(base_dir)
    if not allow_write_to_core(base_dir, path, is_sandbox_mode=is_sandbox_mode):
        raise CoreWriteForbidden(
            "Sandbox modunda canlı çekirdek logs/log.txt path'ine yazma yasak",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(existing + line + "\n", encoding="utf-8")


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


def save_config_json(
    base_dir: Path | str,
    data: dict,
    *,
    is_sandbox_mode: bool = False,
) -> None:
    """
    config.json yazımı için merkezi sink.

    - Path: config_file_path(base_dir)
    - Guard: allow_write_to_core(live_base_dir=base_dir, target_path=config_file_path)
      is_sandbox_mode=True iken canlı çekirdek path'e yazmayı reddeder.
    - is_sandbox_mode varsayılan False olduğu için mevcut davranış korunur.
    """
    path = config_file_path(base_dir)
    if not allow_write_to_core(base_dir, path, is_sandbox_mode=is_sandbox_mode):
        raise CoreWriteForbidden(
            "Sandbox modunda canlı çekirdek config.json path'ine yazma yasak",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    import json  # yerel import: workspace_contract yüzeyini dar tutmak için

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_notes_enc_json(
    base_dir: Path | str,
    data: dict,
    *,
    is_sandbox_mode: bool = False,
) -> None:
    """
    notes.enc.json yazımı için merkezi sink.

    - Path: notes_file_path(base_dir)
    - Guard: allow_write_to_core(live_base_dir=base_dir, target_path=notes_file_path)
      is_sandbox_mode=True iken canlı çekirdek path'e yazmayı reddeder.
    - is_sandbox_mode varsayılan False olduğu için mevcut davranış korunur.
    """
    path = notes_file_path(base_dir)
    if not allow_write_to_core(base_dir, path, is_sandbox_mode=is_sandbox_mode):
        raise CoreWriteForbidden(
            "Sandbox modunda canlı çekirdek notes.enc.json path'ine yazma yasak",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    import json  # yerel import: workspace_contract yüzeyini dar tutmak için
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def save_presence_cfg_json(
    base_dir: Path | str,
    data: dict,
    *,
    is_sandbox_mode: bool = False,
) -> None:
    """
    presence.json yazımı için merkezi sink.

    - Path: presence_cfg_path(base_dir)
    - Guard: allow_write_to_core(live_base_dir=base_dir, target_path=presence_cfg_path)
      is_sandbox_mode=True iken canlı çekirdek path'e yazmayı reddeder.
    - is_sandbox_mode varsayılan False olduğu için mevcut davranış korunur.
    """
    path = presence_cfg_path(base_dir)
    if not allow_write_to_core(base_dir, path, is_sandbox_mode=is_sandbox_mode):
        raise CoreWriteForbidden(
            "Sandbox modunda canlı çekirdek presence.json path'ine yazma yasak",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    import json  # yerel import: workspace_contract yüzeyini dar tutmak için

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_identity_json(
    base_dir: Path | str,
    data: dict,
    *,
    is_sandbox_mode: bool = False,
) -> None:
    """
    identity.json yazımı için merkezi sink.

    - Path: identity_file_path(base_dir)
    - Guard: allow_write_to_core(live_base_dir=base_dir, target_path=identity_file_path)
      is_sandbox_mode=True iken canlı çekirdek path'e yazmayı reddeder.
    - is_sandbox_mode varsayılan False olduğu için mevcut davranış korunur.
    """
    path = identity_file_path(base_dir)
    if not allow_write_to_core(base_dir, path, is_sandbox_mode=is_sandbox_mode):
        raise CoreWriteForbidden(
            "Sandbox modunda canlı çekirdek identity.json path'ine yazma yasak",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    import json  # yerel import: workspace_contract yüzeyini dar tutmak için

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_keystore_json(
    base_dir: Path | str,
    data: dict,
    *,
    is_sandbox_mode: bool = False,
) -> None:
    """
    keystore.json yazımı için merkezi sink.

    - Path: keystore_file_path(base_dir)
    - Guard: allow_write_to_core(live_base_dir=base_dir, target_path=keystore_file_path)
      is_sandbox_mode=True iken canlı çekirdek path'e yazmayı reddeder.
    - is_sandbox_mode varsayılan False olduğu için mevcut davranış korunur.
    """
    path = keystore_file_path(base_dir)
    if not allow_write_to_core(base_dir, path, is_sandbox_mode=is_sandbox_mode):
        raise CoreWriteForbidden(
            "Sandbox modunda canlı çekirdek keystore.json path'ine yazma yasak",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    import json  # yerel import: workspace_contract yüzeyini dar tutmak için

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_task_store_json(
    tasks_dir: Path | str,
    data: dict,
    *,
    sandbox_mode: bool,
    live_base_dir: Path | str | None = None,
) -> None:
    """
    TaskStore için merkezi yazım sink'i.

    - Path: tasks_dir / "tasks.json" (TaskStore.base_dir ile hizalı)
    - Guard (yalnızca sandbox_mode=True iken):
      allow_write_to_core(live_base_dir or tasks_dir.parent, target_path, is_sandbox_mode=True)
      canlı çekirdek state path'ine yazmayı reddeder.
    - sandbox_mode=False varsayılan davranışı korur; guard devre dışı.
    """
    tasks_dir_path = Path(tasks_dir)
    target_path = tasks_dir_path / "tasks.json"

    if sandbox_mode:
        live_base = Path(live_base_dir) if live_base_dir is not None else tasks_dir_path.parent
        if not allow_write_to_core(live_base, target_path, is_sandbox_mode=True):
            raise CoreWriteForbidden(
                "Sandbox modunda canlı çekirdek state path'e yazma yasak",
            )

    tasks_dir_path.mkdir(parents=True, exist_ok=True)
    import json  # yerel import: workspace_contract yüzeyini dar tutmak için

    target_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_allowed_trash_path(base_dir: Path | str, path: Path | str) -> bool:
    """
    Verilen path, sözleşmedeki tek trash hedefi mi?
    Silinen/taşınan öğe yalnızca bu path'e gidebilir; başka çöp dizini kullanılamaz.
    """
    base = Path(base_dir).resolve()
    candidate = Path(path).resolve()
    return candidate == base / LUMOS_TRASH_DIRNAME


def ensure_trash_dir(
    base_dir: Path | str,
    *,
    is_sandbox_mode: bool = False,
) -> None:
    """
    Trash dizinini oluşturan merkezi sink (yoksa oluşturur).

    - Path: trash_path(writing_base_dir(base_dir, is_sandbox_mode)); sandbox sözleşmesi ile hizalı.
    - Guard: allow_write_to_core(live_base_dir=base_dir, path, is_sandbox_mode)
      is_sandbox_mode=True iken canlı çekirdek path'e yazmayı reddeder; yazım sandbox/trash'e gider.
    """
    dest_base = writing_base_dir(base_dir, is_sandbox_mode)
    path = trash_path(dest_base)
    if not allow_write_to_core(base_dir, path, is_sandbox_mode=is_sandbox_mode):
        raise CoreWriteForbidden(
            "Sandbox modunda canlı çekirdek trash path'ine yazma yasak",
        )
    path.mkdir(parents=True, exist_ok=True)


def move_to_trash(
    base_dir: Path | str,
    source_path: Path | str,
    *,
    is_sandbox_mode: bool = False,
) -> Path:
    """
    Dosya veya dizini sözleşmedeki tek trash dizinine taşıyan merkezi sink.

    - Hedef: trash_path(writing_base_dir(base_dir, is_sandbox_mode)); sandbox sözleşmesi ile hizalı.
    - Guard: is_allowed_trash_path(dest_base, dest_dir) ve
      allow_write_to_core(live_base_dir=base_dir, dest_dir, is_sandbox_mode).
    - Hedef dosya zaten varsa FileExistsError.

    Dönüş: taşınan öğenin yeni path'i.
    """
    import shutil

    source = Path(source_path).resolve()
    dest_base = writing_base_dir(base_dir, is_sandbox_mode)
    dest_dir = trash_path(dest_base)
    if not is_allowed_trash_path(dest_base, dest_dir):
        raise CoreWriteForbidden(
            "Trash hedefi sözleşmedeki path değil",
        )
    if not allow_write_to_core(base_dir, dest_dir, is_sandbox_mode=is_sandbox_mode):
        raise CoreWriteForbidden(
            "Sandbox modunda canlı çekirdek trash path'ine yazma yasak",
        )
    ensure_trash_dir(base_dir, is_sandbox_mode=is_sandbox_mode)
    dest = dest_dir / source.name
    if dest.exists():
        raise FileExistsError(f"Trash hedefi zaten var: {dest}")
    shutil.move(str(source), str(dest))
    return dest


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

    Davranış modeli:
    - is_sandbox_mode=False ise: mevcut davranış korunur, her zaman True döner.
      Bu, canlı modda core state'e yazmanın guard tarafından kısıtlanmadığı
      (sadece üst katman politika ile sınırlı olduğu) anlamına gelir.
    - is_sandbox_mode=True ise: target_path live_base_dir altında ve çekirdek state ise False.
      Bu durumda audit kaydı da üretilir.
    """
    live = Path(live_base_dir).resolve()
    target = Path(target_path).resolve()

    if not is_sandbox_mode:
        # Mevcut davranışı koru; yine de audit için allow kararı log'lanabilir.
        record_guard_event(
            GuardEvent(
                action="write",
                decision="allow",
                path=target,
                sandbox_mode=False,
                reason="sandbox_disabled",
                caller="workspace_contract.allow_write_to_core",
            ),
        )
        return True

    try:
        target.relative_to(live)
    except ValueError:
        # Hedef canlı base altında değil; sandbox guard kapsamı dışında.
        record_guard_event(
            GuardEvent(
                action="write",
                decision="allow",
                path=target,
                sandbox_mode=True,
                reason="outside_live_base",
                caller="workspace_contract.allow_write_to_core",
            ),
        )
        return True

    if is_core_state_path(live, target):
        record_guard_event(
            GuardEvent(
                action="write",
                decision="deny",
                path=target,
                sandbox_mode=True,
                reason="core_state_under_live_base",
                caller="workspace_contract.allow_write_to_core",
            ),
        )
        return False

    record_guard_event(
        GuardEvent(
            action="write",
            decision="allow",
            path=target,
            sandbox_mode=True,
            reason="non_core_under_live_base",
            caller="workspace_contract.allow_write_to_core",
        ),
    )
    return True


class CoreWriteForbidden(Exception):
    """Sandbox modunda canlı çekirdek state path'e yazma girişimi."""

# lumos:instruction-pipeline safe touch

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)

# lumos:instruction-pipeline safe touch (resync)
