# Phase 1 — Gerçek entegrasyon okuma hazırlığı

**Amaç:** Dashboard, Sandbox ve System ekranları için ilk bağ noktalarının repo içinde nerede olduğunu doğrulamak. Backend davranışı değiştirilmedi; yalnızca okuma odaklı analiz.

---

## Dashboard readiness

| Soru | Sonuç |
|------|--------|
| **Bugün gerçekten okunabilecek veri nerede?** | `workspace_contract`: `writing_base_dir(live_base, is_sandbox_mode)`, sabitler. Sandbox durumu ve yazım hedefi bu fonksiyonlarla türetilebilir. Guard/son olay/uyarı için tek okuma noktası yok. |
| **Doğrudan bağlanabilir** | `workspace_contract.writing_base_dir`, `LUMOS_SANDBOX_DIRNAME` (live_base + is_sandbox_mode panel tarafına başka yoldan verilirse). |
| **Mapping ister** | Sandbox + guard + son N olay + uyarılar → tek dashboard payload; tarih alanları panel formatına. |
| **Henüz hazır değil** | Son aktivite kaynağı (log/presence/task belirsiz); guard durumu metni; uyarı listesi toplayıcı. Panel'e base_dir ve is_sandbox_mode sağlayacak tek okuma kanalı (API) yok. |
| **Entegrasyon riski** | **Orta** — birden fazla kaynaktan toplulaştırma; tek giriş noktası olmadığı için ilk adımda kısmi bağ yeterli. |

---

## Sandbox readiness

| Soru | Sonuç |
|------|--------|
| **Bugün gerçekten okunabilecek veri nerede?** | `src/core/workspace_contract.py`: `sandbox_base_path(live_base_dir)`, `writing_base_dir(live_base_dir, is_sandbox_mode)`, `LUMOS_SANDBOX_DIRNAME`. Hepsi salt okuma (fonksiyon/sabit). `main.py`: `sandbox_mode` = `_sandbox_mode_from_env()` veya CLI `--sandbox`; `base_dir` = `_lumos_dir()`. `CoreState` içinde `_sandbox_mode`, `_base_dir` tutuluyor; dışarıya API ile açılmıyor. |
| **Doğrudan bağlanacak alanlar** | `workspace_contract` import edilip `writing_base_dir(base, is_sandbox)`, `sandbox_base_path(base)` çağrılabilir. Panel tarafı base ve is_sandbox'ı alabildiği anda metrics (Yazım Yönü, Sandbox Base) doğrudan türetilir. |
| **Mapping gerektiren alanlar** | is_sandbox_mode + live_base → panel contract metrics (Kaynak, Sandbox Base, Yazım Yönü, Sözleşme Durumu). Sections statik kalabilir. "Kaynak" (CLI/ENV/varsayılan) bilgisi main'de dağınık; tek alan yok. |
| **Henüz beklemesi gereken alanlar** | Sandbox "kaynak" etiketi (CLI/ENV/varsayılan) için tek okuma noktası yok. Panel'in base_dir ve is_sandbox_mode alacağı ilk kanal (ör. durum endpoint'ı) henüz tanımlı değil. |
| **Entegrasyon riski** | **Düşük** — workspace_contract ile doğrudan eşleşir; eksik sadece kaynak etiketi ve panel'e state sağlama kanalı. |

---

## System readiness

| Soru | Sonuç |
|------|--------|
| **Bugün gerçekten okunabilecek veri nerede?** | `src/core/startup_health.py`: `get_startup_summary(base_dir, keystore_initialized, presence_module)` → tek satır string; `get_durum_parts(...)` → `consent_ok`, `lock_ok`, `durum_label`, `not_line`. Consent/lock/presence odaklı; panel'in beklediği 8+1 health kartı yapısı yok. |
| **Doğrudan bağlanacak alanlar** | **Phase 2 (dar):** `workspace_contract` — `core.workspace_contract` import + `trash_path(base)`, `sandbox_base_path(base)` (salt okuma). `task_engine` — `base/tasks.json` varlığı ve JSON okunabilirliği (`read_backend_state.py` içinde). |
| **Mapping gerektiren alanlar** | `get_startup_summary` veya `get_durum_parts` → en azından "Genel Sağlık" kartı (status: ok/uyarı, note: summary veya not_line). Diğer kartlar için backend'de ayrı kontrol yok; genişletme veya placeholder kart gerekir. |
| **Henüz beklemesi gereken alanlar** | Sandbox kaynağı, config/identity/keystore sink için ayrı backend kontrolleri (şu an türetilmiş/sabit notlar). startup_health tam kart seti üretmiyor. |
| **Entegrasyon riski** | **Orta** — mevcut özet/durum ile tek kart doldurulabilir; Phase 2 ile workspace_contract ve task_engine dar gerçek okumaya bağlandı. |

---

## Özet tablo

| Ekran    | Doğrudan bağlanacak                    | Mapping gerekir                          | Henüz bekleyen                                      |
|----------|----------------------------------------|------------------------------------------|-----------------------------------------------------|
| Dashboard| writing_base_dir, sandbox sabit (giriş verilirse) | Sandbox+guard+olay+uyarı → payload       | Son aktivite, guard metni, uyarı listesi, giriş kanalı |
| Sandbox  | writing_base_dir, sandbox_base_path, LUMOS_SANDBOX_DIRNAME | is_sandbox + base → metrics               | Kaynak etiketi, panel'e base_dir/is_sandbox kanalı   |
| System   | workspace_contract (yükleme+path), task_engine (tasks.json okunabilirliği) | get_startup_summary / get_durum_parts → genel kart | Diğer kartlar türetilmiş/sabit; ileride genişletilebilir |

**Not:** "Giriş kanalı" / "panel'e state sağlama": Backend davranışı değiştirilmediği için şu an panel veriyi doğrudan repo içi modüllerden okuyamıyor; ilk gerçek bağ için tek okuma noktası (ör. durum API'si) tanımlandığında base_dir, is_sandbox_mode ve isteğe bağlı health özeti buradan beslenecek.

**Phase 2 (Görevler / Silinenler / Kayıtlar):** Görevler için `list_updated` (tasks.json dosya mtime) backend’den okunuyor; Silinenler için `trash_location` çözümlenmiş path. Kayıtlar için `log_file_updated` (log.txt mtime) ve `log_location` (çözümlenmiş path) backend’den okunuyor. original_path/scope trash’ta yok; "—" fallback.

**Phase 2 checkpoint (panel):** Gerçek okuma / fallback / sınırlar / sonraki adım özeti: `panel/PANEL_PHASE2_CHECKPOINT.md`.
