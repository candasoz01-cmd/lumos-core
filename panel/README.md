# Lumos Panel v1

**Kapsam:** Mock tabanlı operatör paneli. Backend veya canlı API yok; tüm veri `js/app.js` içindeki `mockState` ile beslenir. Hash routing ile tek sayfada ekranlar arası geçiş yapılır.

**Veri katmanı:** Ekranlar doğrudan ham mock nesneleri okumaz; `getDashboardData()`, `getTasksData()`, `getSandboxData()` vb. adapter fonksiyonları normalize veri döner. Panel hâlâ mock tabanlıdır; veri akışı adapter üzerinden olduğu için gerçek backend entegrasyonu bir sonraki aşamada bu katman üzerinden kolayca eklenebilir.

**Demo senaryo sistemi:** Panel, backend olmadan farklı operasyon durumlarını göstermek için hazır demo senaryoları destekler. Üst çubukta (DEV yanında) senaryo seçici bulunur; seçim değişince tüm ekranların adapter verisi o senaryoya göre güncellenir. Senaryolar: Normal operasyon, Korumalı alan açık, Guard engelli, Config uyarı, Silinenler dolu.

**Veri sözleşmesi (tek kaynak):** Tüm ekran veri alanları `panel/js/contracts.js` içinde tek yerde tanımlıdır: `CONTRACTS` (şema), `applyContractFallbacks` (eksik alan güvenli varsayılan), stub üreticileri ve normalizer'lar. Bridge backend şeklini (snake_case) döner; fixture mapper'ları (`js/fixtures.js`) panel şekline çevirir; adapter `LC.normalize*` ile sözleşmeye hizalayıp eksik alanları doldurur. Davranış değişmez; ekranlar hep aynı contract çıktısını okur.

**Contract / stub katmanı:** Ekran bazlı veri şekilleri `js/contracts.js` içinde `CONTRACTS` ve stub üreticileri (`buildDashboardStub`, `buildSandboxStub`, …) ile tanımlıdır; adapter bu çıktıyı kullanır. Gerçek backend entegrasyonunda yalnızca mapping (API yanıtı → contract şekli) değiştirilecek; ekranlar aynı contract'ı okumaya devam eder.

**Backend binding map:** Gerçek entegrasyon öncesi referans için `BACKEND_BINDING_MAP.md` hazırlandı; her ekranın hangi backend kaynak adaylarına bağlanacağı ve boşluk/risk seviyeleri orada özetlenir.

**Fixture payload ve mapper:** Backend-benzeri örnek payload'lar (`js/fixtures.js` — `LumosFixtures.payloads`) ve bunları panel contract'ına çeviren mapper'lar hazır. Üst çubukta "Veri kaynağı: Demo | Fixture" seçici ile entegrasyon provası yapılabilir. Gerçek backend geldiğinde panel contract'a geçiş bu katmandan (fixture yerine API yanıtı → aynı mapper) yapılacak. Detay: `BACKEND_PAYLOAD_FIXTURES.md`.

**Milestone özeti:** Panel v1 hattı bilinçli olarak kilitlendi; sonraki adım gerçek backend entegrasyonu. Özet: `PANEL_V1_MILESTONE.md`.

**Phase 1 backend bridge:** Dashboard, Korumalı Alan ve Sistem Durumu için gerçek veri giriş noktası hazırlandı (`js/backend-bridge.js`, source provider + adapter zinciri). Gerçek veri yoksa panel fallback (demo/fixture) veriyle çalışmaya devam eder. Detay: `BACKEND_BRIDGE_PHASE1.md`.

**Phase 1 readiness:** Gerçek entegrasyon için okuma odaklı hazırlık analizi yapıldı; ilk hedef ekranlar Dashboard, Sandbox, System. Hangi alanın nereden okunabileceği ve nelerin mapping/beklemede olduğu: `BACKEND_PHASE1_READINESS.md`.

**Phase 1 read-only bridge uygulandı:** Dashboard, Korumalı Alan ve Sistem Durumu için hazır kaynak varsa (workspace_contract + consent_ok) okunuyor; `panel/scripts/read_backend_state.py --write` ile state enjekte edilebilir. Aksi halde fixture/demo fallback çalışır. Detay: `BACKEND_PHASE1_APPLIED.md`.

**Phase 1 bridge genişletmesi (Config / Identity / Keystore):** Aynı read-only hattı Config, Kimlik ve Anahtar Kasası ekranlarını da besler. `read_backend_state.py` çıktısına `config` (config_snapshot: profil, workspace_root, write_status), `identity` (identity_state, identity_guard_result vb.), `keystore` (keystore_ready, keystore_state — consent_ok ile) eklenir; backend-bridge ve app adapter bu üç ekran için backend → fixture/demo önceliğiyle çalışır. Yazım yok; salt okunur.

**Phase 1 bridge — Görevler, Silinenler, Kayıtlar:** Aynı read-only hattı Görevler, Silinenler ve Kayıtlar ekranlarına genişletildi. Kaynaklar: `base/tasks.json` (görev listesi), `base/trash` (dizin listesi), `base/logs/log.txt` (son satırlar). `read_backend_state.py` çıktısına `tasks`, `trash`, `logs` eklenir; `backend-bridge.js` ve `app.js` adapter bu üç ekran için backend → fixture → demo önceliğiyle beslenir. Yazım yok; salt okunur.

**Phase 1 tamamlanma checkpoint:** `PANEL_PHASE1_CHECKPOINT.md` — bridge ile bağlı ekranlar, bilinçli sınırlar, Phase 2 ilk adım (yalnızca System ekranında gerçek backend okuma noktaları) özetlenir.

**Phase 2 dar okuma (System):** Sistem Durumu ekranında `workspace_contract` (modül yükleme + path) ve `task_engine` (tasks.json okunabilirliği) gerçek backend'den okunuyor; diğer kartlar türetilmiş/sabit, okunamayan alanlar açık fallback ile bırakıldı. Yazım yok; panel/ ve `read_backend_state.py` kapsamında.

**Phase 2 dar okuma (Görevler, Silinenler):** Görevler için `list_updated` (tasks.json mtime) backend’den okunuyor, panelde "Liste son güncelleme" gösterilir. Silinenler için `trash_location` çözümlenmiş (absolute) path; original_path/scope okunamadığı için "—" fallback bırakıldı.

## Çalıştırma

- **Doğrudan:** `panel/index.html` açın (`file://`).
- **HTTP ile:** Repo kökünden `python3 -m http.server 8080` → `http://localhost:8080/panel/`
- **Yönlendirme:** `#dashboard`, `#tasks`, `#sandbox`, `#config`, `#identity`, `#keystore`, `#trash`, `#logs`, `#system`

## Hazır ekranlar

| Ekran           | Hash         |
|-----------------|--------------|
| Gösterge Paneli | `#dashboard` |
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
- **Çalıştırma:** `panel/index.html` doğrudan açılır veya repo kökünden `python3 -m http.server 8080` ile `http://localhost:8080/panel/`. Hash: `#dashboard`, `#tasks`, `#sandbox`, `#config`, `#identity`, `#keystore`, `#trash`, `#logs`, `#system`.
