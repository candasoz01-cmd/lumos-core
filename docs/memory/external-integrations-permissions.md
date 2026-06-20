# Dış entegrasyonlar ve izinler — canonical kayıt

## Amaç

ChatGPT **Saved Memories** ve oturum bağlamından taşınan mail, takvim, dış sistem bağlantıları ve izin tabanlı entegrasyon notlarının repo'daki **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir. **Gerçek credential, token veya production endpoint bu dosyaya yazılmaz.**

| Konu | Kural |
|------|--------|
| **ChatGPT Saved Memories** | **Canonical değildir.** Referans ve geçici kaynak. |
| **`docs/memory/`** | **Canonical'dır.** Çelişki varsa repo metni esas alınır. |
| **Çekirdek sözleşme** | Güvenlik, yetki, kalıcı silme ve onay kuralları `docs/lumos-karar-sozlesmesi.md` ile sabittir; bu dosyadaki maddeler bunları gevşetemez. |

Taşıma süreci: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

---

## Entegrasyon felsefesi

Lumos **belirli bir entegrasyon yöntemine bağlı tanımlanmaz**. Amaç, kullanıcının **yetki verdiği kapsamda** ilgili sistemi kullanabilmektir; **teknik yöntem ikincildir**.

İzinli yollar örnek olarak şunları içerebilir (tümü değil):

| Yöntem | Not |
|--------|-----|
| **Resmi API** | OAuth, REST, platform SDK — mümkün olduğunda tercih edilen yol |
| **Yerel entegrasyon** | Cihaz/OS düzeyi bağlayıcı |
| **Computer Use** | Tarayıcı/uygulama düzeyi kontrollü dış etki — [`computer-use-permission-gate-decision.md`](./computer-use-permission-gate-decision.md) (OD-012) |
| **Erişilebilirlik katmanları** | İzinli ve yasal erişim yolları |
| **Gelecekteki izinli yöntemler** | Kullanıcı onayı + Lumos geçidi + çekirdek sözleşme ile |

**Omurga sabittir; yöntem değişkendir:** Aynı izin, onay ve gateway kuralları — kullanıcı kapsamı, provenance, mod ayrımı — **OpenAI Computer Use** ile **doğrudan API entegrasyonları** (ve diğer izinli yöntemler) altında **aynı çatıda** tutulur. Yöntem seçimi uygulama kararıdır; platform yeteneği, kullanıcı yetkisi ve güvenlik sınırlarına göre değerlendirilir.

Bu belgedeki mail, takvim, connector ve Computer Use bölümleri **aynı felsefenin** alan-özel ifadeleridir; tek bir yönteme indirgenmez.

---

## İzin ve kullanıcı onayı

### Genel kural

Kullanıcı **açık onayı** olmadan aşağıdaki işlemler **yapılmaz**:

| Kategori | Yasak (onaysız) |
|----------|-----------------|
| Ödeme | Ödeme başlatma, yenileme, satın alma |
| Domain | Domain satın alma, yenileme |
| Veri | Dış platformdan veri çekme, kalıcı import |
| E-posta | Okuma, gönderme, silme, arşivleme |
| Dış yazma | Harici sistemlere yazma / dış etkili aksiyon |

### Gateway ilkesi

- Dış sistem işlemleri **Lumos güvenli geçidi** ve **kullanıcı onayı** üzerinden yapılır.
- Bağlayıcılar (connector) kullanıcı verisini veya dış içeriği **kaynak/köken belirsiz** şekilde içe aktarmaz.
- **Ayrım zorunlu:** otomatik dış operasyon ↔ yalnızca rehber/kısayol (manuel UI kısayolu).

**Referans:** Render / Vercel / GitHub manuel kısayolları UI dokümanında; burada **izinli dış bağlantı ilkesi** olarak kayıtlıdır — otomatik deploy veya credential yönetimi değil, kullanıcı yönlendirmesi.

---

## Mail entegrasyonu

> **OD-031 kapsam notu:** Tam strateji belgesi private strategy vault'ta. Public repoda yalnızca ADR-002 seviyesi ilke, demo-safe kod stub referansları ve canonical boundary tutulur — [`public-repo-boundary.md`](./public-repo-boundary.md) § Bölüm A.

**Durum:** `[decision-approved / implementation-pending]` — ilke kararları onaylı; public demo-safe stub (`src/integrations/mail/`, PR #413–#415); **ürün uygulanmamış**.

**Public referanslar (demo-safe):**

- [`docs/decisions/ADR-002-mail-inbox-intelligence.md`](../decisions/ADR-002-mail-inbox-intelligence.md) — taslak; onaysız okuma/gönderim yok; öneri/önizleme ile gerçek aksiyon ayrımı
- [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) (OD-031) — private strategy notice stub
- [`mail-strategy-migration-index.md`](../mail-strategy-migration-index.md) — taşınan belgeler indeksi

### Hedef davranış (public özet — ADR-002 hizası)

- Mail, inbox intelligence için **ilk aday kanal**; diğer iletişim kanalları gelecekte ayrı değerlendirme.
- **Varsayılan kapalı:** izin olmadan okuma, gönderme veya dış etki yok.
- **Taslak kapsam:** okuma + önem önceliği sunumu + önerilen aksiyonlar (önizleme); gönder/sil/arşiv ayrı onay gerektirir.
- Kural motoru, granüler izin matrisi, provider seçimi ve connector uygulaması → **private katman** (stub: [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md)).

### Tasarım ilkeleri (public)

| İlke | Açıklama |
|------|----------|
| İzinli erişim | Yalnızca kullanıcının açıkça verdiği mail erişim izni |
| Kaynak atıfı | Özet/öneri hangi kaynağa dayanıyor belirtilir |
| Aksiyon ayrımı | Okuma/özet ↔ gönder/sil/arşiv: ayrı onay katmanı (ADR-002) |

### Yasak (açık yetkilendirme olmadan)

- E-posta **okuma**
- E-posta **gönderme**
- E-posta **silme**
- E-posta **arşivleme**

---

## Takvim ve kişiler (OD-032)

> **Kapsam sınırı:** Bu bölüm yalnızca **Takvim + Kişiler** içindir. GitHub, Slack, Linear, Notion, Drive ve benzeri **çalışma araçları** → **OD-033** (aşağıdaki §Platform connector'ları / çalışma araçları); OD-032 ile **birleştirilmez**.

**Durum:** `[decision-approved / implementation-pending]` — ilke kararları onaylı; uygulama yok. **Onaylı karar özeti:** [`calendar-contacts-decision.md`](./calendar-contacts-decision.md) (OD-032).

### Hedef davranış (gelecek)

**Takvim** (kullanıcı yetkilendirmesi dahilinde):

- Okuma, toplantı oluşturma, taşıma/yeniden zamanlama, iptal, RSVP (katılım yanıtı), kullanıcı adına planlama — granüler izin paketi (`cal_read`, `cal_create`, `cal_update`, `cal_cancel`, `cal_rsvp`, `cal_plan` vb.) ve OD-041/OD-012 hibrit onay omurgası.

**Kişiler:**

- Kişi bulma, ilişkilendirme, iletişim geçmişi bağlama (provenance ile), kişi bazlı kurallar — OD-031 kural modeli ile çapraz; granüler izin (`contact_read`, `contact_link`, `contact_history_link`, `contact_rule` vb.).

### Tasarım ilkeleri

| İlke | Açıklama |
|------|----------|
| Varsayılan pasif | İzin olmadan takvim/kişi okuma ve dış etki yok |
| Granüler izin | Okuma ↔ oluştur/iptal/RSVP/plan ↔ kişi yazma ayrı grant |
| Kişi kuralları | OD-031 ile aynı opt-in, revoke, çakışmada güvenli kazanır |
| Entegrasyon yöntemi ikincil | Google Calendar, iCal, CalDAV, yerel OS — aynı izin omurgası |
| Vault | Credential OD-001/002; Lumos yüzeyinde açık tutulmaz |
| Çalışma araçları hariç | Notion, Asana, GitHub vb. → OD-033 |

### Yasak (açık yetkilendirme olmadan)

- Takvim **okuma**, **oluşturma**, **iptal**, **RSVP**, **planlama**
- Kişi **arama**, **yazma**, **ilişkilendirme**, **kişi kuralı tetikleme**

### Uygulama bekliyor (implementation-pending)

İlke kararları onaylı; aşağıdakiler **henüz uygulanmadı** — detay: [`calendar-contacts-decision.md`](./calendar-contacts-decision.md) §Implementation-pending.

- Provider seçimi (Google Calendar, iCal, CalDAV, Apple Contacts vb.)
- Connector kodu, bridge entegrasyonu, sync modeli
- Onay UX, takvim/kişi kural editörü
- Vault credential şeması (OD-001/002 ile birlikte)

---

## Platform connector'ları / çalışma araçları (OD-033)

> **Kapsam sınırı:** Bu bölüm yalnızca **çalışma/ürün verimliliği platformları** içindir. Takvim + Kişiler → [`calendar-contacts-decision.md`](./calendar-contacts-decision.md) (OD-032); iletişim kanalları → [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) (OD-031); ticari domain → OD-039–042. **Birleştirilmez.**

**Durum:** `[decision-approved / implementation-pending]` — ilke kararları onaylı; uygulama yok. **Onaylı karar özeti:** [`work-tools-connectors-decision.md`](./work-tools-connectors-decision.md) (OD-033).

### Hedef davranış (gelecek)

- Lumos, **açık izin paketi ve değerlendirme listesi** ile GitHub, Slack, Google Drive, Linear, Notion, Asana ve benzeri platformlarda bağlam okuma, bildirim ve kural-kapsamlı dış etki yapabilir — varsayılan pasif; connector **otomatik eklenmez**.
- Her platform **tek tek** ihtiyaç + etki analizi sonrası değerlendirilir; watchlist ≠ entegrasyon.

### Değerlendirme listesi (özet)

| Katman | Araç | Rol (taslak) | Not |
|--------|------|--------------|-----|
| 1 | **GitHub** | Repo/issue/PR bağlamı | UI manuel kısayol mevcut; **ilk connector adayı** (uygulama paketi) |
| 2 | **Slack** | Bildirim / kanal özeti | İzin + provenance; iş yeri bağlamı (OD-031 ile sınır ayrımı) |
| 2 | **Google Drive** | Dosya okuma / referans | Kalıcı import onaysız yok |
| 3 | **Linear** | Görev/issue senkronu | Panel/görev akışı çakışma kontrolü |
| 4 | **Notion**, **Asana** | Sayfa / görev bağlamı | Ayrı platform değerlendirmesi |
| 5 | Diğer benzer araçlar | — | Listeye ekleme ayrı karar |

### Tasarım ilkeleri

| İlke | Açıklama |
|------|----------|
| Değerlendirme listesi | Otomatik connector ekleme yok; tek platform, tek pilot |
| Granüler izin | `{platform}_read`, `_notify`, `_create`, `_update`, `_comment`, `_share`, `_delete` |
| Varsayılan pasif | İzin olmadan okuma/yazma yok |
| Hibrit onay | OD-041/OD-012 — oturum vs kural-kapsamlı vs işlem bazlı |
| Vault | Credential OD-001/002 |
| Entegrasyon yöntemi ikincil | Resmi API tercih; Computer Use aynı izin omurgası |
| UI kısayolu ≠ connector | GitHub/Render/Vercel yönlendirme — otomatik veri akışı değil |

### Yasak (açık yetkilendirme olmadan)

- Platform **okuma**, **oluşturma**, **güncelleme**, **paylaşım**, **silme**
- Onaysız **kalıcı import** (toplu dosya/issue/görev)
- **Rastgele/toplu** connector ekleme

### Uygulama bekliyor (implementation-pending)

İlke kararları onaylı; aşağıdakiler **henüz uygulanmadı** — detay: [`work-tools-connectors-decision.md`](./work-tools-connectors-decision.md) §Implementation-pending.

- İlk connector pilotu (öneri GitHub, Katman 1)
- OAuth scope, webhook vs poll (platform başına)
- Onay UX, platform kural editörü
- Lumos görev motoru ↔ Linear/Asana çakışma algoritması
- Vault credential şeması (OD-001/002 ile birlikte)

---

## OpenAI ajan ve computer-use araçları

> **Yöntem notu:** Computer Use, Lumos entegrasyonlarının **tanımı değil**; §Entegrasyon felsefesi kapsamında **izinli yöntemlerden biridir**. Doğrudan API connector'ları ile aynı izin/onay omurgasını paylaşır.

**Durum:** `[needs-review]` — izleme listesi; her biri ayrı değerlendirme.

| Araç / API | Takip | Değerlendirme notu |
|------------|-------|---------------------|
| OpenAI Agents SDK | evet | Çekirdek panel/görev/güvenlik akışı korunmalı |
| Realtime / voice agents | evet | Ses deneyimi dokümanı ile hizala |
| Computer Use | evet | Onaysız dış yazma/klik riski — sıkı kapı |
| Codex Plugins | evet | Public repo sınırı + onay modeli |

**İlke:** Hepsi birden eklenmez; **birer birer** değerlendirilir, mevcut Lumos karar katmanları gevşetilmez.

---

## Dış sistem aksiyon sınırları

| Sınır | Kural |
|-------|--------|
| Otomatik dış ops | Kullanıcı onayı + Lumos geçidi zorunlu |
| Kısayol / rehber | Yalnızca yönlendirme; credential veya veri çekme yok |
| Kalıcı import | Açık onay olmadan yok |
| Ödeme / domain | Açık onay olmadan yok |
| Mail aksiyonları | Açık yetkilendirme olmadan yok |
| Dış yazma | Onaysız yok |

**Ayrım özeti:**

```
[ Kullanıcı onayı ] → [ Lumos gateway ] → [ İzinli connector ] → dış sistem
[ UI kısayolu ]     → tarayıcı / manuel adım (otomatik veri akışı yok)
```

---

## Kaynak / köken şeffaflığı

| Gereksinim | Açıklama |
|------------|----------|
| Provenance | Dış içerik hangi sistem, hesap, zaman — kullanıcıya görünür |
| Kaynak atıfı | Özet/öneri hangi ham kaynağa dayanıyor belirtilir |
| İçe aktarma | Belirsiz kökenli toplu import yasak |
| Connector sınırı | Connector "sessiz" arka plan senkronu yapmaz (onaysız) |

Mail özetleri ve ileride takvim/Slack özetleri bu tabloya tabidir.

---

## Riskler

| Risk | Azaltma |
|------|---------|
| Onaysız dış veri çekme | Genel izin tablosu + gateway |
| Credential sızıntısı | Secret bu dosyaya yazılmaz; vault katmanı |
| Connector scope creep | Değerlendirme listesi; rastgele ekleme yok |
| Computer-use kötüye kullanım | Ayrı onay; dış yazma kapısı |
| ChatGPT memory drift | Repo canonical; periyodik migration kontrolü |
| Mail gizlilik ihlali | Kapsam + önem sırası + aksiyon ayrımı (tasarım) |

---

## Migration tablosu

ChatGPT Saved Memories / oturum bağlamından bu dosyaya taşınan maddeler.

| # | Kaynak konu | Hedef bölüm | Durum | Not |
|---|-------------|-------------|--------|-----|
| 1 | Mail okuma/özet (gelecek) | Mail entegrasyonu | `[migrated]` | Tasarım needs-review |
| 2 | Mail: onaysız okuma/gönder/sil/arşiv yok | Mail entegrasyonu | `[migrated]` | |
| 3 | Genel: onaysız ödeme, domain, veri çekme, import, mail, dış yazma | İzin ve kullanıcı onayı | `[migrated]` | security-architecture ile hizalı |
| 4 | GitHub, Slack, Drive, Linear listesi | Platform connector'ları / çalışma araçları | `[migrated]` | Karar: work-tools-connectors-decision.md (OD-033) |
| 5 | OpenAI Agents, Realtime, Computer Use, Codex Plugins | OpenAI ajan… | `[migrated]` | Tek tek evaluate |
| 6 | Render/Vercel/GitHub UI kısayolları | İzin ve gateway | `[migrated]` | UI doc referansı |
| 7 | Gateway + provenance + otomatik vs kısayol ayrımı | Gateway / Kaynak | `[migrated]` | |
| 8 | Takvim + kişiler (OD-032) | Takvim ve kişiler | `[migrated]` | Karar: calendar-contacts-decision.md; çalışma araçları → OD-033 |

---

## Manuel eklenecek maddeler

ChatGPT Saved Memories'ten henüz işlenmemiş maddeler için şablon. Taşıma tamamlanınca durumu ve hedef bölümü güncelleyin.

| # | Durum | ChatGPT / oturum metni (yapıştır) | Hedef bölüm | Not |
|---|--------|-----------------------------------|-------------|-----|
| 1 | `[queued]` | | | |
| 2 | `[queued]` | | | |
| 3 | `[queued]` | | | |
| 4 | `[queued]` | | | |
| 5 | `[queued]` | | | |

*(Boş satırlar kasıtlıdır; gerektiğinde yeni satır ekleyin.)*

---

*Son güncelleme: 2026-06-21 (OD-031 Phase 2 Step 4 — canonical boundary + ADR-002 stub sync)*
