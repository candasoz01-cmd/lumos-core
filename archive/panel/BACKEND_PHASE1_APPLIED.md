# Phase 1 — Read-only bridge uygulandı

**Amaç:** Dashboard, Korumalı Alan ve Sistem Durumu ekranları için repo içi okunabilir kaynaklardan veri çekmeye hazır katman. Backend davranışı değiştirilmedi; yazma akışlarına dokunulmadı.

---

## Gerçekten bağlanan alanlar

| Ekran    | Alan / kaynak | Açıklama |
|----------|----------------|----------|
| Dashboard | `sandbox_mode`, `writing_base_dir` | workspace_contract: `writing_base_dir(live_base, is_sandbox_mode)` → "canlı" / "sandbox" |
| Dashboard | `guard_status` | Sabit "KORUMA AKTİF" (panel metni; guard davranışı değişmedi) |
| Dashboard | `recent_events`, `warnings` | Boş dizi (tek okuma noktası yok; fallback’te bırakıldı) |
| Sandbox   | `sandbox_mode`, `writing_base_dir` | Aynı workspace_contract kaynağı |
| Sandbox   | `sandbox_source` | "varsayılan" (CLI/ENV kaynak etiketi tek alan değil; zorlanmadı) |
| System    | `system_health.workspace_contract` | Sabit ok/note (sözleşme yüklü) |
| System    | `system_health.sandbox_source`, `trash_contract` | Sözleşmeden türetilen sabit notlar |
| System    | `system_health.general` | startup_health.consent_ok(base_dir) → status + note |
| System    | task_engine, config_sink, identity_sink, keystore_sink | "Veri yok." (backend’de ayrı okuma yok) |

---

## Fallback’te bırakılan alanlar

| Ekran    | Alan | Neden |
|----------|------|--------|
| Dashboard | Son aktivite (recent_events) | Log/presence/task tek toplayıcı yok; backend davranışı değiştirilmedi. |
| Dashboard | Uyarı listesi (warnings) | Toplayıcı yok. |
| Sandbox   | Kaynak etiketi (CLI/ENV/varsayılan) | main’de dağınık; tek okuma alanı yok. |
| System    | Lock, presence, keystore, identity, config sink | get_durum_parts/get_startup_summary keystore ve presence modülü ister; bu turda sadece consent_ok kullanıldı. |

---

## Teknik not

- **Okuma kaynağı:** `panel/scripts/read_backend_state.py` — yalnızca `workspace_contract` (writing_base_dir, sandbox_base_path, LUMOS_SANDBOX_DIRNAME) ve `startup_health.consent_ok` import eder. main.py, yazma, guard/sink davranışı değişmez.
- **Panel tarafı:** `js/backend-bridge.js` → `window.__LUMOS_READ_STATE__` varsa (dashboard/sandbox/system payload’ları) döner; yoksa `null` → mevcut fixture/demo fallback.
- **Enjeksiyon:** `state_inject.js` varsayılan `null`. Canlı veri için: `PYTHONPATH=src python3 panel/scripts/read_backend_state.py --write` → `panel/js/state_inject.js` güncellenir; panel yenilenince backend okuma kullanılır.
- **Env:** `LUMOS_BASE_DIR` (varsayılan `.lumos`), `LUMOS_SANDBOX_MODE` (varsayılan `false`).

---

## Sonraki gerçek entegrasyon adımı

- Tek okuma kanalı (ör. durum endpoint’ı veya panel’i besleyen host) tanımlandığında: base_dir ve is_sandbox_mode bu kanaldan verilir; script veya API aynı payload şeklini üretir.
- Son aktivite / uyarı listesi için backend’de toplayıcı veya log/presence okuma açıldığında dashboard payload’a eklenir.
- System: get_durum_parts veya get_startup_summary’nin tam çıktısı (keystore/presence ile) bir endpoint’tan panel’e verildiğinde 8+1 kart doldurulabilir.
