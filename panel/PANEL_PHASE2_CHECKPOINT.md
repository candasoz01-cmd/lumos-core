# Panel Phase 2 Read-Only Backend — Kalıcı Checkpoint

**Amaç:** Phase 2 read-only backend genişlemesinin mevcut durumunu kalıcı checkpoint ile kilitlemek; hangi ekran/alanın gerçek okumaya bağlı olduğu, nelerin fallback kaldığı ve sonraki teknik adım netleştirilir. Davranış değiştirilmedi; yalnızca mimari kilitleme.

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
| list_updated | tasks.json dosya mtime (ISO); panelde "Liste son güncelleme" |

### Silinenler

| Alan | Kaynak |
|------|--------|
| trash_location | Çözümlenmiş (absolute) path |
| trash_items | `base/trash` dizin listesi (name, trash_path, moved_at) |
| trash_last_move | Son taşıma zamanı (dizin mtime türetilmiş) |

### Kayıtlar

| Alan | Kaynak |
|------|--------|
| log_items | `base/logs/log.txt` son 100 satır |
| log_file_updated | log.txt dosya mtime (ISO) |
| log_location | Çözümlenmiş path |

### Config (Yapılandırma)

Bu turda dokunulmadı. profil, workspace_root ENV/base; last_activity, last_activity_text sabit/fallback.

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

Dashboard ve Sandbox ENV/base ile beslenir. Config bu turda sabit/fallback; Identity ve Keystore yukarıdaki dar gerçek okumaya bağlıdır.

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
| **Config** | last_activity, last_activity_text | Bu turda dokunulmadı; sabit/fallback. |
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

- **A) Kimlik ve Anahtar Kasası Phase 2 dar okuma:** Uygulandı. identity.json / keystore.json varlık ve mtime; içerik okunmaz. Yapılandırma bu turda dokunulmadı.
- **B) read_backend_state.py içinde tekrar eden okumaları sadeleştirme:** İsteğe bağlı; aynı base/dosyalara birden fazla stat/okuma tek geçişte toplanabilir. Davranış değişmez.

---

## Referans

- **Kaynak:** `panel/scripts/read_backend_state.py`; çıktı `window.__LUMOS_READ_STATE__` (`--write` → `panel/js/state_inject.js`).
- **Akış:** backend-bridge.js → fixtures.js (mapper) → app.js (getXxxData → normalizer) → render.
- **Phase 1 ayrıntı:** `PANEL_PHASE1_CHECKPOINT.md`, `BACKEND_PHASE1_READINESS.md`.
