"""
Yetki profilleri ve güvenlik sınırı.
Genel onay modu izin profilinin kapsadığı işlerle sınırlıdır;
kritik işler asla otomatik yapılmaz.

Açık onay (sözleşme): Öner ama bekle / açık onayla uygula ayrımı.
- Analiz/öneri: analyze, read, plan — açık onay gerekmez.
- Uygulama adımları: safe_local, write_local — kisitli_otonom'da yalnızca
  general_approval True iken izinli; rapor profili hiçbir uygulama adımına izin vermez.

Bu modül karar katmanlarını ve profil bazlı yetki matrisini tek merkezde tutar:
- Karar katmanları: analiz, öneri, uygulama, asla.
- Tek guard fonksiyonu: is_allowed_for_profile(profile, step_type, general_approval).
- Yardımcılar:
  - get_decision_layer(step_type) → karar katmanı (analiz/öneri/uygulama/asla)
    - requires_explicit_approval(profile, step_type, general_approval) → bu profil için açık onay gerektiren uygulama adımı mı?
"""
from __future__ import annotations

from dataclasses import dataclass

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

# Karar katmanları (docs/lumos-karar-sozlesmesi.md ile uyumlu kavramsal seviye)
DECISION_LAYER_ANALYZE = "analiz"
DECISION_LAYER_SUGGEST = "oner"
DECISION_LAYER_APPLY = "uygulama"
DECISION_LAYER_NEVER = "asla"

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


@dataclass(frozen=True)
class StepPermission:
    """
    Tek adım türü için profil bazlı yetki matrisi.

    - decision_layer: analiz / oner / uygulama / asla
    - allowed_without_approval: genel onay kapalıyken izinli profiller
    - allowed_with_approval: genel onay açıkken izinli profiller
    """

    decision_layer: str
    allowed_without_approval: frozenset[str]
    allowed_with_approval: frozenset[str]


# Tek merkezli yetki matrisi: profil × adım türü × genel onay
STEP_PERMISSION_MATRIX: dict[str, StepPermission] = {
    # Analiz/okuma/planlama: tüm profillerde her zaman serbest (sadece analiz/öneri).
    STEP_TYPE_ANALYZE: StepPermission(
        decision_layer=DECISION_LAYER_ANALYZE,
        allowed_without_approval=frozenset(ALL_PROFILES),
        allowed_with_approval=frozenset(ALL_PROFILES),
    ),
    STEP_TYPE_READ: StepPermission(
        decision_layer=DECISION_LAYER_ANALYZE,
        allowed_without_approval=frozenset(ALL_PROFILES),
        allowed_with_approval=frozenset(ALL_PROFILES),
    ),
    STEP_TYPE_PLAN: StepPermission(
        decision_layer=DECISION_LAYER_SUGGEST,
        allowed_without_approval=frozenset(ALL_PROFILES),
        allowed_with_approval=frozenset(ALL_PROFILES),
    ),
    # safe_local (uygulama, ama sınırlı):
    # - rapor: asla
    # - guvenli_yurut: genel onaydan bağımsız izinli
    # - kisitli_otonom: yalnızca genel onay açıkken izinli
    STEP_TYPE_SAFE_LOCAL: StepPermission(
        decision_layer=DECISION_LAYER_APPLY,
        allowed_without_approval=frozenset({PROFILE_GUVENLI_YURUT}),
        allowed_with_approval=frozenset({PROFILE_GUVENLI_YURUT, PROFILE_KISITLI_OTONOM}),
    ),
    # write_local (uygulama, daha riskli):
    # - rapor: asla
    # - guvenli_yurut: asla
    # - kisitli_otonom: yalnızca genel onay açıkken izinli
    STEP_TYPE_WRITE_LOCAL: StepPermission(
        decision_layer=DECISION_LAYER_APPLY,
        allowed_without_approval=frozenset(),
        allowed_with_approval=frozenset({PROFILE_KISITLI_OTONOM}),
    ),
    # external / critical: hiçbir profilde izinli değil (asla).
    STEP_TYPE_EXTERNAL: StepPermission(
        decision_layer=DECISION_LAYER_NEVER,
        allowed_without_approval=frozenset(),
        allowed_with_approval=frozenset(),
    ),
    STEP_TYPE_CRITICAL: StepPermission(
        decision_layer=DECISION_LAYER_NEVER,
        allowed_without_approval=frozenset(),
        allowed_with_approval=frozenset(),
    ),
}


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

    Davranış matrisi (tek kaynak: STEP_PERMISSION_MATRIX):
    - rapor:
      - analyze/read/plan: her zaman izinli (analiz/öneri)
      - safe_local/write_local/external/critical: asla izinli değil
    - guvenli_yurut:
      - analyze/read/plan: her zaman izinli (analiz/öneri)
      - safe_local: her zaman izinli (uygulama, ama yerel ve güvenli)
      - write_local/external/critical: asla izinli değil
    - kisitli_otonom:
      - general_approval=False: sadece analyze/read/plan (analiz/öneri)
      - general_approval=True: analyze/read/plan + safe_local + write_local (uygulama)
      - external/critical: asla izinli değil
    """
    if profile not in ALL_PROFILES:
        return False
    perm = STEP_PERMISSION_MATRIX.get(step_type)
    if perm is None:
        return False
    if general_approval:
        return profile in perm.allowed_with_approval
    return profile in perm.allowed_without_approval


def get_decision_layer(step_type: str) -> str:
    """
    Adım türünün karar katmanı:
    - analiz: analyze, read
    - oner: plan
    - uygulama: safe_local, write_local
    - asla: external, critical veya tanımsız türler
    """
    perm = STEP_PERMISSION_MATRIX.get(step_type)
    if perm is None:
        return DECISION_LAYER_NEVER
    return perm.decision_layer


def requires_explicit_approval(profile: str, step_type: str, general_approval: bool) -> bool:
    """
    Bu profil için adım türü yapısal olarak sadece genel onay açıkken mi izinli?
    general_approval parametresi sonucu değiştirmez; imza, is_allowed_for_profile ile
    hizalı olması için eklenmiştir.
    Örnek:
    - kisitli_otonom + safe_local/write_local → True
    - guvenli_yurut + safe_local → False (genel onaydan bağımsız serbest)
    - rapor için tüm uygulama adımları zaten yasak → False
    """
    if profile not in ALL_PROFILES:
        return False
    perm = STEP_PERMISSION_MATRIX.get(step_type)
    if perm is None:
        return False
    return (
        profile in perm.allowed_with_approval
        and profile not in perm.allowed_without_approval
    )


def is_safe_step_kind(kind: str) -> bool:
    """Adım türü güvenlik sınırı dışında mı (yani güvenli mi)."""
    return kind in (STEP_TYPE_ANALYZE, STEP_TYPE_READ, STEP_TYPE_PLAN, STEP_TYPE_SAFE_LOCAL)


def may_execute_step_at_runtime(profile: str, step_type: str, general_approval: bool) -> bool:
    """
    Runtime step enforcement: Bu adım türü verilen profil ve genel onay ile yürütülebilir mi?
    TaskEngine.run_task() her adım öncesi bu fonksiyonu kullanır; analiz/öneri/uygulama/açık onay
    ayrımı böylece sadece dokümantasyon değil, gerçek runtime guard olur.
    - Karar katmanı "asla" (external, critical, tanımsız) → False.
    - Diğer türler için merkezi is_allowed_for_profile matrisi kullanılır.
    """
    if get_decision_layer(step_type) == DECISION_LAYER_NEVER:
        return False
    return is_allowed_for_profile(profile, step_type, general_approval)
