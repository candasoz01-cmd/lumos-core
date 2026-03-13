"""
Yetki profilleri ve güvenlik sınırı.
Genel onay modu izin profilinin kapsadığı işlerle sınırlıdır;
kritik işler asla otomatik yapılmaz.

Açık onay (sözleşme): Öner ama bekle / açık onayla uygula ayrımı.
- Analiz/öneri: analyze, read, plan — açık onay gerekmez.
- Uygulama adımları: safe_local, write_local — kisitli_otonom'da yalnızca
  general_approval True iken izinli; rapor profili hiçbir uygulama adımına izin vermez.
Tek guard: is_allowed_for_profile(profile, step_type, general_approval).
"""
from __future__ import annotations

# Profil adları (canonical, dosya/CLI ile uyumlu)
PROFILE_RAPOR = "rapor"
PROFILE_GUVENLI_YURUT = "guvenli_yurut"
PROFILE_KISITLI_OTONOM = "kisitli_otonom"

ALL_PROFILES = (PROFILE_RAPOR, PROFILE_GUVENLI_YURUT, PROFILE_KISITLI_OTONOM)

# Adım türleri (güvenlik sınırı kontrolü için)
# Analiz/öneri (açık onay gerekmez): analyze, read, plan
STEP_TYPE_ANALYZE = "analyze"       # sadece analiz, hiçbir değişiklik yok
STEP_TYPE_READ = "read"             # dosya/not okuma
STEP_TYPE_PLAN = "plan"             # plan üretme, öneri
# Uygulama (kisitli_otonom'da general_approval gerekir): safe_local, write_local
STEP_TYPE_SAFE_LOCAL = "safe_local" # güvenli yerel iş (self test, commit önerisi vb.)
STEP_TYPE_WRITE_LOCAL = "write_local"  # yerel yazma (dikkatli; kalıcı silme hariç)
STEP_TYPE_EXTERNAL = "external"     # dış servis / network
STEP_TYPE_CRITICAL = "critical"     # kritik sistem ayarı, kalıcı silme, geri dönüşsüz

# Kod düzeyinde: asla otomatik yapılmayan işler (profil/genel onaydan bağımsız)
SECURITY_NEVER_AUTO = frozenset({
    "permanent_delete",      # kalıcı silme
    "external_write",        # dış servislere kontrolsüz yazma
    "irreversible_user_op",  # kullanıcı adına geri dönüşsüz işlem
    "critical_system_config", # kritik sistem ayarı değişikliği
})

SECURITY_BOUNDARY_DESCRIPTION = (
    "Asla otomatik: kalıcı silme, dış servise kontrolsüz yazma, "
    "geri dönüşsüz kullanıcı işlemi, kritik sistem ayarı değişikliği."
)


def get_profile_display_name(profile: str) -> str:
    if profile == PROFILE_RAPOR:
        return "rapor (sadece analiz, uygulama yok)"
    if profile == PROFILE_GUVENLI_YURUT:
        return "güvenli yürüt (yerel güvenli işler)"
    if profile == PROFILE_KISITLI_OTONOM:
        return "kısıtlı otonom (genel onay ile çok adımlı)"
    return profile


def is_allowed_for_profile(profile: str, step_type: str, general_approval: bool) -> bool:
    """
    Profil + genel onay ile bu adım türüne izin var mı?
    Açık onay guard'ı: uygulama adımları (safe_local, write_local) kisitli_otonom'da
    yalnızca general_approval True iken izinli; rapor hiçbir uygulama adımına izin vermez.
    - rapor: sadece analyze, read, plan (analiz/öneri)
    - guvenli_yurut: analyze, read, plan, safe_local; write_local yok
    - kisitli_otonom: general_approval False iken sadece analyze, read, plan;
      True iken safe_local ve write_local da izinli. critical/external asla izinli değil.
    """
    if step_type == STEP_TYPE_CRITICAL or step_type == STEP_TYPE_EXTERNAL:
        return False
    if profile == PROFILE_RAPOR:
        return step_type in (STEP_TYPE_ANALYZE, STEP_TYPE_READ, STEP_TYPE_PLAN)
    if profile == PROFILE_GUVENLI_YURUT:
        return step_type in (STEP_TYPE_ANALYZE, STEP_TYPE_READ, STEP_TYPE_PLAN, STEP_TYPE_SAFE_LOCAL)
    if profile == PROFILE_KISITLI_OTONOM:
        if not general_approval:
            return step_type in (STEP_TYPE_ANALYZE, STEP_TYPE_READ, STEP_TYPE_PLAN)
        return step_type in (STEP_TYPE_ANALYZE, STEP_TYPE_READ, STEP_TYPE_PLAN, STEP_TYPE_SAFE_LOCAL, STEP_TYPE_WRITE_LOCAL)
    return False


def is_safe_step_kind(kind: str) -> bool:
    """Adım türü güvenlik sınırı dışında mı (yani güvenli mi)."""
    return kind in (STEP_TYPE_ANALYZE, STEP_TYPE_READ, STEP_TYPE_PLAN, STEP_TYPE_SAFE_LOCAL)
