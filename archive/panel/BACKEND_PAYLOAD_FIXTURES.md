# Backend Payload Fixtures ve Mapper Katmanı

**Amaç:** Gerçek backend entegrasyonu yapılmadan önce, backend’den gelebilecek örnek ham payload şekillerini fixture olarak tanımlamak ve bunları panel contract’ına map eden katmanı kurmak. Entegrasyon provası için kullanılır; fetch/canlı veri yok.

---

## Fixture neyi temsil ediyor?

- **Fixture:** Backend-benzeri ham veri örneği. Alan adları ve yapı, gerçek API yanıtına benzeyecek şekilde tasarlanır (ör. `snake_case`, `recent_events`, `writing_base_dir`, `config_snapshot`).
- Panel contract’ından **farklı** olabilir: contract ekranın beklediği normalize şekil (title, subtitle, metrics, sections, listItems vb.); fixture ise “API’den gelen” ham şekil.
- `js/fixtures.js` içinde `LumosFixtures.payloads` (dashboard, sandbox, config, identity, keystore, trash, logs, tasks, system) tanımlıdır.

---

## Contract ile farkı ne?

| | Fixture (backend-benzeri) | Contract (panel beklediği) |
|--|---------------------------|----------------------------|
| **Kaynak** | Simüle API yanıtı | Ekranın okuduğu normalize veri |
| **Alan adları** | snake_case, backend terimleri | title, subtitle, metrics, sections, listItems, vb. |
| **Yapı** | Örn. `recent_events`, `config_snapshot`, `trash_items` | Örn. `sections[].events`, `metrics[]`, `listItems[]` |
| **Kullanım** | Mapper girişi | Adapter çıktısı; ekranlar bunu okur |

---

## Mapper neden var?

- Backend’den gelen ham payload, panel contract’ına **dönüştürülmeli**; ekranlar contract’ı okur, ham API şeklini okumaz.
- **Mapper:** `mapDashboardPayloadToPanelData(payload)` vb. — fixture (veya ileride gerçek API yanıtı) → contract şekli.
- Eksik alanlarda **güvenli fallback:** eksik metrics → boş liste, eksik detail → null (EmptyState), eksik listItems → boş dizi, eksik badge → boş/atlanır. Panel kırılmaz.

---

## Gerçek entegrasyonda hangi katman değişecek?

- **Şu an:** Adapter ya stub (demo senaryo) ya da fixture + mapper kullanıyor; veri kaynağı “Demo” / “Fixture” seçici ile seçilir.
- **Gerçek backend geldiğinde:** Aynı contract korunur. Değişecek tek yer: adapter’da “veri kaynağı” artık stub/fixture yerine **API yanıtı** olur; API yanıtı yine aynı mapper’lara (veya mapper mantığının taşındığı tek bir mapping katmanına) beslenir. Yani:
  - `getDashboardData()` örn. `fetch('/api/dashboard')` → gelen payload → `mapDashboardPayloadToPanelData(payload)` → `normalizeDashboard(..., {})` → ekran aynı contract’ı okur.
- Fixture’lar ve mapper’lar, bu geçişte **referans ve provası** olarak kullanılacak; gerçek entegrasyonda panel contract’a geçiş bu katmandan yapılacak.
