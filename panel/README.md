# Lumos Panel v1

---

## Paneli aç — adres (önce bunu oku)

| Ne | Değer |
|----|--------|
| **Kartlı sonuç ekranı** | **http://127.0.0.1:8080/#yanit** |
| **Sunucuyu nereden** | `panel` klasörünün içinde: aşağıdaki komut |

Sunucuyu **panel** dizininde başlat (böylece adres kökte kalır, `/panel/` gerekmez):

```bash
cd panel
python3 -m http.server 8080
```

**Alternatif:** Repo kökünden `python3 -m http.server 8080` → panel için **http://127.0.0.1:8080/panel/#yanit**

**Akış (`#feed`) için** ayrı terminalde backend:

```bash
cd backend
npm start
```

Manuel test adımları (beklenen görünüm dahil): **`docs/panel-manuel-test.md`**. Karar listesi: **`docs/lumos-karar-ve-uygulama-listesi.md`**.

---

**Kapsam:** Çoğu ekran mock tabanlı (`mockState`). **Akış** ekranı (`#feed`) ise doğrudan Express API **GET /posts/feed** çağırır (CORS açık); taban: `LUMOS_POSTS_API_BASE` veya `localStorage.lumos_posts_api_base`, yoksa `http://127.0.0.1:3000`. Backend: `cd backend && npm start`. Hash routing ile ekranlar arası geçiş.

**Veri katmanı:** Ekranlar doğrudan ham mock nesneleri okumaz; `getDashboardData()`, `getTasksData()`, `getSandboxData()` vb. adapter fonksiyonları normalize veri döner. Panel hâlâ mock tabanlıdır; veri akışı adapter üzerinden olduğu için gerçek backend entegrasyonu bir sonraki aşamada bu katman üzerinden kolayca eklenebilir.

**Demo senaryo sistemi:** Panel, backend olmadan farklı operasyon durumlarını göstermek için hazır demo senaryoları destekler. Üst çubukta (DEV yanında) senaryo seçici bulunur; seçim değişince tüm ekranların adapter verisi o senaryoya göre güncellenir. Senaryolar: Normal operasyon, Korumalı alan açık, Guard engelli, Config uyarı, Silinenler dolu.

**Veri sözleşmesi (tek kaynak):** Tüm ekran veri alanları `panel/js/contracts.js` içinde tek yerde tanımlıdır: `CONTRACTS` (şema), `applyContractFallbacks` (eksik alan güvenli varsayılan), stub üreticileri ve normalizer'lar. Bridge backend şeklini (snake_case) döner; fixture mapper'ları (`js/fixtures.js`) panel şekline çevirir; adapter `LC.normalize*` ile sözleşmeye hizalayıp eksik alanları doldurur. Davranış değişmez; ekranlar hep aynı contract çıktısını okur.

**Contract / stub katmanı:** Ekran bazlı veri şekilleri `js/contracts.js` içinde `CONTRACTS` ve stub üreticileri (`buildDashboardStub`, `buildSandboxStub`, …) ile tanımlıdır; adapter bu çıktıyı kullanır. Gerçek backend entegrasyonunda yalnızca mapping (API yanıtı → contract şekli) değiştirilecek; ekranlar aynı contract'ı okumaya devam eder.

**Backend veri sözleşmesi:** Ekran bazlı beklenen alanlar, zorunlu/opsiyonel ve fallback davranışı tek yerde: `BACKEND_DATA_CONTRACT.md`. Şema kaynağı `js/contracts.js` ile uyumludur.

**Backend binding map:** Gerçek entegrasyon öncesi referans için `BACKEND_BINDING_MAP.md` hazırlandı; her ekranın hangi backend kaynak adaylarına bağlanacağı ve boşluk/risk seviyeleri orada özetlenir.

**Fixture payload ve mapper:** Backend-benzeri örnek payload'lar (`js/fixtures.js` — `LumosFixtures.payloads`) ve bunları panel contract'ına çeviren mapper'lar hazır. Üst çubukta "Veri kaynağı: Demo | Fixture" seçici ile entegrasyon provası yapılabilir. Gerçek backend geldiğinde panel contract'a geçiş bu katmandan (fixture yerine API yanıtı → aynı mapper) yapılacak. Detay: `BACKEND_PAYLOAD_FIXTURES.md`.

**Milestone özeti:** Panel v1 hattı bilinçli olarak kilitlendi; sonraki adım gerçek backend entegrasyonu. Özet: `PANEL_V1_MILESTONE.md`.

**Phase 1 backend bridge:** Dashboard, Korumalı Alan ve Sistem Durumu için gerçek veri giriş noktası hazırlandı (`js/backend-bridge.js`, source provider + adapter zinciri). Gerçek veri yoksa panel fallback (demo/fixture) veriyle çalışmaya devam eder. Detay: `BACKEND_BRIDGE_PHASE1.md`.

**Phase 1 readiness:** Gerçek entegrasyon için okuma odaklı hazırlık analizi yapıldı; ilk hedef ekranlar Dashboard, Sandbox, System. Hangi alanın nereden okunabileceği ve nelerin mapping/beklemede olduğu: `BACKEND_PHASE1_READINESS.md`.

**Phase 1 read-only bridge uygulandı:** Dashboard, Korumalı Alan ve Sistem Durumu için hazır kaynak varsa (workspace_contract + consent_ok) okunuyor; `panel/scripts/read_backend_state.py --write` ile state enjekte edilebilir. Aksi halde fixture/demo fallback çalışır. Detay: `BACKEND_PHASE1_APPLIED.md`.

**Phase 1 bridge genişletmesi (Config / Identity / Keystore):** Aynı read-only hattı Config, Kimlik ve Anahtar Kasası ekranlarını da besler. `read_backend_state.py` çıktısına `config` (config_snapshot: profil, workspace_root, write_status), `identity` (identity_state, identity_guard_result vb.), `keystore` (keystore_ready, keystore_state — consent_ok ile) eklenir; backend-bridge ve app adapter bu üç ekran için backend → fixture/demo önceliğiyle çalışır. Yazım yok; salt okunur.

**Phase 1 bridge — Görevler, Silinenler, Kayıtlar:** Aynı read-only hattı Görevler, Silinenler ve Kayıtlar ekranlarına genişletildi. Kaynaklar: `base/tasks.json` (görev listesi), `base/trash` (dizin listesi), `base/logs/log.txt` (son satırlar). `read_backend_state.py` çıktısına `tasks`, `trash`, `logs` eklenir; `backend-bridge.js` ve `app.js` adapter bu üç ekran için backend → fixture → demo önceliğiyle beslenir. Yazım yok; salt okunur.

**Phase 1 tamamlanma checkpoint:** `PANEL_PHASE1_CHECKPOINT.md` — bridge ile bağlı ekranlar, bilinçli sınırlar, Phase 2 ilk adım (yalnızca System ekranında gerçek backend okuma noktaları) özetlenir.

**Phase 2 dar okuma (System):** Sistem Durumu ekranında `workspace_contract` (modül yükleme + path) ve `task_engine` (tasks.json okunabilirliği) gerçek backend'den okunuyor; diğer kartlar türetilmiş/sabit, okunamayan alanlar açık fallback ile bırakıldı. **Phase 2 genişletme:** System ekranına çözümlü path bilgileri (`system_paths`: yazım hedefi, trash, sandbox, config, logs, görevler) ve çekirdek dosya özeti (`system_summary`: config/trash/log/tasks var/yok ve sayısal sinyaller) eklendi; genel consent notu netleştirildi (Lock/presence bu hatta doğrulanmaz). Yazım yok; panel/ ve `read_backend_state.py` kapsamında.

**Phase 2 dar okuma (Görevler, Silinenler):** Görevler için `list_updated`, `list_updated_text`, `tasks_file_path` backend’den okunuyor; panelde liste son güncelleme ve dosya yolu gösterilir. Silinenler için `trash_location` çözümlenmiş path; `trash_scope_fallback_note` ile original_path/scope okunamadığında "—" fallback açıklanır.

**Phase 2 dar okuma (Kayıtlar):** Kayıtlar için `log_file_updated`, `log_updated_text` ve `log_location` (çözümlenmiş path) backend’den okunuyor; panelde son güncelleme ve dosya yolu gösterilir. Dosya yoksa null; açık fallback.

**Phase 2 dar okuma (Görevler / Silinenler / Kayıtlar) veri değeri:** Görevler: `list_updated`, `list_updated_text`, `tasks_file_path`, `task_count`, `tasks_file_exists`; Silinenler: `trash_location`, `trash_last_move`, `trash_item_count`, `trash_scope_fallback_note`; Kayıtlar: `log_file_updated`, `log_updated_text`, `log_location`, `log_line_count`, `log_file_exists`. Okunamayan alanlar açık fallback; backend write yok.

**Phase 2 checkpoint (kalıcı):** Phase 2 read-only backend hattı kalıcı checkpoint ile kapatıldı; yeni veri kaynağı açılmadı. Hangi ekranlar gerçek okuma alıyor, hangi alanlar fallback, neden dar read-only köprü ve sonraki teknik adım: `PANEL_PHASE2_CHECKPOINT.md`.

**Phase 2 dar okuma (Kimlik, Anahtar Kasası):** Kimlik ekranında `identity_state` (mevcut/mevcut değil) ve `identity_last_write` (identity.json mtime). Anahtar Kasası ekranında `keystore_last_update` (keystore.json mtime). İçerik okunmaz; sadece varlık ve mtime.

**Phase 2 dar okuma (Yapılandırma):** Yapılandırma ekranında backend’den güvenli okuma: `profil`, `workspace_root` (ENV/base), `last_activity` (config.json mtime; dosya yoksa null), `last_activity_text` (açık fallback). config.json içeriği okunmaz; sadece path ve mtime.

## Çalıştırma

- **Doğrudan:** `panel/index.html` açın (`file://`).
- **HTTP ile:** Repo kökünden `python3 -m http.server 8080` → `http://localhost:8080/panel/`
- **Yönlendirme:** `#dashboard`, `#yanit` (kartlı sonuç / örnek özet + deste kartları), `#feed`, …

## Hazır ekranlar

| Ekran           | Hash         |
|-----------------|--------------|
| Gösterge Paneli | `#dashboard` |
| Kartlı sonuç    | `#yanit`     |
| Akış            | `#feed`      |
| Görevler        | `#tasks`     |
| Korumalı Alan   | `#sandbox`   |
| Yapılandırma    | `#config`    |
| Kimlik          | `#identity`  |
| Anahtar Kasası  | `#keystore`  |
| Silinenler      | `#trash`     |
| Kayıtlar        | `#logs`      |
| Sistem Durumu   | `#system`    |

Ortak bileşenler: Sidebar, Topbar, StatusBadge, MetricCard, SectionCard, EmptyState, EventList, DetailPanel, ViewHeader. Detay ve mock state yapısı için `js/app.js` ve `css/app.css` kaynak dosyalarına bakın.

---

## Mevcut kapsam / bilinçli sınırlar / çalıştırma

- **Kapsam:** Tüm veri mock/stub ile; hash routing ile ekran geçişi. Backend, auth, WebSocket yok.
- **Bilinçli sınırlar:** Canlı API, yeni ekran veya büyük modül bu sürümde açılmaz; sadece mock tabanlı operatör görünümü.
- **Adapter / contract:** Ekran verisi contract şemasına göre; stub üreticileri (`buildXxxStub`) state → contract şekli, normalizer'lar eksik alanları güvenli varsayılana çeker. Ekranlar `getXxxData()` çıktısından beslenir. Gerçek backend entegrasyonunda sadece mapping katmanı (API → contract) değiştirilecek; contract referans alınacak.
- **Çalıştırma:** `panel/index.html` doğrudan açılır veya repo kökünden `python3 -m http.server 8080` ile `http://localhost:8080/panel/`. Hash listesi: hazır ekranlar tablosu (`#yanit` katmanlı yanıt örneği).

---

## E2E (legacy kalite kapısı)

> **Legacy:** Birincil üretim yüzeyi `ui/` (Astro `/panel`) — bkz. OD-043. Bu dizindeki Playwright E2E (`panel/e2e/`) **legacy statik panel** kalite kapısıdır; üretim `/panel` doğrulaması değildir (OD-046).

| Komut (kök) | Hedef | Not |
|-------------|-------|-----|
| `npm run e2e:package` | `ui/dist` → `/panel` | OD-046 birincil package kapısı (Faz 4) |
| `npm run e2e:package:api` | `ui/dist` + `panel_tasks_server` | API package kapısı |
| `npm run e2e:tasks-offline-online` | `ui/dist` + offline/online geçişi | Görev API dayanıklılık kapısı |
| `npm run e2e:smoke:ui` | `ui/dist` → `/panel` | OD-046 v1/v2 smoke (üretim yüzeyi) |
| `npm run e2e:legacy:package` | `panel/index.html` statik | Legacy paket kapısı (geçiş dönemi) |
| `npm run e2e:legacy:package:api` | panel + `panel_tasks_server` | Legacy API kapısı |
| `npm run e2e:legacy:tasks-offline-online` | panel + offline/online | Legacy offline/online kapısı |

CI: `ui-smoke` (hızlı varlık) + `ui-e2e` (package trio) — `.github/workflows/ci.yml`.

Legacy E2E ayrıntıları: `panel/e2e/run-package.mjs`. UI E2E: `ui/e2e/package-local.mjs`, `ui/e2e/smoke-panel.mjs`.
