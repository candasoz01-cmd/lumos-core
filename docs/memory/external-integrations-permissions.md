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

**Durum:** `[needs-review]` — gelecek özellik; tasarım notları canonical, uygulama yok.

### Hedef davranış (gelecek)

- Lumos, **izinle** gelen e-postaları okur.
- Önem sırasına göre özetler ve kullanıcıya sunar.

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

*Son güncelleme: 2026-06-17*
