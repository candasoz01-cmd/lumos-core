# Dokunulmaz çekirdek / çekirdek overwrite yasağı — guard çıktı özeti

Bu belge, üçüncü guard paketi (dokunulmaz çekirdek alanlar / çekirdek overwrite yasağı) için istenen çıktı formatında özettir. Tam teşhis: `docs/lumos-guard-cekirdek-overwrite-teshis.md`.

---

## 1. Guard gerektiren kod alanları

| Alan | Konum | Taşıyan kritik dosya / modül / giriş noktası |
|------|--------|------------------------------------------------|
| **Güvenlik** | Kilit, keystore, presence, kimlik | `src/security/keystore.py`, `src/security/identity.py`, `src/security/presence_lock.py` — yazma: keystore/identity/presence dosyaları; kilidi aç: `main.py` (kullanıcı aksiyonu). |
| **Yetki** | Üç profil, STEP_TYPE_*, critical/external asla izinli değil | `src/task_engine/profiles.py` — `PROFILE_*`, `STEP_TYPE_*`, `is_allowed_for_profile()`. Giriş: `src/task_engine/engine.py` → `TaskEngine.run_task()` (her adım öncesi yetki kontrolü). |
| **Temel politika** | Offline/online, emin olmadığı yerde konuşmaz | Docs + `src/policy/`; overwrite guard için yetki + SECURITY_NEVER_AUTO yeterli. |
| **Çekirdek karar sınırları** | SECURITY_NEVER_AUTO | `src/task_engine/profiles.py` — frozenset; daraltılmaz. |
| **Kalıcı silme guard’ı** | Sadece kullanıcı komutu + uyarı; trash tek path | `src/core/workspace_contract.py` (may_perform_permanent_delete, trash_path, LUMOS_TRASH_DIRNAME); `src/task_engine/engine.py` (TaskStore.delete); `src/main.py` (görev sil → user_initiated=True). |
| **Açık onay guard’ı** | write_local/safe_local genel onay ile | `src/task_engine/profiles.py` (is_allowed_for_profile + general_approval); `src/task_engine/engine.py` (run_task). |
| **Çekirdek state yazma** | tasks.json, config, notlar, log, alias, keystore/identity | TaskStore._save; save_presence_cfg; SecureNotesStore; save_aliases; keystore/identity write. Sandbox açıldığında: bu path’lere sadece tanımlı yazıcılar; overwrite yasağı guard’ı. |

---

## 2. Aktif risk noktaları

| Risk | Konum | Önlem |
|------|--------|--------|
| **Sabit override** | Herhangi modül | `profiles.SECURITY_NEVER_AUTO = ...` vb. atama yapılmamalı. Grep ile taranır; test ile sabitler beklenen değerde (test_core_inviolable.py). |
| **SECURITY_NEVER_AUTO veya yetki gevşetmesi** | profiles.py | Set daraltılmaz; critical/external asla True dönmez. Mevcut testler regression koruması. |
| **Trash path gevşetmesi** | workspace_contract.py | LUMOS_TRASH_DIRNAME == "trash"; test_workspace_contract + test_core_inviolable. |
| **Çekirdek state’e keyfi yazma** | Sandbox açıldığında | Çekirdek state path listesi + yazma öncesi “bu path listede mi → yasak” kontrolü. |

---

## 3. En dar ilk overwrite guard paketi

- **Çekirdek sabitlerin read-only doğrulaması:** Test ile `profiles.PROFILE_*`, `STEP_TYPE_*`, `SECURITY_NEVER_AUTO` ve `workspace_contract.LUMOS_TRASH_DIRNAME` beklenen değerlerde; gevşetme veya silme testi kırar. Uygulandı: `tests/test_core_inviolable.py`.
- **Çekirdek state path listesi (tek kaynak):** Overwrite yasağı referansı için tek yerde tanım; sandbox açıldığında yazma guard’ında kullanılır. Uygulandı: `core/workspace_contract.py` → `CORE_STATE_PATH_NAMES`; test: `test_workspace_contract.py` (boş olmama + tasks.json/trash/config dahil).
- **Atama taraması:** Bu sabitlerin kendi modülü dışında reassign edilmemesi; grep ile doğrulandı (sadece tanım ve test assert’leri var).

Hedef: Sistem dokunulmaz çekirdek alanları kendi başına değiştiremez; değiştirilebilir ile dokunulmaz ayrışır; sandbox/kopya mantığıyla çelişmez; mevcut davranış bozulmaz.

---

## 4. Bilerek dokunulmayacak alanlar

- **Workspace omurgası:** `.lumos/`, `tasks/`, `logs/`, `trash/`, `config/`; `lumos-workspace-contract.mdc` ve ilgili kurallar.
- **Kalıcı silme guard’ı:** may_perform_permanent_delete, TaskStore.delete(user_initiated=...), is_allowed_trash_path, trash_path.
- **Açık onay guard’ı:** is_allowed_for_profile(..., general_approval), TaskEngine.run_task kullanımı.
- **CI teşhis ve rules:** ci-diagnosis.mdc, kando-lumos-multi-agent.mdc, lumos-karar-ozet.mdc.
- **Büyük dosya mimarisi tartışması:** Sadece en dar guard; mimari refactor açılmaz.

---

## 5. Önerilen uygulama sırası

1. **Teşhis doğrulama + grep** — Çekirdek sabit ataması sadece tanım modülünde; başka yerde reassign yok.
2. **Test: çekirdek sabitler** — SECURITY_NEVER_AUTO, LUMOS_TRASH_DIRNAME, profil adları, critical/external asla izinli değil (mevcut: test_core_inviolable.py).
3. **Çekirdek state path listesi (opsiyonel)** — Tek modülde veya dokümanda “overwrite yasağı path’leri” listesi; sandbox açıldığında kullanılacak.
4. **Docs** — Sözleşme/uygulama planında “çekirdek overwrite yasağı” cümlesi (isteğe bağlı).
5. **Commit** — Teşhis doc + test (+ opsiyonel path listesi); davranış değişikliği yok; mevcut guard’lar aynen kalır.

---

*Referans: docs/lumos-guard-cekirdek-overwrite-teshis.md, docs/lumos-karar-sozlesmesi.md, .cursor/rules/lumos-karar-ozet.mdc.*
