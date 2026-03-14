# Panel Phase 2 Read-Only Backend — Kalıcı Checkpoint

**Amaç:** Phase 2 read-only backend genişlemesinin mevcut durumunu kalıcı checkpoint ile kilitlemek; hangi ekran/alanın gerçek okumaya bağlı olduğu, nelerin fallback kaldığı ve sonraki teknik adım netleştirilir. Davranış değiştirilmedi; yalnızca mimari kilitleme. Bu turda yeni veri kaynağı açılmaz; mevcut Config + Kimlik + Anahtar Kasası hattı tek yerde özetlenir.

---

## Phase 2 dar read-only — mini checkpoint (kilitleme)

- **Config ekranında gerçek okunan:** `profil` (ENV), `workspace_root` (base path), `last_activity` (config.json mtime; dosya yoksa null), `last_activity_text` (açık fallback metni). config.json **içeriği okunmaz**; sadece path ve mtime.
- **Kimlik ekranında gerçek okunan:** `identity_state` (mevcut / mevcut değil), `identity_last_write` (identity.json mtime; yoksa null). `identity_target_scope`, `identity_guard_result` sabit. Kimlik **içeriği okunmaz**.
- **Anahtar Kasası ekranında gerçek okunan:** `keystore_ready` (consent_ok), `keystore_state` (Hazır/Kilitli), `keystore_last_update` (keystore.json mtime; yoksa null). `keystore_write_scope` sabit. Anahtar/passphrase **ifşası yok**.
- **Fallback kalan alanlar:** Dashboard (recent_events, guard_status), Sandbox (sandbox_source), System (bazı kartlar türetilmiş/sabit), Görevler (guard_result satır bazlı), Silinenler (original_path, scope), Kayıtlar (log_filter, satır timestamp). Config/Identity/Keystore’da okunamayan alanlar açık fallback (Bölüm 2).
- **Backend write neden açılmadı:** Panel salt okuma hattı ile sınırlı; yazım isteği gönderen ekran/akış yok. Güvenlik ve sözleşme gereği Phase 2’de sadece dar okuma kilitlendi.
- **Sonraki sağlıklı adım:** Görevler / Silinenler / Kayıtlar tarafında derinleştirme (içerik/metadata zenginleştirme, guard sonuçları, log satır timestamp’i vb.). Bu turda bu ekranlar için sayısal sinyaller eklendi (tasks_file_exists, task_count; trash_dir_exists, trash_item_count; log_file_exists, log_line_count); panelde gösterim dar ve kontrollü.

---

## 1. Gerçek backend okumaya bağlanan ekran ve alanlar

Aşağıdaki dört ekran ve alanları `read_backend_state.py` çıktısından gerçek okumaya bağlıdır (script çalıştırılıp `--write` ile state_inject.js güncellendiğinde canlı veri kullanılır).

### System (Sistem Durumu)

| Alan | Kaynak |
|------|--------|
| workspace_contract | `core.workspace_contract` import + `trash_path(base)`, `sandbox_base_path(base)`; ok / uyarı + not |
| task_engine | `base/tasks.json` varlığı ve JSON okunabilirliği; ok / — + not |
| keystore_sink, general | `consent_ok(base)` türetilmiş; ifşa yok |

### Görevler

| Alan | Kaynak |
|------|--------|
| task_list | `base/tasks.json` (id, title, status, updated, last_run, output_summary) |
| list_updated | tasks.json dosya mtime (ISO) |
| list_updated_text | Son güncelleme metni (panelde gösterim) |
| tasks_file_path | Çözülmüş tasks.json dosya yolu |
| tasks_file_exists | tasks.json var mı (bool) |
| task_count | Görev sayısı (sayısal özet) |

### Silinenler

| Alan | Kaynak |
|------|--------|
| trash_location | Çözümlenmiş (absolute) path |
| trash_items | `base/trash` dizin listesi (name, trash_path, moved_at; original_path/scope meta yoksa —) |
| trash_last_move | Son taşıma zamanı (dizin mtime türetilmiş) |
| trash_scope_fallback_note | original_path/scope okunamadığında açıklama metni |
| trash_dir_exists | trash dizini var mı (bool) |
| trash_item_count | Öğe sayısı (sayısal özet) |

### Kayıtlar

| Alan | Kaynak |
|------|--------|
| log_items | `base/logs/log.txt` son 100 satır |
| log_file_updated | log.txt dosya mtime (ISO) |
| log_updated_text | Son güncelleme metni (panelde gösterim) |
| log_location | Çözümlenmiş path |
| log_file_exists | log.txt var mı (bool) |
| log_line_count | Görüntülenen satır sayısı (sayısal özet) |

### Config (Yapılandırma)

| Alan | Kaynak |
|------|--------|
| profil, workspace_root | ENV (LUMOS_PROFILE), base path |
| write_status | Sabit "Salt okunur" |
| last_activity | config.json mtime (ISO); dosya yoksa null |
| last_activity_text | Dosya varsa "Config dosyası son güncelleme (mtime)."; yoksa "Config dosyası yok veya okunamadı; yalnızca okuma." |
| (içerik) | Okunmaz; sadece path + mtime (identity/keystore ile aynı dar model). |

### Identity (Kimlik)

| Alan | Kaynak |
|------|--------|
| identity_state | identity.json varlığı → "mevcut" / "mevcut değil" |
| identity_last_write | identity.json mtime (ISO); yoksa null |
| identity_target_scope, identity_guard_result | Sabit (içerik okunmaz) |

### Keystore (Anahtar Kasası)

| Alan | Kaynak |
|------|--------|
| keystore_ready, keystore_state | consent_ok(base) (mevcut) |
| keystore_last_update | keystore.json mtime (ISO); yoksa null |
| keystore_write_scope | Sabit (anahtar/passphrase ifşası yok) |

Dashboard ve Sandbox ENV/base ile beslenir. Config yukarıdaki dar gerçek okumaya (config.json mtime) bağlıdır; Identity ve Keystore aynı şekilde.

---

## 2. Hâlâ fallback / mock kalan alanlar

| Ekran | Alan | Neden |
|-------|------|--------|
| **Dashboard** | recent_events, warnings | Tek toplayıcı/okuma noktası yok; boş dizi |
| **Dashboard** | guard_status | Sabit "KORUMA AKTİF" metni |
| **Sandbox** | sandbox_source | CLI/ENV kaynak etiketi tek alan değil; "varsayılan" |
| **System** | sandbox_source, trash_contract, config_sink, identity_sink | Sabit/türetilmiş notlar; ayrı backend kontrolü yok |
| **Görevler** | guard_result (satır bazlı) | Backend’de görev bazlı guard sonucu yok; "—" |
| **Görevler** | selected_task_id | UI state; backend’de yok |
| **Silinenler** | original_path, scope (öğe bazlı) | Sadece dizin listesi; taşıma metadata yok; "—" |
| **Kayıtlar** | Satır bazlı timestamp | log.txt satır timestamp’i yok; dosya mtime kullanılıyor |
| **Kayıtlar** | log_filter | Sabit "all" |
| **Config** | (yok) | last_activity config.json mtime; last_activity_text backend’den; okunamayan açık fallback. |
| **Identity / Keystore** | (giderildi) | Phase 2 dar okuma: identity.json / keystore.json varlık + mtime; içerik okunmaz. Dosya yoksa null / açık fallback. |

---

## 3. Read-only bridge, contracts, fixtures, backend-bridge, state_inject — teknik özet

- **state_inject.js:** Tek satırlık enjeksiyon; `window.__LUMOS_READ_STATE__` değişkeni. İçerik `read_backend_state.py --write` ile yazılır; canlı API yok.
- **read_backend_state.py:** Tek okuma kaynağı. workspace_contract, base dizinleri, tasks.json, trash, logs okur; JSON payload üretir. Write yok; sadece panel için state üretimi.
- **backend-bridge.js:** `window.__LUMOS_READ_STATE__` varsa ekran bazlı backend şeklini (snake_case) döner; yoksa null → panel fixture/demo fallback.
- **contracts.js:** Panel veri şeması (CONTRACTS), stub üreticileri, normalizer'lar, applyContractFallbacks. Bridge/fixture çıktısı bu şemaya çekilir.
- **fixtures.js:** Backend-benzeri payload örnekleri ve map*PayloadToPanelData mapper'ları. Bridge çıktısı veya fixture aynı mapper ile contract şekline dönüşür.
- **Akış:** state_inject (veya yoksa fixture) → backend-bridge (snake_case) → fixtures mapper → contract normalizer → app getXxxData → render. Hash routing, Türkçe arayüz, demo/fixture fallback korunur.

---

## 4. Bilinçli sınırlar

- **Backend write yok:** Hiçbir ekran yazma isteği göndermez.
- **Tek kaynak:** Canlı API/fetch yok; veri `read_backend_state.py` çıktısı (`--write` → state_inject.js) veya fixture/demo.
- **Hash routing, Türkçe arayüz, demo/fixture fallback** korunur; backend verisi yoksa panel aynı ekranları fallback ile gösterir.
- **Panel dışına yayılma yok:** Genişleme yalnızca panel/ ve read_backend_state.py; main.py, guard, yazım akışları değişmedi.

---

## 5. Sonraki mantıklı teknik adım

- **A) Kimlik ve Anahtar Kasası Phase 2 dar okuma:** Uygulandı. identity.json / keystore.json varlık ve mtime; içerik okunmaz.
- **B) Yapılandırma Phase 2 dar okuma:** config.json path + mtime (last_activity, last_activity_text); içerik okunmaz. Okunamayan alanlar açık fallback.
- **Sonraki sağlıklı adım (Görevler / Silinenler / Kayıtlar):** Bu üç ekranda içerik/metadata zenginleştirme (guard sonuçları, original_path/scope, log satır timestamp’i vb.) — Sayısal sinyaller (task_count, trash_item_count, log_line_count) backend'den okunuyor; içerik/metadata derinleştirme sonraki adım.
- **İsteğe bağlı:** read_backend_state.py içinde tekrar eden okumaları sadeleştirme; davranış değişmez.

---

## Referans

- **Kaynak:** `panel/scripts/read_backend_state.py`; çıktı `window.__LUMOS_READ_STATE__` (`--write` → `panel/js/state_inject.js`).
- **Akış:** backend-bridge.js → fixtures.js (mapper) → app.js (getXxxData → normalizer) → render.
- **Phase 1 ayrıntı:** `PANEL_PHASE1_CHECKPOINT.md`, `BACKEND_PHASE1_READINESS.md`.
