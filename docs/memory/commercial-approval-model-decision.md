# Ticari onay modeli — onaylı karar (OD-041)

> **Durum:** `decision-approved` — ilke kararları onaylandı; **uygulama başlamadı** (`implementation-pending`). Bu belge kod değişikliği değildir.
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) — güvenlik, yetki, kalıcı silme ve onay kuralları bu kararı gevşetemez.
>
> **Canonical kaynaklar:** [`commercial-domain-payments.md`](./commercial-domain-payments.md), [`payment-scope-decision.md`](./payment-scope-decision.md), [`computer-use-permission-gate-decision.md`](./computer-use-permission-gate-decision.md), [`external-integrations-permissions.md`](./external-integrations-permissions.md), [`open-decisions-needs-review.md`](./open-decisions-needs-review.md).

**Kaynak OD:** OD-041 (`commercial-domain-payments.md` — Kullanıcı onayı §3)

---

## Amaç

OD-041 kapsamında domain, ödeme, abonelik ve diğer **ticari dış aksiyonlar** için onay modelini netleştirmek.

Bu belge:

- Eski belirsizliği (`tek seferlik mi oturum bazlı mı?`) **hibrit model** ile çözer.
- Düşük riskli okuma/izleme ile **dış etkili ticari işlem** onayını katı biçimde ayırır.
- OD-012 (Computer Use) ile **işlem bazlı açık onay** hizasını ticari alana taşır.
- Oturum izninin **asla ödeme veya ticari işlem yetkisi** olmadığını sabitler.

**Uygulama notu:** İlke kararları onaylandı; kod, test, panel, ödeme entegrasyonu, onay UX implementasyonu veya otomasyon yapılandırması **henüz başlamadı**.

---

## Kapsam

| Dahil | Hariç |
|-------|--------|
| Domain satın alma, yenileme, transfer | PSP seçimi, banka/merchant kurulumu (OD-011) |
| Ödeme başlatma, checkout, para transferi | Ödeme altyapısı uygulama paketi detayı |
| Abonelik başlatma / yenileme | Maliyet paylaşımı QR/link ürün modeli (OD-040) |
| DNS değişikliği (ticari registrar bağlamında) | Domain izleme UX tasarımı (OD-042) |
| Üçüncü taraf ödeme linki oluşturma/paylaşma | Credential, token, production endpoint |
| Ticari bağlamda düşük riskli okuma, izleme, araştırma, durum kontrolü | Computer Use teknik entegrasyonu (OD-012 uygulama) |

**Çelişki çözümü:** `commercial-domain-payments.md` Kullanıcı onayı §3'teki `[needs-review]` ifadesi bu belgeyle **geçersiz kılınır**; canonical onay modeli bu dosyadır.

---

## Karar

**Onaylı karar (firm):** Ticari dış aksiyonlar için **hibrit onay modeli** geçerlidir.

| # | Kural | Durum |
|---|--------|--------|
| CA1 | **Düşük riskli** okuma, izleme, araştırma ve durum kontrolü **oturum bazlı izin** ile yapılabilir. | `decision-approved` |
| CA2 | **Dış etkili ticari aksiyonlar** her seferinde **işlem bazlı açık onay** gerektirir. | `decision-approved` |
| CA3 | Ödeme, satın alma, abonelik, yenileme, para transferi, domain satın alma, domain transferi, DNS değişikliği — her biri için **işlem başlamadan önce ayrı açık onay** zorunludur. | `decision-approved` |
| CA4 | **Sessiz onay yok;** varsayılan-onay yok; önceki onayın otomatik devri (auto-carry-forward) yok. | `decision-approved` |
| CA5 | OD-012 ile hizalı: dış etkili aksiyonlarda **işlem bazlı açık onay** canonical modeldir. | `decision-approved` |
| CA6 | **Oturum izni asla** ödeme veya ticari işlem yetkisine dönüşmez. | `decision-approved` |
| CA7 | Ticari işlem öncesi kullanıcı **ne, nerede, hangi etki, yaklaşık maliyet** görür; işlem bu bilgi olmadan başlamaz. | `decision-approved` |

---

## Hibrit model

```
[ Oturum / görev kapsamı ]  →  düşük risk: okuma · izleme · araştırma · durum kontrolü
[ İşlem bazlı açık onay ]   →  dış etkili ticari: ödeme · satın alma · abonelik · transfer · DNS · ...
```

**Firm ilkeler:**

1. **Oturum izni** yalnızca bilgi toplama ve kullanıcıya sunma kapsamını genişletir; ticari işlem hakkı vermez.
2. **Her dış etkili ticari adım** kendi onay kapısından geçer; çok adımlı akışta önceki adımın onayı sonraki adımı **otomatik yetkilendirmez**.
3. **Mod yükseltmesi** (izleme → satın alma) yeni, ayrı ve açık onay gerektirir — OD-012 §7 ile aynı mantık.
4. Lumos güvenli geçidi üzerinden; arka planda sessiz ticari işlem yok.

---

## İşlem bazlı vs oturum bazlı tablo

| Aktivite türü | Örnek | Onay modeli | Oturum izni yeterli mi? |
|---------------|-------|-------------|-------------------------|
| **Okuma / izleme** | Domain müsaitlik sorgusu, fiyat listesi, abonelik durumu görüntüleme | Oturum bazlı (görev kapsamı + yetki profili) | Evet — dış etki yok |
| **Araştırma** | Marka koruma varyasyon taraması, registrar karşılaştırma notu | Oturum bazlı | Evet — bilgi only |
| **Durum kontrolü** | Ödeme/abonelik pending durumu, DNS mevcut kayıt okuma | Oturum bazlı | Evet — salt okuma |
| **Ödeme başlatma** | Checkout, kart/PSP yönlendirme, para transferi | **İşlem bazlı açık onay** | Hayır |
| **Satın alma** | Domain kaydı, ürün/hizmet satın alma | **İşlem bazlı açık onay** | Hayır |
| **Abonelik** | Yeni abonelik, plan yükseltme | **İşlem bazlı açık onay** | Hayır |
| **Yenileme** | Domain yenileme, abonelik renewal | **İşlem bazlı açık onay** | Hayır |
| **Domain transferi** | Registrar transfer başlatma | **İşlem bazlı açık onay** | Hayır |
| **DNS değişikliği** | A/NS/MX kaydı güncelleme (etkili) | **İşlem bazlı açık onay** | Hayır |
| **Ödeme linki** | Üçüncü taraf tek link / QR oluşturma (Lumos adına) | **İşlem bazlı açık onay** | Hayır |

**Gerilim çözümü:** `commercial-domain-payments.md` §Kullanıcı onayı satır 3'teki "tek seferlik veya oturum bazlı olabilir" ifadesi, bu tablo ile **netleştirildi** — oturum yalnızca düşük riskli bilgi katmanı içindir; ticari işlem **her zaman işlem bazlıdır**, "tek seferlik oturum onayı ile birden fazla ödeme" modeli **yasaktır**.

---

## OD-012 hizası

| OD-012 ilkesi | OD-041 karşılığı |
|---------------|------------------|
| Dış etkili aksiyonlarda işlem bazlı açık onay (CU4, §5) | Tüm ticari dış aksiyonlar aynı kapıdan geçer |
| Genel onay Computer Use dış etkisi için tek başına yeterli değil (§5) | Genel onay ticari işlem için tek başına yeterli değil (CA6) |
| Okuma/gözlem vs dış etki mod ayrımı (§7) | Oturum izni vs işlem onayı ayrımı (hibrit model) |
| Mod yükseltmesi yeni onay gerektirir (§7) | İzlemeden satın almaya sessiz geçiş yok |
| Ödeme/satın alma/domain zorunlu onay (§6) | CA3 ile birebir; DNS değişikliği eklendi |
| Varsayılan-onay yasağı (§5) | CA4 — sessiz, önceden işaretli, carry-forward yok |

**Canonical ifade:** Dış etkili aksiyonlar (Computer Use veya doğrudan entegrasyon fark etmeksizin) için **işlem bazlı açık onay** tek standarttır; ticari alan bu standardın alt kümesidir, istisna değildir.

---

## OD-011 çapraz

[`payment-scope-decision.md`](./payment-scope-decision.md) (OD-011) ödeme **kapsamını** ve **erteleme sınırını** tanımlar; OD-041 **onay modelini** tanımlar. İkisi çelişmez:

| Boyut | OD-011 | OD-041 |
|-------|--------|--------|
| Ödeme altyapısı | Uygulama paketi gelene kadar aktif kapsam dışı | — |
| Onaysız ödeme yasağı | Evet (ilke) | Evet — işlem bazlı onay zorunlu |
| Domain satın alma/yenileme | Onaysız başlatılmaz | Her işlem ayrı onay |
| QR/tek link | Gelecek ürün notu (OD-040) | Oluşturma/paylaşma işlem bazlı onay |
| Kullanıcı görünürlüğü | Kapsam + risk gösterimi | Ne/nerede/etki/yaklaşık maliyet (CA7) |

Ödeme sistemi uygulamaya alındığında (OD-011 `implementation-pending` tamamlandığında) onay kapısı **OD-041 hibrit modeline** uygun kurulur; ayrı veya gevşek bir ticari onay modeli icat edilmez.

---

## Implementation-pending

Aşağıdakiler **henüz uygulanmadı**; bu belge uygulama izni vermez.

### Onay UX akışı (bekleyen)

```
[ Bilgi: müsaitlik · fiyat · risk · yaklaşık maliyet ]
        ↓
[ Kapsam ekranı: ne / nerede / etki ]
        ↓
[ İşlem bazlı açık onay — bu işlem için ]
        ↓
[ Lumos gateway ]
        ↓
[ Tek ticari işlem yürütülür ]
        ↓
[ Sonuç + kanıt kullanıcıya ]
```

**Bekleyen tasarım soruları (`needs-review` alt detay):**

- Onay ekranı wireframe ve CLI sözdizimi
- Çok adımlı checkout'ta ara bilgi vs ara onay ayrımı
- Yaklaşık maliyet gösterim formatı (para birimi, vergi dahil/hariç notu)
- İşlem iptali ve geri alma UX'i

### `kisitli_otonom` genel onay detayı (firm + bekleyen UX)

| Katman | Kural |
|--------|--------|
| **Genel onay (`kisitli_otonom`)** | Sınırlı `write_local` için geçerli; **ticari dış aksiyon için tek başına yeterli değildir**. |
| **Ticari işlem** | Genel onay açık olsa bile her ödeme/satın alma/transfer/domain/DNS adımı **ayrı işlem onayı** ister. |
| **Oturum izni** | Görev kapsamı içinde okuma/izleme; ödeme yetkisi **değildir**. |
| **Profil `rapor`** | Ticari dış etki yok; yalnızca bilgi ve simülasyon. |
| **Profil `guvenli_yurut`** | Safe local; ticari dış etki yine işlem onayı kapısından. |

**Implementation-pending:** Genel onay ile işlem onayının UI'da nasıl gösterileceği; çakışma durumunda hangi kapının öncelikli olduğu (firm: işlem onayı her zaman ek ve zorunlu).

---

## UX spec outline (implementation-pending checklist)

| # | Bileşen | Açıklama | Public-safe |
|---|---------|----------|-------------|
| UX1 | Oturum izni banner | Okuma/izleme kapsamı; «ticari yetki değildir» | Docs/stub |
| UX2 | İşlem onay modal | ne / nerede / etki / yaklaşık maliyet — CA7 | Taslak only |
| UX3 | DNS vs satın alma ayrımı | CA3 — ayrı onay adımları | [`od-039-042-domain-chain-decision.md`](./od-039-042-domain-chain-decision.md) |
| UX4 | `kisitli_otonom` genel onay rozeti | Genel onay ≠ işlem onayı | Taslak |
| UX5 | İptal / geri alma | Kullanıcı-visible; otomatik yok | Taslak |
| UX6 | Computer Use ticari tıklama | OD-012 aynı kapı | Cross-ref |

**Not:** Wireframe ve panel kodu **private/onaylı impl paketi** — public repoda yalnızca bu checklist.

---

## Riskler

| Risk | Azaltma (onaylı ilke) |
|------|------------------------|
| Oturum onayının ödeme yetkisine kayması | CA6 — oturum ≠ ticari yetki |
| "Bir kez onayladım, devam et" carry-forward | CA4 — önceki onay sonraki işlemi yetkilendirmez |
| Sessiz arka plan ödemesi | Gateway + işlem bazlı onay; CA2 |
| Belirsiz maliyet / kapsam | CA7 — yaklaşık maliyet ve etki öncesi zorunlu |
| Computer Use ile ticari işlem bypass | OD-012 hizası; aynı işlem bazlı kapı |
| `kisitli_otonom` genel onayın ticari genişlemesi | Genel onay ticari işlem için yetersiz (firm) |
| ChatGPT memory / eski "oturum belirsiz" metin | Bu belge canonical; §Kullanıcı onayı güncellendi |

---

## OD eşleme

| OD | Kaynak | Konu | Bu belgedeki karşılık | Durum |
|----|--------|------|------------------------|--------|
| **OD-041** | commercial-domain-payments.md | Ticari onay modeli | Bu belgenin tamamı | **decision-approved / implementation-pending** |
| OD-012 | computer-use-permission-gate-decision.md | Computer Use işlem bazlı onay | §OD-012 hizası | decision-approved / implementation-pending |
| OD-011 | payment-scope-decision.md | Ödeme kapsamı | §OD-011 çapraz — kapsam ayrı, onay hizalı | decision-approved / implementation-pending |
| OD-040 | commercial-domain-payments.md | Maliyet paylaşımı QR/link | Link oluşturma = işlem bazlı onay | needs-review |
| OD-039 | commercial-domain-payments.md | Domain redirect | [`domain-redirect-model-decision.md`](./domain-redirect-model-decision.md); zincir: [`od-039-042-domain-chain-decision.md`](./od-039-042-domain-chain-decision.md) | decision-approved / implementation-pending |
| OD-042 | commercial-domain-payments.md | Domain izleme tasarımı | Okuma/izleme = oturum izni; zincir: [`od-039-042-domain-chain-decision.md`](./od-039-042-domain-chain-decision.md) | decision-approved / implementation-pending |

**İndeks notu:** `open-decisions-needs-review.md` OD-041 satırı bu belgeyle senkron tutulur; canonical kaynak önce `commercial-domain-payments.md`, onaylı karar özeti bu dosyadır.

---

## Sonraki adım

1. **Implementation-pending:** Ticari onay UX akışı, işlem onay ekranı, yaklaşık maliyet gösterimi, `kisitli_otonom` genel onay ile işlem onayı UI ayrımı.
2. Ödeme uygulama paketi (OD-011) başlamadan önce bu onay modeli ürün gereksinimlerine **referans** olarak alınır; ayrı model icat edilmez.
3. Computer Use (OD-012) ticari tıklama/yazma senaryolarında **aynı işlem bazlı kapı** kullanılır.
4. Domain izleme (OD-042) yalnızca oturum izni katmanında kalır; satın alma yolu işlem onayına bağlanır.

**Yasak (bu aşamada):** kod, test, ödeme entegrasyonu, PSP kurulumu, credential, production endpoint, onay ekranı implementasyonu.

---

Son güncelleme: 2026-06-20 (UX checklist — envanter ab791c14 §12 #2)
