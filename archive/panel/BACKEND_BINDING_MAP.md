# Panel – Backend Binding Map

**Amaç:** Gerçek backend entegrasyonuna geçmeden önce, her panel ekranının hangi backend veri/kaynak adaylarına bağlanacağını netleştiren teknik köprü planı. Bu belge sadece harita; fetch/API/kod entegrasyonu yok.

**Kapsam:** panel/ altında doküman; backend dosyalarında değişiklik yok.

---

## 1. Ekran bazlı binding map

### Dashboard (Gösterge Paneli)

| Başlık | İçerik |
|--------|--------|
| **Panelde beklenen veri alanları** | `title`, `subtitle`, `metrics` (Korumalı Alan Durumu, Yazım Hedefi, Koruma Durumu, Son Aktivite), `sections` (Son Olaylar = events, Uyarılar = warnings, Hızlı geçişler = links). |
| **Backend'de olası kaynak/modül** | Sandbox durumu: `workspace_contract.writing_base_dir` / sandbox modu bayrağı; guard durumu: guard/engine çıktısı; son olaylar: log/presence veya event akışı; uyarılar: config/guard uyarı toplayıcı. |
| **Araya girecek adapter/mapping notu** | Tek response’ta birleştirme: sandbox + guard + son N olay + uyarı listesi → `metrics` + `sections[].events` / `sections[].warnings`. Tarih alanları `formatTime` ile panel formatına. |
| **Belirsiz kalan alanlar** | “Son aktivite”nin tek kaynağı (log mu, presence mi, task last_run mu) henüz net değil. |
| **Entegrasyon riski seviyesi** | **Orta** — birden fazla kaynaktan toplulaştırma gerekir. |

---

### Sandbox (Korumalı Alan)

| Başlık | İçerik |
|--------|--------|
| **Panelde beklenen veri alanları** | `title`, `subtitle`, `metrics` (Kaynak, Sandbox Base, Yazım Yönü, Sözleşme Durumu), `sections` (metin blokları: Çözümleme Mantığı, Guard Kuralı, Canlı/sandbox farkı). |
| **Backend'de olası kaynak/modül** | `core/workspace_contract`: `sandbox_base_path(live_base)`, `writing_base_dir(live_base, is_sandbox_mode)`, `LUMOS_SANDBOX_DIRNAME`. Sandbox modunun kaynağı: CLI/ENV/varsayılan çözümleyici (sandbox_mode kaynağı). |
| **Araya girecek adapter/mapping notu** | `is_sandbox_mode` + `live_base` → metrics değerleri ve “Yazım Yönü”. Sections statik/metin kalabilir veya backend’den tek metin alanı. |
| **Belirsiz kalan alanlar** | Sandbox “kaynak” (CLI/ENV/varsayılan) bilgisinin backend’de nerede tutulduğu. |
| **Entegrasyon riski seviyesi** | **Düşük** — workspace_contract ile doğrudan eşleşir; tek eksik kaynak bilgisi. |

---

### Config (Yapılandırma)

| Başlık | İçerik |
|--------|--------|
| **Panelde beklenen veri alanları** | `title`, `subtitle`, `metrics` (Mevcut Yapılandırma Özeti, Yazım Durumu, Son Config Aktivitesi), `sections` (Sink/Guard hattı metni). |
| **Backend'de olası kaynak/modül** | `core/config`: config okuma/yazım; config write/sink hattı (yazım durumu, hedef kontrolü); son config aktivitesi için log veya config mtime/metadata. |
| **Araya girecek adapter/mapping notu** | Config özeti (profil, workspace_root) + write status + son aktivite metni → `metrics`. Sections statik veya backend’den tek metin. |
| **Belirsiz kalan alanlar** | “Yazım durumu” ve “son config aktivitesi” için tek API/alan adı. |
| **Entegrasyon riski seviyesi** | **Orta** — config okuma net; sink/guard tarafı ve “son aktivite” netleşmeli. |

---

### Identity (Kimlik)

| Başlık | İçerik |
|--------|--------|
| **Panelde beklenen veri alanları** | `title`, `subtitle`, `metrics` (Kimlik hazır mı, Son Yazım, Hedef Kapsam, Guard Sonucu), `sections` (Sink/Guard bağlantısı metni). |
| **Backend'de olası kaynak/modül** | `security/identity`: kimlik durumu, hedef kapsam; identity sink/guard (yazım kapsamı, guard sonucu); son yazım zamanı (metadata veya log). |
| **Araya girecek adapter/mapping notu** | Identity durum + son yazım + kapsam + guard sonucu → `metrics`. Hassas alan (kimlik içeriği) panelde gösterilmez; sadece durum. |
| **Belirsiz kalan alanlar** | “Son yazım” ve “guard sonucu” için ortak endpoint/alan. |
| **Entegrasyon riski seviyesi** | **Orta** — güvenlik sınırı nedeniyle sadece durum alanları açılacak; kaynak netleşmeli. |

---

### Keystore (Anahtar Kasası)

| Başlık | İçerik |
|--------|--------|
| **Panelde beklenen veri alanları** | `title`, `subtitle`, `metrics` (Hazır mı, Şifreli Durum, Son Güncelleme, Yazım Kapsamı), `sections` (Görünürlük ilkesi metni). |
| **Backend'de olası kaynak/modül** | `security/keystore`: kilit durumu (locked/unlocked), hazır bayrağı; keystore sink (yazım kapsamı); son güncelleme (metadata). Anahtar/passphrase asla panelde açılmaz. |
| **Araya girecek adapter/mapping notu** | Sadece durum alanları → `metrics`. Sections statik. |
| **Belirsiz kalan alanlar** | “Son güncelleme” ve “yazım kapsamı” için tek kaynak. |
| **Entegrasyon riski seviyesi** | **Yüksek** — hassas veri sızması riski; yalnızca durum API’si kullanılmalı. |

---

### Trash (Silinenler)

| Başlık | İçerik |
|--------|--------|
| **Panelde beklenen veri alanları** | `title`, `subtitle`, `summaryMetrics` (Çöp Konumu, Son Taşıma, Öğe Sayısı, Kapsam), `listItems` (id, name, originalPath, trashPath, movedAt, scope), `selectedId`, `selectedItem`, `detailTitle`, empty state alanları. |
| **Backend'de olası kaynak/modül** | `core/workspace_contract`: `trash_path(base)`, `LUMOS_TRASH_DIRNAME`; trash akışı: taşınan öğe listesi (FS taraması veya manifest). Son taşıma: en son movedAt veya dizin metadata. |
| **Araya girecek adapter/mapping notu** | Trash dizin yolu + liste (manifest veya FS) → `summaryMetrics` + `listItems`. `movedAt`/scope backend’den veya dosya metadata’dan. |
| **Belirsiz kalan alanlar** | Liste kaynağı: sadece FS listesi mi yoksa ayrı trash manifest/DB. |
| **Entegrasyon riski seviyesi** | **Orta** — path sözleşmesi net; liste ve metadata kaynağı netleşmeli. |

---

### Logs (Kayıtlar)

| Başlık | İçerik |
|--------|--------|
| **Panelde beklenen veri alanları** | `title`, `subtitle`, `filters`, `activeFilter`, `events` (id, kind, text, ts), `sectionTitle`. |
| **Backend'de olası kaynak/modül** | Log/presence hattı: `core/logfmt`, logs dizini; presence/event akışı. Kind: görev, sandbox, config, trash, identity, keystore, guard. |
| **Araya girecek adapter/mapping notu** | Son N log satırı veya event stream → `events`. Filtre panelde (kind); backend’den tümü veya kind parametreli. |
| **Belirsiz kalan alanlar** | Tekil log API mi, dosya tail mi, presence event stream mi. |
| **Entegrasyon riski seviyesi** | **Orta** — format (kind, text, ts) backend ile uyumlu olmalı; kaynak seçimi netleşmeli. |

---

### Tasks (Görevler)

| Başlık | İçerik |
|--------|--------|
| **Panelde beklenen veri alanları** | `title`, `subtitle`, `filters`, `activeFilter`, `listItems` (id, title, status, updated, lastRun, guardResult, outputSummary), `selectedId`, `selectedTask`, empty/detail/runNote alanları. |
| **Backend'de olası kaynak/modül** | `task_engine`: görev listesi (engine/store); status, lastRun, guardResult, outputSummary task engine ve guard çıktısından. |
| **Araya girecek adapter/mapping notu** | Task list + her görev için guard sonucu ve çıktı özeti → `listItems`. Filtre panelde (status); backend’den tümü veya filtreli. |
| **Belirsiz kalan alanlar** | `outputSummary` ve `guardResult`’ın task engine’de nerede tutulduğu. |
| **Entegrasyon riski seviyesi** | **Orta** — task listesi net; detay ve guard alanları eşleşmeli. |

---

### System (Sistem Durumu)

| Başlık | İçerik |
|--------|--------|
| **Panelde beklenen veri alanları** | `title`, `subtitle`, `healthCards` (title, status, note) — workspace_contract, task_engine, sandbox_source, trash_contract, config_sink, identity_sink, keystore_sink, general. |
| **Backend'de olası kaynak/modül** | `core/startup_health`: get_startup_summary benzeri; sistem durumu/health benzeri durum alanları (workspace sözleşmesi yüklü mü, task engine çalışıyor mu, sandbox kaynağı, trash, config/identity/keystore sink, genel özet). |
| **Araya girecek adapter/mapping notu** | Health/summary yapısı → `healthCards` (sabit başlıklar: Workspace Sözleşmesi, Görev Motoru, …). status: ok/uyarı/hata; note: kısa açıklama. |
| **Belirsiz kalan alanlar** | Paneldeki 8+1 kartın tam olarak hangi backend kontrollerine karşılık geleceği. |
| **Entegrasyon riski seviyesi** | **Orta** — startup_health ve benzeri genişletilebilir; kart listesi sabit, backend tarafı netleşmeli. |

---

## 2. Mevcut backend omurgası – bağ adayları

Aşağıdaki modüller/alanlar, panel binding için **aday** olarak referans alınabilir. Backend dosyalarında değişiklik yapılmadan sadece bağ haritası için kullanılır.

| Aday | Konum / not |
|------|-------------|
| **workspace_contract** | `src/core/workspace_contract.py` — `trash_path()`, `sandbox_base_path()`, `writing_base_dir()`, `LUMOS_TRASH_DIRNAME`, `LUMOS_SANDBOX_DIRNAME`, `CORE_STATE_PATH_NAMES`. Dashboard (yazım hedefi), Sandbox, Trash (path), System (çekirdek path referansı). |
| **Sandbox mode kaynağı** | Sandbox modunun (is_sandbox_mode) ve kaynak (CLI/ENV/varsayılan) bilgisinin sağlandığı yer; engine veya CLI/state. |
| **Config write/sink hattı** | `core/config` ve config yazımı; yazım durumu, hedef kontrolü. Config ekranı. |
| **Identity** | `security/identity.py` — kimlik durumu, hedef kapsam; identity sink/guard. |
| **Keystore** | `security/keystore.py` — kilit durumu, hazır bayrağı; keystore sink; hassas veri panelde yok. |
| **Trash akışı** | `workspace_contract.trash_path`; silinen öğe listesi (FS veya manifest). |
| **Task engine / task store** | `task_engine/engine.py`, task listesi, status, guard sonucu, çıktı özeti. |
| **Log / presence hattı** | `core/logfmt`, logs dizini, `security/presence_*`; olay akışı, kind/text/ts. |
| **System/health benzeri** | `core/startup_health.py` — get_startup_summary; consent, lock, presence; genişletilerek healthCards kaynağı olabilir. |

---

## 3. Contract ↔ Backend boşluk matrisi

| Durum | Açıklama | Örnek |
|-------|----------|--------|
| **Panel contract’ta var, backend’de henüz net kaynak yok** | Panel alanı tanımlı; backend’de tek karşılık veya API adı belirsiz. | “Son aktivite” (Dashboard), “Sandbox kaynak” (Sandbox), “Son yazım” (Identity), “Son güncelleme” (Keystore), trash list manifest, log event API. |
| **Backend’de var, panelde henüz gösterilmiyor** | Backend’de veri/alan var; panel contract’ta yer yok veya ekran yok. | consent, presence ayrıntısı, macOS izinleri detayı (startup_health). |
| **Doğrudan bağlanır** | Tek kaynak, minimal mapping. | Sandbox: `writing_base_dir`, `sandbox_base_path`; Trash: `trash_path`, `LUMOS_TRASH_DIRNAME`; System: health kartları ↔ startup_health genişletilmiş çıktı. |
| **Mapping gerekir** | Backend alan adı / formatı panel contract’tan farklı; adapter’da dönüşüm. | Tüm tarih alanları → panel `formatTime`; status değerleri → badge variant; guard sonucu metni → metrics. |
| **Toplulaştırma gerekir** | Birden fazla backend kaynağı tek ekran verisine birleştirilir. | Dashboard: sandbox + guard + olaylar + uyarılar; System: birden fazla health kontrolü → healthCards. |

---

## 4. Kullanım

- Gerçek backend entegrasyonu yapılırken bu belge **referans** alınacak.
- Her ekran için “Panelde beklenen veri alanları” = panel contract (`js/contracts.js` CONTRACTS) ile uyumlu tutulacak.
- Adapter/mapping notları, ileride API yanıtı → contract şeklini uygulayacak katmanda kullanılacak.
- Belirsiz alanlar ve risk seviyeleri, entegrasyon sırasında önceliklendirme için kullanılabilir.
