# Lumos Panel v1

**Kapsam:** Mock tabanlı operatör paneli. Backend veya canlı API yok; tüm veri `js/app.js` içindeki `mockState` ile beslenir. Hash routing ile tek sayfada ekranlar arası geçiş yapılır.

**Veri katmanı:** Ekranlar doğrudan ham mock nesneleri okumaz; `getDashboardData()`, `getTasksData()`, `getSandboxData()` vb. adapter fonksiyonları normalize veri döner. Panel hâlâ mock tabanlıdır; veri akışı adapter üzerinden olduğu için gerçek backend entegrasyonu bir sonraki aşamada bu katman üzerinden kolayca eklenebilir.

**Demo senaryo sistemi:** Panel, backend olmadan farklı operasyon durumlarını göstermek için hazır demo senaryoları destekler. Üst çubukta (DEV yanında) senaryo seçici bulunur; seçim değişince tüm ekranların adapter verisi o senaryoya göre güncellenir. Senaryolar: Normal operasyon, Korumalı alan açık, Guard engelli, Config uyarı, Silinenler dolu.

**Contract / stub katmanı:** Panel hâlâ mock/stub tabanlıdır. Ekran bazlı veri şekilleri `CONTRACTS` ve stub üreticileri (`buildDashboardStub`, `buildTasksStub`, vb.) ile tek yerde tanımlıdır; adapter bu contract çıktısını kullanır ve hafif normalizasyon (eksik metrics/badges/detail için güvenli varsayılan) uygular. Gerçek backend entegrasyonunda yalnızca bu katmandaki mapping (stub yerine API yanıtı → contract şekli) değiştirilecek; ekranlar aynı contract'ı okumaya devam eder.

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
