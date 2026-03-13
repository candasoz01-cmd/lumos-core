# Guard zinciri — teknik durum özeti

Kod seviyesinde hangi guard’ların aktif olduğunun kısa referansı. Sonraki runtime sandbox aşaması için temel belge.

---

## Milestone 1 kapanış özeti

| Başlık | Ana korunan dosyalar | Test koruması | Kalan açık risk |
|--------|----------------------|---------------|------------------|
| Kalıcı silme / sabit trash | `src/core/workspace_contract.py` (LUMOS_TRASH_DIRNAME, trash_path, is_allowed_trash_path, may_perform_permanent_delete), `src/task_engine/engine.py` (TaskStore.delete), `src/main.py` (görev sil → user_initiated=True) | `tests/test_workspace_contract.py` — LUMOS_TRASH_DIRNAME, trash_path, is_allowed_trash_path, may_perform_permanent_delete | Silinen öğe fiziksel olarak trash’e taşınmıyor; main’de trash_dir hâlâ `base / "trash"`; silme/taşıma akışında trash_path(base) ve is_allowed_trash_path zorunlu değil. |
| Açık onay | `src/task_engine/profiles.py` (STEP_TYPE_*, SECURITY_NEVER_AUTO, is_allowed_for_profile, STEP_PERMISSION_MATRIX), `src/task_engine/engine.py` (run_task) | `tests/test_task_engine.py` — is_allowed_for_profile matrisi ve runtime step enforcement senaryoları | CLI → engine genel onay bayrağının tek kaynaktan ve doğru set edilmesi henüz audit edilmedi; UI/CLI tarafında açık onay akışı formel değil. |
| Çekirdek overwrite | `src/core/inviolable.py` (verify_core_constants, EXPECTED_*), `src/core/workspace_contract.py` (CORE_STATE_PATH_NAMES) | `tests/test_core_inviolable.py` — çekirdek sabitler, SECURITY_NEVER_AUTO, profil adları; `tests/test_workspace_contract.py` — CORE_STATE_PATH_NAMES | verify_core_constants() sadece testte çalışıyor; runtime’da çekirdek sabit doğrulaması ve çekirdek path’e yazma yasağı henüz zorunlu değil. |
| Sandbox / kopya alanı | `src/core/workspace_contract.py` (CORE_STATE_PATH_NAMES, is_core_state_path, allow_write_to_core, CoreWriteForbidden), `src/task_engine/engine.py` (TaskStore.sandbox_mode, TaskStore._save) | `tests/test_workspace_contract.py` — is_core_state_path, allow_write_to_core; TaskStore sandbox_mode=True ile canlı path’e yazmada CoreWriteForbidden | Sadece TaskStore bu guard’a bağlı; diğer yazıcılar (SecureNotesStore, save_aliases, save_presence_cfg, keystore/identity) ve main/CLI sandbox modunu henüz kullanmıyor. |
| Runtime sandbox enforcement | Aynı: TaskStore üzerinden `src/task_engine/engine.py` + allow_write_to_core ile `src/core/workspace_contract.py` | `tests/test_workspace_contract.py` — TaskStore sandbox senaryoları | Runtime sandbox sadece TaskStore için devrede; diğer side-effect sink’ler ve tüm yazma yollarında zorunlu değil; sandbox_mode bayrağı CLI’dan sistematik geçmiyor. |
| Merkezi yetki matrisi | `src/task_engine/profiles.py` (STEP_PERMISSION_MATRIX, is_allowed_for_profile, STEP_TYPE_*) | `tests/test_task_engine.py` — profil × adım türü matrisi | Yeni adım türleri veya profiller eklenirse matrisin ve testlerin birlikte güncellenmemesi riski; tüm adım yürütümlerinin bu matrise zorunlu bağlı olduğu henüz runtime’da ayrı bir guard ile doğrulanmıyor. |
| Görev adımı karar katmanı | `src/task_engine/profiles.py` (get_decision_layer benzeri katman mantığı, STEP_TYPE_*, SECURITY_NEVER_AUTO), `src/task_engine/engine.py` (run_task’ta adım türü/katman kullanımı) | `tests/test_task_engine.py` — decision layer’a bağlı step enforcement senaryoları (analiz/uygulama ayrımı) | Adımın `kind` alanı ile gerçek yapılan işin her zaman uyuştuğu henüz garanti değil; bir step içinde yanlış türde side-effect (ör. write_local işleri analyze adımında) yapılmasını engelleyen ayrı bir guard yok. |
| Runtime step enforcement | `src/task_engine/engine.py` (run_task — her adım öncesi may_execute_step_at_runtime), `src/task_engine/profiles.py` (may_execute_step_at_runtime, STEP_PERMISSION_MATRIX) | `tests/test_task_engine.py` — test_runtime_step_enforcement_* (external/critical red, analiz rapor izinli) | Tüm görev çalıştırma yüzeylerinin (farklı entrypoint/komutlar) aynı runtime guard’ı kullandığı formel olarak test edilmedi; SECURITY_NEVER_AUTO ile kalıcı silme gibi özel adım türleri için ek red branch’i henüz ayrı guard olarak yok. |

---

## Kalıcı silme / sabit trash guard

- **Korunan:** Kalıcı silme yalnızca kullanıcı komutu; tek çöp dizini sözleşmesi.
- **Ana dosyalar:** `src/core/workspace_contract.py` (may_perform_permanent_delete, trash_path, is_allowed_trash_path, LUMOS_TRASH_DIRNAME); `src/task_engine/engine.py` (TaskStore.delete); `src/main.py` (görev sil → user_initiated=True).
- **Test:** `tests/test_workspace_contract.py` — LUMOS_TRASH_DIRNAME, trash_path, is_allowed_trash_path, may_perform_permanent_delete.
- **Açık risk:** Silinen öğe fiziksel olarak trash’e taşınmıyor (sadece JSON’dan çıkarılıyor). main’de trash_dir hâlâ `base / "trash"`; trash_path(base) kullanılmıyor. is_allowed_trash_path silme/taşıma akışında zorlamada değil.

---

## Açık onay guard / Runtime step enforcement

- **Korunan:** write_local/safe_local yalnızca yetki + genel onay ile; rapor hiç uygulama adımı yürütmez; critical/external asla izinli değil.
- **Ana dosyalar:** `src/task_engine/profiles.py` (may_execute_step_at_runtime, is_allowed_for_profile, PROFILE_*, STEP_TYPE_*); `src/task_engine/engine.py` (run_task — her adım öncesi may_execute_step_at_runtime).
- **Test:** `tests/test_task_engine.py` — is_allowed_for_profile matrisi; runtime: test_runtime_step_enforcement_* (external/critical red, analiz rapor izinli).
- **Açık risk:** CLI → engine genel onay bayrağının tek kaynaktan ve doğru set edilmesi ayrı audit konusu olabilir.

### Docs seviyesi vs runtime guard (step enforcement)

| Ne | Nerede kalır | Runtime’da zorlanan mı |
|----|----------------|-------------------------|
| Karar katmanları (analiz / öneri / uygulama / asla) metni | docs/lumos-karar-sozlesmesi.md, .cursor/rules | Evet: step.kind → get_decision_layer → asla ise red; diğerleri is_allowed_for_profile |
| Yetki matrisi (profil × adım türü × genel onay) | profiles.py STEP_PERMISSION_MATRIX | Evet: may_execute_step_at_runtime(profile, step_type, general_approval) run_task’ta her adım öncesi |
| SECURITY_NEVER_AUTO (permanent_delete, external_write, …) listesi | profiles.py, docs | Kısmen: external/critical adım türü runtime’da asla izinli değil; kalıcı silme ayrı guard (may_perform_permanent_delete) |
| “Analiz adımı uygulama gibi yürütülmesin” | Sözleşme metni | Evet: adım türü (kind) belirleyici; uygulama türü profil/onay uygun değilse adım yürütülmez |

---

## Çekirdek overwrite guard

- **Korunan:** Çekirdek sabitlerin değiştirilmemesi; çekirdek state path listesi tek kaynak.
- **Ana dosyalar:** `src/core/inviolable.py` (verify_core_constants, EXPECTED_*); `src/core/workspace_contract.py` (CORE_STATE_PATH_NAMES).
- **Test:** `tests/test_core_inviolable.py` — verify_core_constants(), SECURITY_NEVER_AUTO, LUMOS_TRASH_DIRNAME, profil adları, critical/external asla izinli değil. `tests/test_workspace_contract.py` — CORE_STATE_PATH_NAMES.
- **Açık risk:** verify_core_constants() yalnızca testte çağrılıyor; runtime’da sabit doğrulama yok. Yazma noktalarında “çekirdek path’e yazma yasak” kontrolü henüz yok (sandbox kapalı).

---

## Sandbox / kopya guard

- **Korunan:** Çekirdek state path tanımı; “bu path çekirdek mi?” (is_core_state_path); sandbox modunda canlı çekirdek path'e yazma reddi (allow_write_to_core). TaskStore runtime’da sandbox_mode=True iken canlı çekirdek path’e yazarsa CoreWriteForbidden fırlatır.
- **Ana dosyalar:** `src/core/workspace_contract.py` (CORE_STATE_PATH_NAMES, is_core_state_path, allow_write_to_core, CoreWriteForbidden); `src/task_engine/engine.py` (TaskStore.sandbox_mode, TaskStore._save guard).
- **Test:** `tests/test_workspace_contract.py` — is_core_state_path; allow_write_to_core (sandbox True/False, core/non-core); TaskStore sandbox_mode=True ile canlı path’e yazmada CoreWriteForbidden.
- **Açık risk:** Diğer yazıcılar (SecureNotesStore, save_aliases, save_presence_cfg, keystore/identity) henüz guard’a bağlı değil; sandbox modu main/CLI’da açılmadığı için şu an sadece TaskStore dar uygulama.

---

## Bir sonraki teknik faz

Bu aşamadan sonra yeni guard açarken hedef, mevcut zinciri üç dar eksende sertleştirmek:

1. **Side-effect sink ve sandbox merkezileştirme**  
   - Tüm yazıcılar (TaskStore, SecureNotesStore, save_aliases, save_presence_cfg, keystore/identity) tek bir side-effect katmanına bağlansın; bu katman allow_write_to_core + CORE_STATE_PATH_NAMES üzerinden sandbox/enforce yapsın.  
   - main/CLI’dan gelen sandbox_mode bayrağı bu katmana tek kaynaktan aktarılsın; sandbox dışı yazma girişimleri için ortak CoreWriteForbidden benzeri hata yüzeyi oluşturulsun.

2. **Genel onay + explicit approval + runtime execution zincirinin sıkı birleşmesi**  
   - CLI/UI’daki açık onay (kilit açma, kalıcı silme, genel onay) tek bir approval state’e iner; engine sadece bu state üzerinden adım yürütümü yapsın.  
   - SECURITY_NEVER_AUTO kapsamındaki adımlar için (özellikle permanent_delete) run_task içinde ayrı red branch’i ve bunun etrafında entegrasyon/test senaryoları tanımlansın.

3. **Görev adımı türü ↔ gerçek side-effect eşleşmesi**  
   - Her step.kind (analyze, safe_local, write_local, external/critical yok) için izin verilen yan etkiler netleştirilip, step gövdesinde yanlış türde iş yapılmasına karşı runtime guard eklenmesi planlansın.  
   - Bu eşleşme hem merkezi yetki matrisiyle hem de testlerle korunarak, docs’taki karar katmanları tablosu ile runtime davranışı bire bir hizalansın.

---

*Referans: docs/lumos-guard-kalici-silme-teşhis.md, docs/lumos-guard-acik-onay-teshis.md, docs/lumos-guard-cekirdek-overwrite-cikti.md, docs/lumos-guard-sandbox-kopya-siniri.md.*
