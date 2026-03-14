# Panel Phase 1 Read-Only Bridge — Tamamlanma Checkpoint

**Tarih:** Phase 1 tamamlandı kabulü; Phase 2 ilk adım için referans.

## Phase 1 özeti

- **Amaç:** Panel ekranlarını read-only backend verisiyle besleyebilecek hattı kurmak. Yazım yok; sadece okuma.
- **Kaynak:** `panel/scripts/read_backend_state.py` — workspace_contract, consent_ok, tasks.json, trash dizini, logs dosyası kullanılır. Çıktı `window.__LUMOS_READ_STATE__` ile panel'e enjekte edilir (`--write` ile `panel/js/state_inject.js`).
- **Akış:** Bridge (`backend-bridge.js`) → backend şeklini döner; fixture mapper'lar (`fixtures.js`) panel contract şekline çevirir; adapter (`app.js`) `getXxxData()` ile normalizer üzerinden ekrana veri sağlar. Backend yoksa veya eksikse demo/fixture fallback kullanılır.

## Read-only bridge ile bağlı ekranlar

| Ekran | Bridge fonksiyonu | Veri kaynağı (read_backend_state.py) | Not |
|-------|-------------------|--------------------------------------|-----|
| Dashboard | readBackendDashboardState | dashboard (sandbox_mode, writing_base_dir, guard_status, recent_events, warnings) | ENV + base |
| Sandbox | readBackendSandboxState | sandbox (sandbox_mode, sandbox_source, writing_base_dir) | ENV + base |
| **System** | readBackendSystemState | system.system_health (workspace_contract, task_engine, sandbox_source, trash_contract, config_sink, identity_sink, keystore_sink, general) | **Phase 2 ilk gerçek okuma hedefi** |
| Config | readBackendConfigState | config.config_snapshot (profil, workspace_root, write_status) | Salt okunur; yazım yok |
| Identity | readBackendIdentityState | identity (identity_state, identity_guard_result vb.) | İçerik okunmaz; sadece durum |
| Keystore | readBackendKeystoreState | keystore (keystore_ready, keystore_state; consent_ok ile) | Anahtar ifşası yok |
| Görevler | readBackendTasksState | tasks.task_list (base/tasks.json) | Salt okunur |
| Silinenler | readBackendTrashState | trash.trash_items (base/trash dizini) | Salt okunur |
| Kayıtlar | readBackendLogsState | logs.log_items (base/logs/log.txt) | Salt okunur |

## Bilinçli sınırlar (Phase 1)

- **Backend write yok:** Hiçbir ekran yazma isteği göndermez; panel sadece okur.
- **Tek kaynak:** Gerçek canlı API/fetch yok; veri `read_backend_state.py` çıktısı veya fixture/demo.
- **System ekranı:** Şu an `system_health` değerleri büyük ölçüde türetilmiş (consent_ok, sabit notlar). Phase 2'de ilk gerçek backend okuma noktaları bu ekranda açılacak (örn. startup_health, workspace_contract doğrudan okuma).
- **Hash routing, Türkçe arayüz, demo/fixture fallback** korunur; davranış kırılmaz.

## Phase 2 — İlk adım: System ekranı

- **Hedef:** Yalnızca System ekranında ilk gerçek backend okuma noktalarını netleştirmek ve (dar kapsamda) kullanmak.
- **Noktalar:** `read_backend_state.py` içinde `system_health` üretimi tek ve genişletilebilir yapıya alınır (SYSTEM_HEALTH_KEYS); ileride her kart için gerçek okuma (startup_health, task_engine durumu vb.) bu yapı üzerinden eklenebilir.
- **Panel tarafı:** Bridge/contracts/fixtures/app hattı System için aynı `system_health` şemasını kullanır; ek kart veya alan eklendiğinde sadece sıra ve anahtarlar uyumlu tutulur.
- **Kapsam:** Sadece System; diğer ekranlarda davranış değişikliği yok.
