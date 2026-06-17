# Domain, ödeme ve ticari dış aksiyonlar — canonical kayıt

## Amaç

ChatGPT **Saved Memories** ve oturum bağlamından taşınan domain/marka koruma, ödeme sistemi ve ticari dış aksiyon notlarının repo'daki **tek kaynak (canonical)** kaydı.

Bu dosya otomatik senkronize edilmez; içerik manuel kopyala-yapıştır ile güncellenir. **Gerçek ödeme credential'ı, banka bilgisi, domain registrar hesabı veya production endpoint bu dosyaya yazılmaz.**

| Konu | Kural |
|------|--------|
| **ChatGPT Saved Memories** | **Canonical değildir.** Referans ve geçici kaynak. |
| **`docs/memory/`** | **Canonical'dır.** Çelişki varsa repo metni esas alınır. |
| **Çekirdek sözleşme** | Güvenlik, yetki, kalıcı silme ve onay kuralları `docs/lumos-karar-sozlesmesi.md` ile sabittir; bu dosyadaki maddeler bunları gevşetemez. |

Taşıma süreci: [`chatgpt-saved-memories-migration.md`](./chatgpt-saved-memories-migration.md).

**Çapraz referans ruhu (çelişki yok):**

- [`payment-scope-decision.md`](./payment-scope-decision.md) — OD-011 onaylı karar özeti; şirket/vergi kaydı mevcut; erteleme nedeni şirket yokluğu değildir.
- [`external-integrations-permissions.md`](./external-integrations-permissions.md) — onaysız ödeme/domain/dış yazma yasak; gateway + açık onay.
- [`data-vault-user-data.md`](./data-vault-user-data.md) — kullanıcı verinin sahibi; Lumos kullanıcı adına onaysız ticari aksiyon başlatmaz.

---

## Domain ve marka koruma

**Durum:** `[needs-review]` — izleme/raporlama tasarımı; otomatik satın alma yok.

### Hedef davranış (gelecek)

| # | İlke | Not |
|---|------|-----|
| 1 | Lumos, marka koruma için **benzer domain varyasyonlarını** izleyebilir. | Taşındı |
| 2 | Kullanıcıya **müsaitlik**, **fiyat** ve **risk** bilgisi sunulabilir. | Taşındı |
| 3 | **Açık kullanıcı onayı olmadan:** domain **satın alma**, **yenileme** veya **ödeme başlatma yapılmaz.** | Taşındı — `external-integrations-permissions.md` ile hizalı |
| 4 | Birincil domain hedefi: **`welockai.com`** — korunur, hedef olarak saklanır. | Taşındı |
| 5 | Varyasyon domain'ler edinilirse **birincil domain'e yönlendirme** (redirect) uygulanır. | `[needs-review]` — edinim yalnızca kullanıcı onayı ile; redirect teknik detayı sonra |

### Yasak (onaysız)

- Domain satın alma
- Domain yenileme
- Ödeme veya registrar işlemi başlatma

### Aksiyon özeti

```
[ İzleme / rapor ] → müsaitlik · fiyat · risk (bilgi)
[ Satın alma / yenileme / ödeme ] → açık kullanıcı onayı zorunlu
[ Birincil hedef ] → welockai.com
```

---

## Ödeme sistemi ertelenmiş kapsam

**Durum:** `decision-approved / implementation-pending` (OD-011) — ilke kararları onaylandı; **uygulama başlamadı**. Şirket/vergi kaydı **mevcut**; erteleme nedeni şirket yokluğu değildir. Beklenen: ödeme ürün modeli, PSP seçimi, hukuk/mali ödeme akışı, abonelik modeli ve uygulama paketi. Ayrıntı: [`payment-scope-decision.md`](./payment-scope-decision.md).

| # | Kural | Not |
|---|--------|-----|
| 1 | Ödeme sistemi özelliği, **ödeme ürün modeli + PSP/hukuk-mali ödeme akışı uygulama paketi** hazır olana kadar **ertelenir** (şirket/vergi kaydı mevcut). | OD-011 — `decision-approved` |
| 2 | Bu sürede: **banka**, **PSP**, **merchant hesabı** veya **ödeme sağlayıcı entegrasyonu** aktif geliştirme kapsamında yapılmaz. | Taşındı |
| 3 | Gelecek fikir (yalnızca ürün notu): kullanıcılar arası **maliyet paylaşımı** için QR kod veya **tek ödeme linki** — uygulama, tasarım veya entegrasyon yok. | `[needs-review]` — OD-040; ürün/hukuk/PSP modeli sonra |

**Özet:** Ödeme altyapısı aktif geliştirme kapsamı dışı; yalnızca not olarak saklanır. Lumos, kullanıcı **açık onayı olmadan** ödeme, satın alma, abonelik, domain satın alma/yenileme veya ödeme linki oluşturma **başlatmaz**. Banka/PSP entegrasyonu, merchant hesabı, checkout, webhook, settlement ve fatura akışı henüz uygulanmadı.

---

## Ticari dış aksiyon sınırları

Tüm **ticari dış aksiyonlar** (domain, ödeme, abonelik, satın alma, yenileme, üçüncü taraf checkout) aşağıdaki sınırlara tabidir.

| Sınır | Kural |
|-------|--------|
| Onay | Kullanıcı **açık onayı** zorunlu |
| Kapsam | İşlem **açık kapsam** ile tanımlı olmalı (ne, nerede, ne kadar) |
| Risk | **Risk gösterimi** kullanıcıya sunulmalı |
| Gateway | Lumos güvenli geçidi üzerinden; sessiz arka plan ödemesi yok |
| Veri | Kullanıcı verisi ve ödeme bilgisi — [`data-vault-user-data.md`](./data-vault-user-data.md) sahiplik ilkesi |
| Entegrasyon | [`external-integrations-permissions.md`](./external-integrations-permissions.md) ile çelişki yok |

**Ticari dış aksiyon örnekleri (hepsi onaylı):**

- Domain satın alma / yenileme
- Ödeme başlatma / checkout yönlendirme
- Abonelik veya faturalı hizmet aktivasyonu
- Üçüncü taraf ödeme linki oluşturma veya paylaşma (Lumos adına)

**Yasak (onaysız):** yukarıdakilerin tümü.

---

## Kullanıcı onayı

| # | Kural | Not |
|---|--------|-----|
| 1 | Domain satın alma, yenileme ve ödeme başlatma **açık kullanıcı onayı olmadan yapılmaz.** | Taşındı |
| 2 | Ticari dış aksiyon öncesi: **kapsam** (işlem türü, tutar/hedef, sağlayıcı) kullanıcıya gösterilir. | Taşındı |
| 3 | Onay tek seferlik veya oturum bazlı olabilir — model `[needs-review]`. | Çekirdek sözleşme onay katmanları esas |
| 4 | Lumos, kullanıcı adına **sessiz** veya **varsayılan-onaylı** ticari işlem başlatmaz. | Taşındı |

**Onay akışı (taslak):**

```
[ Bilgi: müsaitlik · fiyat · risk ] → [ Kapsam + risk ekranı ] → [ Açık onay ] → [ İzinli aksiyon ]
```

---

## Risk ve şeffaflık

| Risk | Azaltma |
|------|---------|
| Onaysız domain/ödeme | Bu dosya + external-integrations genel yasak tablosu |
| Marka hedefi kayması | `welockai.com` birincil hedef olarak sabit kayıt |
| Erken PSP/banka kurulumu | Ödeme sistemi ertelenmiş kapsam — kurulum yok |
| Ticari scope creep | Her aksiyon: onay + kapsam + risk gösterimi |
| ChatGPT memory drift | Repo canonical; periyodik migration kontrolü |
| Ödeme modeli / PSP / hukuk-mali akış bekleniyor | Ödeme uygulama paketi onaylanmadan aktif kapsama alınmaz; maliyet paylaşımı (OD-040) `[needs-review]` |
| Kullanıcı verisi / ödeme bilgisi | Vault ve sahiplik — data-vault-user-data.md |

**Şeffaflık:** Domain izleme sonuçları ve ticari teklifler kaynak, fiyat ve risk ile birlikte sunulur; otomatik uygulama yok.

---

## Migration tablosu

ChatGPT Saved Memories / oturum bağlamından bu dosyaya taşınan maddeler.

| # | Kaynak konu | Hedef bölüm | Durum | Not |
|---|-------------|-------------|--------|-----|
| 1 | Benzer domain varyasyonlarını izleme (marka koruma) | Domain ve marka koruma | `[migrated]` | Tasarım needs-review |
| 2 | Müsaitlik, fiyat, risk bilgisi sunma | Domain ve marka koruma | `[migrated]` | Bilgi only |
| 3 | Onaysız domain satın alma/yenileme/ödeme yok | Domain / Kullanıcı onayı | `[migrated]` | external-integrations ile hizalı |
| 4 | Birincil domain: welockai.com | Domain ve marka koruma | `[migrated]` | Hedef korunur |
| 5 | Varyasyon domain → birincil redirect | Domain ve marka koruma | `[needs-review]` | Edinim onaylı; redirect detayı sonra |
| 6 | Ödeme sistemi uygulama paketi bekleniyor (şirket/vergi kaydı mevcut) | Ödeme sistemi ertelenmiş kapsam | `[migrated]` | OD-011 `decision-approved` |
| 7 | Banka/PSP/merchant kurulumu aktif kapsam dışı | Ödeme sistemi ertelenmiş kapsam | `[migrated]` | |
| 8 | QR / tek ödeme linki — maliyet paylaşımı fikri | Ödeme sistemi ertelenmiş kapsam | `[needs-review]` | Gelecek ürün notu only; OD-040 |
| 9 | Ticari dış aksiyon: onay + kapsam + risk | Ticari dış aksiyon sınırları | `[migrated]` | |
| 10 | external-integrations ve data-vault ile çelişki yok | Amaç / Ticari sınırlar | `[migrated]` | Çapraz referans |

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
