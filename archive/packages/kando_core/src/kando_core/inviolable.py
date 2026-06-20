"""
Çekirdek overwrite yasağı: beklenen sabit değerler ve doğrulama.
Sistem dokunulmaz çekirdek sabitlerini kendi başına değiştiremez; bu modül
tek kaynak literal'ları tutar ve verify_core_constants() ile kontrol sağlar.
Referans: docs/lumos-guard-cekirdek-overwrite-teshis.md
"""
from __future__ import annotations

# Beklenen değerler (literal; reassignment testte bu değerlerle karşılaştırılır)
EXPECTED_SECURITY_NEVER_AUTO = frozenset({
    "permanent_delete",
    "external_write",
    "irreversible_user_op",
    "critical_system_config",
})
EXPECTED_LUMOS_TRASH_DIRNAME = "trash"
EXPECTED_PROFILE_RAPOR = "rapor"
EXPECTED_PROFILE_GUVENLI_YURUT = "guvenli_yurut"
EXPECTED_PROFILE_KISITLI_OTONOM = "kisitli_otonom"
EXPECTED_STEP_TYPE_CRITICAL = "critical"
EXPECTED_STEP_TYPE_EXTERNAL = "external"


def verify_core_constants() -> bool:
    """
    Çekirdek sabitlerin beklenen değerlerde olduğunu doğrula.
    Reassignment veya gevşetme yapıldıysa False döner.
    """
    from core import workspace_contract
    from task_engine import profiles

    if workspace_contract.LUMOS_TRASH_DIRNAME != EXPECTED_LUMOS_TRASH_DIRNAME:
        return False
    if profiles.SECURITY_NEVER_AUTO != EXPECTED_SECURITY_NEVER_AUTO:
        return False
    if profiles.PROFILE_RAPOR != EXPECTED_PROFILE_RAPOR:
        return False
    if profiles.PROFILE_GUVENLI_YURUT != EXPECTED_PROFILE_GUVENLI_YURUT:
        return False
    if profiles.PROFILE_KISITLI_OTONOM != EXPECTED_PROFILE_KISITLI_OTONOM:
        return False
    if profiles.STEP_TYPE_CRITICAL != EXPECTED_STEP_TYPE_CRITICAL:
        return False
    if profiles.STEP_TYPE_EXTERNAL != EXPECTED_STEP_TYPE_EXTERNAL:
        return False
    return True
