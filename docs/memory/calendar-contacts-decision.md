# Takvim ve kişiler — onaylı karar (OD-032)

> **Durum:** `decision-approved` — ilke kararları onaylandı; **uygulama başlamadı** (`implementation-pending`). Bu belge kod değişikliği değildir.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`external-integrations-permissions.md`](./external-integrations-permissions.md), [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md), [`commercial-approval-model-decision.md`](./commercial-approval-model-decision.md), [`computer-use-permission-gate-decision.md`](./computer-use-permission-gate-decision.md), [`vault-secret-token-decision.md`](./vault-secret-token-decision.md), [`security-architecture.md`](./security-architecture.md), [`product-rules.md`](./product-rules.md), [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

**Kaynak OD:** OD-032 (`external-integrations-permissions.md` — Takvim + Kişiler)

---

## Kapsam sınırı (firm)

| Dahil (OD-032) | Hariç — ayrı karar (OD-033) |
|----------------|------------------------------|
| **Takvim** — okuma, toplantı oluşturma, taşıma, iptal, RSVP, kullanıcı adına planlama | GitHub, Slack, Linear, Notion, Google Drive, Asana vb. **çalışma araçları** connector'ları |
| **Kişiler** — bulma, ilişkilendirme, iletişim geçmişi bağlama, kişi bazlı kurallar | Mail / mesaj kanalları otomasyonu — [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) (OD-031) |
| İzin paketi, onay omurgası, vault/credential ilkesi | Provider seçimi (Google Calendar, iCal, CalDAV, Apple Contacts vb.) — `implementation-pending` |
| OD-031 kişi bazlı kural modeli ile çapraz referans | Connector kodu, sync, onay UX wireframe |

**Firm:** Takvim, kişiler ve çalışma araçları **tek karar dosyasında birleştirilmez**. OD-032 yalnızca **Takvim + Kişiler**; OD-033 yalnızca **platform connector / çalışma araçları** değerlendirme listesidir.

---

## Amaç

OD-032 kapsamında **takvim** ve **kişiler (contacts)** entegrasyonunun ürün davranış ilkesini, izin seviyelerini ve onay omurgasını netleştirmek.

Bu belge:

- Kullanıcı yetkilendirmesi dahilinde takvim ve kişi yeteneklerini **granüler izin paketi** ile tanımlar.
- OD-031 (iletişim kanalları / kişi bazlı kurallar), OD-041 (hibrit onay), OD-012 (Computer Use / dış etki kapısı) ve `product-rules.md` ile **aynı omurgayı** paylaşır.
- Entegrasyon **yöntemine kilitlenmez** — resmi API, yerel/OS bağlayıcı, CalDAV, Computer Use vb. aynı izin ve onay katmanları altında değerlendirilir.
- Vault/credential modeli (OD-001/002) ve public repo sınırı ile hizalanır.

**Uygulama notu:** İlke kararları onaylandı; kod, test, connector, provider entegrasyonu, onay UX veya otomasyon yapılandırması **henüz başlamadı**.

---

## Onaylanan ilke vs bekleyen uygulama

| Katman | Durum | Kapsam |
|--------|--------|--------|
| **İlke kararları** | `decision-approved` | TC1–TC9; granüler izin tabloları (`cal_*`, `contact_*`); OD-031 kişi kuralı omurgası; OD-041/OD-012 hibrit onay; vault ilkesi (OD-001/002); varsayılan pasif; entegrasyon yöntemi ikincil; çalışma araçları kapsam dışı (OD-033). |
| **Uygulama / teknik detay** | `implementation-pending` | Provider seçimi (Google Calendar, iCal, CalDAV, kişi kaynağı); connector/bridge; vault credential şeması; onay UX ve kural editörü; sync/push-poll; `cal_plan` algoritması; Computer Use takvim senaryosu. Hiçbiri uygulanmadı; bu belge uygulama izni vermez. |
| **Needs-review (açık alt detay)** | `needs-review` | Paylaşılan takvim/delegasyon; davetiye vs blok oluşturma; mail (OD-031) birleşik kural önceliği; saat dilimi/tekrarlayan etkinlik edge case'leri. |

---

## Çekirdek çerçeve

**Lumos, kullanıcının kontrollü dijital uzantısıdır.** Takvim ve kişiler alanında kullanıcı adına hareket edebilir; ancak yalnızca:

1. **Kullanıcının açık isteği veya tanımlı kuralı**
2. **Verilmiş izin paketi** (granüler, geri alınabilir, denetlenebilir)
3. **Çekirdek güvenlik ve ürün kuralları** ([`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`product-rules.md`](./product-rules.md), OD-012, OD-041)

Lumos **kendi kendine tam takvim veya adres defteri yetkisi üstlenmez**; izin paketi ve kurallar olmadan okuma, yazma, planlama veya kişi eşleştirme yapmaz.

**Entegrasyon yöntemi ikincildir:** Bkz. [`external-integrations-permissions.md`](./external-integrations-permissions.md) §Entegrasyon felsefesi — amaç kullanıcının yetki verdiği kapsamda takvim/kişi sistemini kullanabilmektir; yöntem seçimi provider/platform bazlı uygulama kararıdır.

---

## Takvim — yetenekler (firm)

Kullanıcı açık izin paketi ve tanımlı kurallar dahilinde Lumos takvimde şunları yapabilir:

| # | Yetenek | Açıklama |
|---|---------|----------|
| T1 | **Okuma** | Takvim görüntüleme, etkinlik listeleme, müsaitlik/doluluk okuma |
| T2 | **Toplantı oluşturma** | Yeni etkinlik / toplantı oluşturma (katılımcı, süre, konum — kapsam grant'ına bağlı) |
| T3 | **Toplantı taşıma** | Etkinliği yeniden zamanlama / reschedule |
| T4 | **Toplantı iptali** | Etkinliği iptal etme (organizatör veya yetki kapsamında) |
| T5 | **Katılım yanıtı (RSVP)** | Kabul / red / belki yanıtı verme |
| T6 | **Kullanıcı adına planlama** | Müsaitlik ve kullanıcı tercihlerine göre toplantı önerme veya oluşturma — **açık `plan` izni** ve kurallar sınırları içinde |

**Firm:** T2–T6 **dış etkili takvim aksiyonlarıdır**; oturum izni tek başına yetmez — bkz. §Hibrit onay modeli.

---

## Kişiler — yetenekler (firm)

Kullanıcı açık izin paketi ve tanımlı kurallar dahilinde Lumos kişiler alanında şunları yapabilir:

| # | Yetenek | Açıklama |
|---|---------|----------|
| C1 | **Kişi bulma** | Ad, e-posta, telefon veya bağlam ile kişi arama / eşleştirme |
| C2 | **İlişkilendirme** | Kişiyi görev, proje, iletişim kanalı veya Lumos bağlamına bağlama |
| C3 | **İletişim geçmişi bağlama** | Kişi ile mail/mesaj/takvim kayıtlarını **provenance ile** ilişkilendirme (ham içerik gereksiz kalıcı yüzeyde tutulmaz) |
| C4 | **Kişi bazlı kurallar** | Belirli kişi(ler) için otomasyon kuralı çalıştırma — **OD-031 kural modeli** ile aynı omurga; takvim/kişi alanına özgü tetikleyiciler eklenebilir |

**Firm:** C2–C4 yazma veya dış etki içerebilir; C3 okuma + ilişki yazımı birleşik izin gerektirir. Kişi bazlı kurallar (C4) **mail (OD-031) ile aynı kural boyutlarını** (kişi, kaynak, konu, içerik, görev, önem) paylaşır; kanal/takvim tetikleyicisi ayrı grant ile tanımlanır.

---

## Firm ilkeler

| # | İlke | Durum |
|---|------|--------|
| TC1 | **Varsayılan pasif:** İzin olmadan takvim okuma, kişi arama veya dış etki yok. | `decision-approved` |
| TC2 | **Granüler izin paketi:** Geri alınabilir, daraltılabilir, denetlenebilir; üst seviye alt seviyeyi otomatik kapsamaz. | `decision-approved` |
| TC3 | **Dış etkili takvim aksiyonu** (oluştur, taşı, iptal, RSVP, plan) oturum izninden **türemez** — kural-kapsamlı grant veya işlem bazlı onay. | `decision-approved` |
| TC4 | **Kişi bazlı kurallar** OD-031 ile aynı opt-in, revoke ve çakışma ilkelerini paylaşır. | `decision-approved` |
| TC5 | **Kalıcı silme asla otomatik değil** — etkinlik/kişi kaydı kalıcı silme kullanıcı açık komutu + tek satır uyarı. | `decision-approved` |
| TC6 | **Credential Lumos yüzeyinde değil** — vault/kasa (OD-001/002). | `decision-approved` |
| TC7 | **İçerik public repo, gereksiz log ve kalıcı bellekte değil** — minimum tutma, provenance. | `decision-approved` |
| TC8 | **Sessiz onay yok;** varsayılan-onay yok; carry-forward yok — OD-041 CA4. | `decision-approved` |
| TC9 | **Çalışma araçları bu belge kapsamında değil** — OD-033. | `decision-approved` |

---

## İzin seviyeleri — Takvim

| Seviye | Kod | Etki | Varsayılan | Onay modeli |
|--------|-----|------|------------|-------------|
| **Okuma** | `cal_read` | Etkinlik listeleme, müsaitlik okuma, hatırlatma görüntüleme | Kapalı | Oturum + takvim/kapsam (OD-041 CA1) |
| **Bildirim** | `cal_notify` | Takvim değişikliği / yaklaşan etkinlik bildirimi | Kapalı | Oturum + kapsam |
| **Oluşturma** | `cal_create` | Yeni etkinlik / toplantı oluşturma | Kapalı | **İşlem bazlı veya kural-kapsamlı açık izin** |
| **Güncelleme / taşıma** | `cal_update` | Reschedule, süre/konum/katılımcı değişikliği | Kapalı | İşlem veya kural-kapsamlı izin |
| **İptal** | `cal_cancel` | Etkinlik iptali | Kapalı | **İşlem bazlı açık onay** (yüksek etki) |
| **RSVP** | `cal_rsvp` | Katılım yanıtı (kabul/red/belki) | Kapalı | İşlem veya kural-kapsamlı izin |
| **Planlama** | `cal_plan` | Kullanıcı adına müsaitlik analizi + toplantı önerme/oluşturma | Kapalı | **Açık `cal_plan` grant +** oluşturma için `cal_create` (veya kural-kapsamlı birleşik grant) |
| **Silme** | `cal_delete` | Etkinlik silme (geri alınabilir katman) | Kapalı | **Yüksek risk — açık onay zorunlu** |
| **Kalıcı silme** | — | Geri dönüşsüz silme | **Asla otomatik** | Kullanıcı açık komutu + tek satır uyarı; `SECURITY_NEVER_AUTO` |

**Firm kurallar:**

1. `cal_plan`, `cal_create`'i **otomatik kapsamaz** — planlama grant'ı ayrı tanımlanır; otomatik toplantı oluşturma yalnızca açık kural + ilgili write grant ile.
2. Toplu iptal veya çoklu katılımcılı etkinlik değişikliği **işlem bazlı onay** gerektirir (kural yoksa).
3. Oturum `cal_read` ≠ `cal_create` / `cal_cancel` / `cal_rsvp` — OD-041 CA6.

---

## İzin seviyeleri — Kişiler

| Seviye | Kod | Etki | Varsayılan | Onay modeli |
|--------|-----|------|------------|-------------|
| **Okuma / arama** | `contact_read` | Kişi bulma, liste görüntüleme | Kapalı | Oturum + kapsam (OD-041 CA1) |
| **İlişkilendirme** | `contact_link` | Kişiyi görev/proje/bağlama bağlama | Kapalı | İşlem veya kural-kapsamlı izin |
| **Geçmiş bağlama** | `contact_history_link` | İletişim geçmişi ilişkilendirme (provenance zorunlu) | Kapalı | İşlem veya kural-kapsamlı izin; ham içerik minimum tutma |
| **Kişi kuralı** | `contact_rule` | Kişi bazlı otomasyon kuralı tetikleme — OD-031 ile hizalı | Kapalı | **Açık kural + kural-kapsamlı grant** |
| **Yazma / düzenleme** | `contact_write` | Adres defterine kayıt ekleme/güncelleme | Kapalı | İşlem bazlı açık onay |
| **Silme** | `contact_delete` | Kişi kaydı silme | Kapalı | **Yüksek risk — açık onay zorunlu** |
| **Kalıcı silme** | — | Geri dönüşsüz silme | **Asla otomatik** | Kullanıcı açık komutu + tek satır uyarı |

**Firm:** `contact_rule` yalnızca OD-031 §Kullanıcı tanımlı otomasyon modeli ile uyumlu **açık opt-in kurallar** için geçerlidir; sessiz veya varsayılan kişi kuralı yok.

---

## Kişi bazlı kurallar — OD-031 çapraz referans

Takvim ve kişiler alanı, iletişim kanalları (OD-031) ile **aynı kural omurgasını** paylaşır:

| Boyut | Takvim / kişi örneği |
|-------|----------------------|
| **Kişi** | "Ahmet ile olan toplantıları her zaman bildir" |
| **Kaynak / hesap** | Belirli Google/iCloud takvim, belirli adres defteri |
| **Konu / etiket** | "Müşteri", "1:1", "Dış toplantı" |
| **İçerik / bağlam** | Etkinlik başlığı anahtar kelimesi |
| **Görev / proje** | Proje X ile ilişkili kişiler |
| **Önem** | Kullanıcı tanımlı öncelik |
| **Tetikleyici** | Takvim oluşturma, RSVP geldi, kişi eklendi, müsaitlik değişti |

**Çakışma (OD-031 CC7 ile aynı):** Otomatik toplantı oluşturma vs "öner, onayla" → **öneri + kullanıcı onayı** kazanır. Kişi kuralı ile genel kural çakışmasında **daha güvenli davranış** tercih edilir.

**Canonical kaynak (kural modeli detayı):** [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) §Kullanıcı tanımlı otomasyon modeli — mail kanalı için tanımlı; kişi/takvim tetikleyicileri bu modele **ek boyut** olarak eklenir, ayrı gevşek model icat edilmez.

---

## Hibrit onay modeli (OD-041 / OD-012 / product-rules)

```
[ Oturum / görev kapsamı + takvim veya kişi scope ]
        →  düşük risk: cal_read · contact_read · cal_notify · sınıflandırma

[ Kural-kapsamlı açık izin ]
        →  kullanıcı tanımlı kural ile sınırlı: cal_create · cal_rsvp · cal_update · contact_link · contact_rule
           (yalnızca kural eşleşmesinde; kural revoke = anında dur)

[ İşlem bazlı açık onay ]
        →  kural dışı veya yüksek risk: cal_cancel · cal_delete · contact_write · contact_delete
           ne / kim / hangi takvim / etki / katılımcılar görünür
```

### OD-041 hizası

| OD-041 ilkesi | Takvim / kişiler karşılığı |
|---------------|----------------------------|
| CA1 — düşük riskli okuma oturum bazlı | `cal_read`, `contact_read`, `cal_notify` — oturum + scope grant |
| CA2 — dış etkili aksiyon işlem bazlı | Kural dışı oluştur/iptal/RSVP/sil, kişi yaz/sil |
| CA4 — sessiz / carry-forward onay yok | Takvim/kişi kuralları ve izin yükseltmesi açık opt-in |
| CA6 — oturum izni ≠ dış etki yetkisi | Oturum okuma ≠ toplantı oluşturma / iptal / RSVP |
| CA7 — ne/nerede/etki | Oluştur/iptal/RSVP öncesi katılımcı, zaman, takvim, etki özeti zorunlu |

### OD-012 hizası

| OD-012 ilkesi | Takvim / kişiler karşılığı |
|---------------|----------------------------|
| CU4 — dış etkili aksiyon açık onay | Takvim yazma, RSVP, kişi yazma = dış etki |
| CU5 — okuma vs dış etki mod ayrımı | Takvim okuma modu ↔ planlama/yazma modu karışmaz |
| §7 — mod yükseltmesi yeni onay | `cal_read` oturumundan `cal_create`'e sessiz geçiş yok |
| CU6 — geri dönüşsüz otomatik yok | Kalıcı silme asla otomatik |

**Canonical ifade:** **Oturum izni** salt okuma/bildirim katmanını genişletir; **oluştur, taşı, iptal, RSVP, planlama, kişi yazma ve kişi kuralı tetikleme** oturum izninden **türemez**.

---

## Vault / credential (OD-001 / OD-002)

| Konu | Karar | Durum |
|------|--------|--------|
| Takvim OAuth token / API credential | Vault/kasa katmanında; Lumos yüzeyinde **açık tutulmaz** | decision-approved (ilke) |
| Kişi/adres defteri credential | Aynı vault modeli | decision-approved (ilke) |
| Connector erişimi | Bridge üzerinden amaç bazlı, kapsam sınırlı | decision-approved (ilke); API `implementation-pending` |
| Log / chat / panel | Credential, ham etkinlik gövdesi, kişi PII **gereksiz yazılmaz** | decision-approved |
| Scope | Hangi takvim, hangi adres defteri — kullanıcıya görünür | decision-approved (ilke); UX `implementation-pending` |

**OD-001/002 durumu:** Takvim/kişi credential'larının vault'ta tutulacağı ilkesi **onaylandı**; token formatı, connector credential şeması ve bridge entegrasyon akışı **`implementation-pending`**.

---

## Gizlilik ve public repo sınırı

| Gereksinim | Kural |
|------------|--------|
| **Public repo** | Etkinlik içeriği, kişi PII, credential, token, production endpoint **yazılmaz** |
| **Log** | PII ve etkinlik/kişi detayı operasyonel loga yazılmaz (firm) |
| **Kalıcı bellek** | Gereksiz tam etkinlik gövdesi veya adres defteri dump'ı kalıcı state'e yazılmaz; özet/provenance minimum tutma |
| **Provenance** | Öneri/aksiyon hangi takvim, hesap, kişi, zaman — kullanıcıya görünür |
| **Demo-safe** | Public repoda yalnızca ilke, onay modeli, placeholder |

---

## Repo gerçekliği (read-only — uygulama yok)

| Konu | Mevcut durum |
|------|--------------|
| **Takvim connector** | Yok — `controlled_bridge.py` kontrollü modda `calendar`/`takvim` yüzeylerini **bilinçli olarak reddeder** |
| **Kişiler (`src/device/contacts.py`)** | Stub: `Contacts.find_number()` her zaman `None` döner; harici adres defteri entegrasyonu yok |
| **Offline engine** | `contacts_read` / `contacts_lookup` lease adları tanımlı; gerçek lookup stub |
| **UI** | `PRODUCT_SUMMARY.md` — sol menüde "Takvim" nav öğesi (ürün hedefi); connector yok |
| **Config** | `config/contacts.json` dokümante edilmiş; OD-032 uygulaması bekliyor |

Bu bölüm **durum tespiti**dir; OD-032 ilke onayı repo'da otomatik implementasyon **başlatmaz**.

---

## Implementation-pending

| Konu | Durum | Not |
|------|--------|-----|
| **Provider seçimi** — Google Calendar, iCal, CalDAV, Apple Calendar, Exchange | **implementation-pending** | Teknik + platform değerlendirme |
| **Kişi kaynağı** — Google Contacts, iCloud, CardDAV, yerel OS | **implementation-pending** | Provenance ve scope ayrı grant |
| Vault API ve takvim/kişi credential şeması | **implementation-pending** | OD-001/002 ile birlikte |
| Onay UX, kural editörü (takvim/kişi tetikleyicileri) | **implementation-pending** | OD-031 UX ile hizalanır |
| Sync sıklığı, push vs poll, çoklu takvim | **implementation-pending** | Operasyonel model |
| `cal_plan` müsaitlik algoritması ve çakışma çözümü | **implementation-pending** | İlke: kullanıcı onayı / kural sınırı firm |
| Connector kodu, bridge entegrasyonu | **implementation-pending** | Public repoda demo-safe |
| Computer Use ile tarayıcı tabanlı takvim senaryosu | **implementation-pending** | OD-012 aynı granüler izin tablosu |

**Needs-review (açık alt detay):**

- Paylaşılan takvim / delegasyon senaryosu
- Toplantı davetiyesi gönderimi vs yalnızca takvim bloğu oluşturma ayrımı
- Kişi verisi ile mail (OD-031) birleşik kural önceliği
- Saat dilimi ve tekrarlayan etkinlik edge case'leri

---

## Bağımlılıklar

| OD / belge | İlişki | Durum |
|------------|--------|--------|
| **OD-031** | Kişi bazlı kural modeli, granüler izin omurgası | decision-approved / implementation-pending |
| **OD-041** | Hibrit onay — oturum vs işlem vs kural-kapsamlı | decision-approved / implementation-pending |
| **OD-012** | Computer Use / dış etki kapısı; mod ayrımı | decision-approved / implementation-pending |
| **OD-001 / OD-002** | Vault, token, credential bridge | decision-approved / implementation-pending |
| **OD-033** | Çalışma araçları — **kapsam dışı**, ayrı değerlendirme | decision-approved / implementation-pending — [`work-tools-connectors-decision.md`](./work-tools-connectors-decision.md) |
| **product-rules** | Lumos geçidi, ne/nerede/etki görünürlüğü | canonical |
| **external-integrations-permissions** | Entegrasyon felsefesi, gateway | canonical |

**Sıra önerisi (firm, uygulama paketi için):** Vault (OD-001/002) → granüler izin/onay UX (OD-041) → takvim/kişi provider değerlendirmesi → connector (bu belge).

---

## Yasak (onaysız veya otomatik)

| # | Aksiyon | Gerekçe |
|---|---------|---------|
| Y1 | Onaysız takvim okuma, oluşturma, iptal, RSVP | TC1; external-integrations-permissions |
| Y2 | Oturum izni ile otomatik toplantı oluşturma (kural olmadan) | TC3; OD-041 CA6 |
| Y3 | Otomatik kalıcı etkinlik/kişi silme | TC5; lumos-karar-sozlesmesi |
| Y4 | Credential'ın Lumos yüzeyinde veya logda açığa çıkması | TC6; OD-001/002 |
| Y5 | Etkinlik/kişi içeriğinin public repo veya gereksiz kalıcı belleğe yazılması | TC7 |
| Y6 | Sessiz kural, varsayılan-onaylı planlama, carry-forward izin | TC8; OD-041 CA4 |
| Y7 | Çalışma aracı connector'ını OD-032 altında birleştirme | TC9; OD-033 ayrımı |
| Y8 | Kişi kuralı ile OD-031 çelişen gevşek otomasyon modeli | TC4 |

---

## OD eşleme

| OD | Kaynak | Konu | Bu belgedeki karşılık | Durum |
|----|--------|------|------------------------|--------|
| **OD-032** | external-integrations-permissions.md | Takvim + Kişiler | Bu belgenin tamamı | **decision-approved / implementation-pending** |
| OD-033 | external-integrations-permissions.md | Platform connector'ları / çalışma araçları | §Kapsam sınırı — hariç | decision-approved / implementation-pending |
| OD-031 | mail-integration-approval-decision.md | Kişi bazlı kurallar | §Kişi bazlı kurallar | decision-approved / implementation-pending |
| OD-041 | commercial-approval-model-decision.md | Hibrit onay | §Hibrit onay modeli | decision-approved / implementation-pending |
| OD-012 | computer-use-permission-gate-decision.md | Dış etki kapısı | §OD-012 hizası | decision-approved / implementation-pending |
| OD-001/002 | vault-secret-token-decision.md | Vault / credential | §Vault | decision-approved / implementation-pending |

**İndeks notu:** `open-decisions-needs-review.md` OD-032 satırı bu belgeyle senkron tutulur; canonical kaynak önce `external-integrations-permissions.md`, onaylı karar özeti bu dosyadır.

---

## Sonraki adım

1. **Onay (tamamlandı — ilke):** Bu belgedeki TC1–TC9 ve izin tabloları `decision-approved` kabul edilir; provider/UX/connector **`implementation-pending`** kalır.
2. **Implementation-pending:** Google Calendar / iCal / CalDAV ve kişi kaynağı değerlendirmesi — ayrı uygulama paketi.
3. Vault modeli (OD-001/002) netleşmeden takvim/kişi credential **Lumos yüzeyine taşınmaz**.
4. Kişi bazlı kurallar implementasyonunda **OD-031 kural editörü ve çakışma algoritması** yeniden icat edilmez — genişletilir.
5. Çalışma araçları (GitHub, Slack, Linear, Notion, Drive) **OD-033** kapsamında ayrı değerlendirilir.

**Yasak (bu aşamada):** kod, test, connector, provider entegrasyonu, credential, production endpoint, takvim/kişi içeriğinin repoya yazılması.

---

Son güncelleme: 2026-06-18
