"""
Dokunulmaz çekirdek alanları — overwrite yasağı guard testleri.
Sözleşme: sistem dokunulmaz çekirdek sabitlerini kendi başına değiştiremez.
Referans: docs/lumos-guard-cekirdek-overwrite-teshis.md
"""
from core.inviolable import verify_core_constants
from task_engine.profiles import (
    PROFILE_RAPOR,
    PROFILE_GUVENLI_YURUT,
    PROFILE_KISITLI_OTONOM,
    STEP_TYPE_CRITICAL,
    STEP_TYPE_EXTERNAL,
    SECURITY_NEVER_AUTO,
    is_allowed_for_profile,
)
from core.workspace_contract import LUMOS_TRASH_DIRNAME


# Beklenen çekirdek değerler (sözleşme ile uyumlu; gevşetme bu testi kırar)
EXPECTED_PROFILES = frozenset({PROFILE_RAPOR, PROFILE_GUVENLI_YURUT, PROFILE_KISITLI_OTONOM})
EXPECTED_NEVER_AUTO = frozenset({
    "permanent_delete",
    "external_write",
    "irreversible_user_op",
    "critical_system_config",
})


def test_core_constants_verify_single_gate():
    """Çekirdek sabitler tek kapı ile doğrulanır; reassignment/gevşetme testi kırar."""
    assert verify_core_constants() is True


def test_security_never_auto_inviolable():
    """SECURITY_NEVER_AUTO daraltılamaz; permanent_delete dahil dört eleman sabit."""
    assert SECURITY_NEVER_AUTO == EXPECTED_NEVER_AUTO
    assert "permanent_delete" in SECURITY_NEVER_AUTO


def test_trash_dirname_inviolable():
    """Tek çöp dizin adı sözleşmesi; değiştirilemez."""
    assert LUMOS_TRASH_DIRNAME == "trash"


def test_profile_names_inviolable():
    """Üç yetki profili sabit; critical/external izinli profil yok."""
    assert PROFILE_RAPOR == "rapor"
    assert PROFILE_GUVENLI_YURUT == "guvenli_yurut"
    assert PROFILE_KISITLI_OTONOM == "kisitli_otonom"
    assert EXPECTED_PROFILES == {PROFILE_RAPOR, PROFILE_GUVENLI_YURUT, PROFILE_KISITLI_OTONOM}


def test_critical_and_external_never_allowed():
    """critical ve external hiçbir profil ve genel onay ile izinli olmamalı."""
    for profile in (PROFILE_RAPOR, PROFILE_GUVENLI_YURUT, PROFILE_KISITLI_OTONOM):
        assert is_allowed_for_profile(profile, STEP_TYPE_CRITICAL, False) is False
        assert is_allowed_for_profile(profile, STEP_TYPE_CRITICAL, True) is False
        assert is_allowed_for_profile(profile, STEP_TYPE_EXTERNAL, False) is False
        assert is_allowed_for_profile(profile, STEP_TYPE_EXTERNAL, True) is False
