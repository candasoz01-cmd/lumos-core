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

> **OD-031 kapsam notu:** Onaylı karar belgesi [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) artık **genel iletişim kanalları otomasyon modelini** tanımlar; **mail ilk uygulama kanalıdır**. Telegram, WhatsApp, Messenger, SMS ve sosyal DM gelecek genişleme adaylarıdır — aynı ilke omurgası, kanal başına ayrı teknik değerlendirme.

**Durum:** `[decision-approved / implementation-pending]` — ilke kararları onaylı; uygulama yok. **Onaylı karar özeti:** [`mail-integration-approval-decision.md`](./mail-integration-approval-decision.md) (OD-031) — iletişim kanalları otomasyon modeli (mail ilk kanal); özetleme/pasif okuma sınırı yok; izin paketi sınırları içinde tam otomasyon mümkün; varsayılan pasif; OD-041/OD-012/product-rules hibrit onay hizası.

### Hedef davranış (gelecek — mail ilk kanal)

- Lumos, **açık izin paketiyle** gelen e-postaları takip eder; varsayılan pasif — izin olmadan okuma yok; grant sonrası okuma, bildirim ve sınıflandırma.
- Kullanıcı tanımlı kurallarla (kişi, domain, konu, içerik, görev, önem) kontrollü otomasyon — bildirim, taslak, kural-kapsamlı otomatik yanıt (açık opt-in, revoke edilebilir); tam otomasyon izin paketi sınırları içinde mümkün.

### Tasarım ilkeleri

| İlke | Açıklama |
|------|----------|
| İzinli erişim | Yalnızca kullanıcının açıkça verdiği mail erişim izni |
| Gizlilik sınırı | Hangi kutular/etiketler kapsamda net tanımlı |
| Önem sıralaması | Özet önceliği kullanıcıya şeffaf kriterlerle |
| Kaynak atıfı | Her özet hangi mesaj/kaynakla ilişkili açıkça belirtilir |
| Aksiyon ayrımı | Okuma/özet ↔ gönder/sil/arşiv: ayrı onay katmanı |

### Yasak (açık yetkilendirme olmadan)

- E-posta **okuma**
- E-posta **gönderme**
- E-posta **silme**
- E-posta **arşivleme**

---

## Takvim / kişiler / çalışma araçları

**Durum:** `[needs-review]` — placeholder; gelecek ihtiyaçlar netleşince genişletilecek.

| Alan | Not |
|------|-----|
| Takvim | Okuma/yazma izin modeli, onay ayrımı — henüz tanımsız |
| Kişiler | Adres defteri erişimi, provenance — henüz tanımsız |
| Çalışma araçları | Notion, Asana vb. adaylar değerlendirme kuyruğunda değil; ihtiyaç doğunca |

Bu bölüm şimdilik **boş şablon**; mail ve genel izin kuralları üst önceliklidir.

---

## GitHub / Drive / Slack / Linear bağlantıları

**Durum:** `[needs-review]` — değerlendirme listesi; rastgele ekleme yok.

Zamanı geldiğinde **tek tek** değerlendirilecek araç listesi:

| Araç | Rol (taslak) | Not |
|------|--------------|-----|
| GitHub | Repo/issue/PR bağlamı | Manuel kısayol UI'da mevcut; otomatik connector sonra |
| Slack | Bildirim / kanal özeti | İzin + provenance zorunlu |
| Google Drive | Dosya okuma / referans | Kalıcı import onaysız yok |
| Linear | Görev/issue senkronu | Panel/görev akışı ile çakışma kontrolü |

**İlke:** Connector eklemeden önce — çekirdek panel/görev/güvenlik akışına etki analizi.

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
| 4 | GitHub, Slack, Drive, Linear listesi | GitHub/Drive/… | `[migrated]` | Değerlendirme sonra |
| 5 | OpenAI Agents, Realtime, Computer Use, Codex Plugins | OpenAI ajan… | `[migrated]` | Tek tek evaluate |
| 6 | Render/Vercel/GitHub UI kısayolları | İzin ve gateway | `[migrated]` | UI doc referansı |
| 7 | Gateway + provenance + otomatik vs kısayol ayrımı | Gateway / Kaynak | `[migrated]` | |
| 8 | Takvim/kişiler/çalışma araçları | Takvim/… | `[needs-review]` | Placeholder |

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

*Son güncelleme: 2026-06-18*
