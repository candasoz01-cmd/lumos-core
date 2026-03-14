# Panel Phase 2 Read-Only Backend — Checkpoint

**Amaç:** Phase 2 dar read-only backend genişlemesi sonrası kalıcı özet. Davranış değiştirilmedi; yalnızca hangi alanın gerçek okumaya bağlandığı ve nelerin fallback kaldığı netleştirilir.

---

## Gerçek backend okumaya bağlanan ekran/alanlar

| Ekran | Alan | Kaynak (read_backend_state.py) |
|-------|------|---------------------------------|
| **Sistem Durumu** | workspace_contract | core.workspace_contract import + trash_path(base), sandbox_base_path(base); ok / uyarı + not |
| **Sistem Durumu** | task_engine | base/tasks.json varlığı ve JSON okunabilirliği; ok / — + not |
| **Sistem Durumu** | keystore_sink, general | consent_ok(base) türetilmiş; ifşa yok |
| **Görevler** | task_list | base/tasks.json (id, title, status, updated, last_run, output_summary) |
| **Görevler** | list_updated | tasks.json dosya mtime (ISO); panelde "Liste son güncelleme" |
| **Silinenler** | trash_location | Çözümlenmiş (absolute) path |
| **Silinenler** | trash_items, trash_last_move | base/trash dizin listesi, son taşıma zamanı |
| **Kayıtlar** | log_items | base/logs/log.txt son 100 satır |
| **Kayıtlar** | log_file_updated, log_location | log.txt mtime (ISO), çözümlenmiş path |
| **Dashboard** | sandbox_mode, writing_base_dir | ENV + base (canlı/sandbox) |
| **Sandbox** | sandbox_mode, writing_base_dir, sandbox_source | ENV + base; sandbox_source sabit "varsayılan" |
| **Config** | config_snapshot (profil, workspace_root, write_status) | ENV + base; yazım yok |
| **Identity** | identity_state, identity_guard_result vb. | Sabit/durum; içerik okunmaz |
| **Keystore** | keystore_ready, keystore_state | consent_ok ile türetilmiş; anahtar ifşası yok |

---

## Hâlâ fallback / mock kalan alanlar

| Ekran | Alan | Neden |
|-------|------|--------|
| **Dashboard** | recent_events, warnings | Tek toplayıcı/okuma noktası yok; boş dizi |
| **Dashboard** | guard_status | Sabit "KORUMA AKTİF" metni |
| **Sandbox** | sandbox_source | CLI/ENV kaynak etiketi tek alan değil; "varsayılan" |
| **Sistem Durumu** | sandbox_source, trash_contract, config_sink, identity_sink | Sabit/türetilmiş notlar; ayrı backend kontrolü yok |
| **Görevler** | guard_result (satır bazlı) | Backend’de görev bazlı guard sonucu yok; "—" |
| **Görevler** | selected_task_id | UI state; backend’de yok |
| **Silinenler** | original_path, scope (öğe bazlı) | Sadece dizin listesi; taşıma metadata yok; "—" |
| **Kayıtlar** | Satır bazlı timestamp | log.txt satır timestamp’i yok; dosya mtime kullanılıyor |
| **Kayıtlar** | log_filter | Sabit "all" |
| **Config / Identity / Keystore** | last_activity, identity_last_write, keystore_last_update vb. | İsteğe bağlı alanlar; tek okuma noktası yok veya sabit |

---

## Bilinçli sınırlar

- **Backend write yok:** Hiçbir ekran yazma isteği göndermez.
- **Tek kaynak:** Canlı API/fetch yok; veri `read_backend_state.py` çıktısı (`--write` → state_inject.js) veya fixture/demo.
- **Hash routing, Türkçe arayüz, demo/fixture fallback** korunur; backend verisi yoksa panel aynı ekranları fallback ile gösterir.
- **Panel dışına yayılma yok:** Genişleme yalnızca panel/ ve read_backend_state.py; main.py, guard, yazım akışları değişmedi.

---

## Sonraki mantıklı teknik adım

- **Tek okuma kanalı:** Panel’i besleyen tek giriş (ör. durum endpoint’ı veya host tarafı state sağlama) tanımlandığında, base_dir ve is_sandbox_mode bu kanaldan verilebilir; script veya API aynı payload şeklini üretir.
- **Dashboard/Sandbox derinleştirme:** recent_events, warnings, sandbox kaynak etiketi için backend’de toplayıcı veya tek alan açıldığında payload’a eklenebilir.
- **System kartları:** startup_health / get_durum_parts genişletilerek diğer health kartları (config_sink, identity_sink vb.) gerçek kontrole bağlanabilir.

---

## Referans

- **Kaynak:** `panel/scripts/read_backend_state.py`; çıktı `window.__LUMOS_READ_STATE__` (`--write` → `panel/js/state_inject.js`).
- **Akış:** backend-bridge.js → fixtures.js (mapper) → app.js (getXxxData → normalizer) → render.
- **Phase 1 ayrıntı:** `PANEL_PHASE1_CHECKPOINT.md`, `BACKEND_PHASE1_READINESS.md`.
