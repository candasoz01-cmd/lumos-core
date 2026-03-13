# Guard zinciri — teknik durum özeti

Kod seviyesinde hangi guard’ların aktif olduğunun kısa referansı. Sonraki runtime sandbox aşaması için temel belge.

---

## Kalıcı silme / sabit trash guard

- **Korunan:** Kalıcı silme yalnızca kullanıcı komutu; tek çöp dizini sözleşmesi.
- **Ana dosyalar:** `src/core/workspace_contract.py` (may_perform_permanent_delete, trash_path, is_allowed_trash_path, LUMOS_TRASH_DIRNAME); `src/task_engine/engine.py` (TaskStore.delete); `src/main.py` (görev sil → user_initiated=True).
- **Test:** `tests/test_workspace_contract.py` — LUMOS_TRASH_DIRNAME, trash_path, is_allowed_trash_path, may_perform_permanent_delete.
- **Açık risk:** Silinen öğe fiziksel olarak trash’e taşınmıyor (sadece JSON’dan çıkarılıyor). main’de trash_dir hâlâ `base / "trash"`; trash_path(base) kullanılmıyor. is_allowed_trash_path silme/taşıma akışında zorlamada değil.

---

## Açık onay guard

- **Korunan:** write_local/safe_local yalnızca yetki + genel onay ile; rapor hiç uygulama adımı yürütmez; critical/external asla izinli değil.
- **Ana dosyalar:** `src/task_engine/profiles.py` (is_allowed_for_profile, PROFILE_*, STEP_TYPE_*); `src/task_engine/engine.py` (run_task — her adım öncesi is_allowed_for_profile).
- **Test:** `tests/test_task_engine.py` — is_allowed_for_profile matrisi; critical/external her zaman False.
- **Açık risk:** CLI → engine genel onay bayrağının tek kaynaktan ve doğru set edilmesi ayrı audit konusu olabilir.

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

## Sonraki mantıklı guard alanları

- **Runtime sandbox enforcement (genişletme):** TaskStore’da uygulandı; SecureNotesStore, save_aliases, save_presence_cfg, keystore/identity yazma noktalarında aynı allow_write_to_core guard’ı; sandbox modunun main/CLI’dan geçirilmesi.
- **Genel onay / yetki matrisi:** CLI’dan engine’e genel onay ve profil geçişinin tek kaynak ve tutarlı olduğunun doğrulanması; gerekirse ek test veya runtime check.
- **Görev adımı uygulama sınırı:** Adım türü (safe_local, write_local) ile gerçek yapılan işin eşleşmesi; yetkisiz iş türünün adım içinde yapılmasının engellenmesi.

---

*Referans: docs/lumos-guard-kalici-silme-teşhis.md, docs/lumos-guard-acik-onay-teshis.md, docs/lumos-guard-cekirdek-overwrite-cikti.md, docs/lumos-guard-sandbox-kopya-siniri.md.*
