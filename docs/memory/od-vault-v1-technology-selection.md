# Vault V1 — teknoloji seçimi (OD-001–005)

> **Durum:** **`decision-approved`** — harman yön onaylandı; somut PoC ve bridge adapter **private impl paketi**.  
> **Bu belge:** OSS/SaaS değerlendirme + seçim özeti — **vault ürün kodu yok**, **secret/API uygulaması yok**.  
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md); public repo boundary geçerli.

**Kaynak:** [`od-vault-dar-v1-design.md`](./od-vault-dar-v1-design.md) §5 (değerlendirme çerçevesi)  
**Yol haritası:** [`vault-implementation-roadmap.md`](./vault-implementation-roadmap.md) V1  
**İlke:** [`vault-secret-token-decision.md`](./vault-secret-token-decision.md)

---

## 1. Değerlendirme eksenleri (E1–E7)

[`od-vault-dar-v1-design.md`](./od-vault-dar-v1-design.md) §5.1 ile aynı. Skor: **✓** uygun · **~** kısmi · **✗** uyumsuz.

---

## 2. Aday tablosu (ciddi seçenekler)

| Aday | Sınıf | Lisans | E1 Lumos ayrımı | E2 Amaç bazlı | E3 Segmentasyon | E4 Self-host | E5 Ops yükü | E6 Public uyum | E7 Maliyet | Dar v1 not |
|------|-------|--------|-----------------|---------------|-----------------|--------------|-------------|----------------|------------|------------|
| **Infisical** (OSS + self-host) | OSS harman çekirdek | **MIT** | ✓ Secret kasada; Lumos yalnızca geçit | ✓ Proje/env RBAC, scoped token | ✓ Proje + ortam izolasyonu | ✓ Self-host Docker/K8s | ~ Orta — küçük ekip için Vault'tan düşük | ✓ Entegrasyon private katmanda | ✓ OSS self-host; SaaS opsiyonel | **Önerilen birincil çekirdek** |
| **OpenBao** (Vault OSS fork) | OSS harman çekirdek | **Apache-2.0** | ✓ Path/policy ile kasa ayrımı | ✓ ACL policy, lease/TTL | ✓ Namespace/path segmentasyonu | ✓ Self-host | ✗ Yüksek — HA, unseal, rotasyon | ✓ Adapter private | ✓ OSS; operasyon maliyeti yüksek | **Kurumsal / HA ihtiyacı alternatifi** |
| **1Password Connect** | SaaS + Connect sunucusu | Ticari | ✓ Connect sunucusu ara katman | ~ Vault item erişimi; fine-grained amaç API sınırlı | ~ Item/collection | ✗ 1Password cloud bağımlılığı | ~ Connect sunucusu bakımı | ✓ Detay private | ✗ Kullanıcı/ekip lisansı | **E4 zayıf — dar v1 birincil değil** |

### 2.1 Kısa liste dışı (neden elendi veya ertelendi)

| Aday | Sınıf | Elendi / ertelendi çünkü |
|------|-------|---------------------------|
| HashiCorp Vault (BSL) | OSS→BSL | Lisans değişimi; yeni dağıtımlar BSL — OSS harman için **OpenBao** tercih edilir |
| AWS Secrets Manager | SaaS | E4 vendor lock-in; E7 bulut maliyeti; kullanıcı verisi AWS'te |
| Bitwarden Secrets Manager | SaaS ağırlıklı | E2 connector amaç kodu modeli zayıf; API programatik vault için sınırlı |
| `pass` / düz dosya GPG | OSS CLI | E2/E3 amaç bazlı erişim ve segmentasyon yok — Lumos connector ihtiyacına uygun değil |
| Doppler | SaaS | E4/E7; Infisical ile overlap — self-host önceliğinde Infisical yeterli |

---

## 3. Eksen skor özeti (T1)

| Eksen | Infisical | OpenBao | 1Password Connect |
|-------|-----------|---------|-------------------|
| E1 — Lumos ayrımı | ✓ | ✓ | ✓ |
| E2 — Amaç bazlı erişim | ✓ | ✓ | ~ |
| E3 — Segmentasyon | ✓ | ✓ | ~ |
| E4 — Self-host / sahiplik | ✓ | ✓ | ✗ |
| E5 — Operasyon | ~ | ✗ | ~ |
| E6 — Public repo | ✓ | ✓ | ✓ |
| E7 — Maliyet | ✓ | ✓ | ✗ |

**Bloklayıcı:** Tüm ciddi adaylar E1/E6 geçer; 1Password E4 nedeniyle birincil değil.

---

## 4. Öneri

| Karar | Seçim |
|-------|--------|
| **Yön** | **Harman** — OSS self-host kasa çekirdeği + Lumos bridge adapter (**private katman**) |
| **Birincil çekirdek** | **Infisical** (MIT, self-host, RBAC, connector credential segmentasyonu) |
| **Alternatif** | **OpenBao** — yüksek operasyon kapasitesi ve Vault-uyumlu policy ihtiyacında |
| **Sıfırdan custom vault** | **Reddedildi** (bilinçli) — güçlü OSS varken gereksiz build |

### 4.1 Gerekçe (harman + Infisical)

1. **E1/E6:** Lumos secret taşımaz; kasa ayrı süreçte kalır; public repoda yalnızca arayüz/stub.
2. **E2/E3:** Proje/ortam + scoped service token ile `integration.mail.read` vb. amaç kodları private adapter'da eşlenebilir ([`od-vault-dar-v1-design.md`](./od-vault-dar-v1-design.md) §4).
3. **E4/E5:** Self-host ile veri sahipliği; OpenBao'ya göre dar v1 pilot için daha düşük operasyon eşiği.
4. **Mail bağımlılığı:** Gmail OAuth credential Infisical secret olarak saklanır; Lumos yalnızca vault bridge üzerinden amaçlı erişim ister ([`od-031-mail-dar-v1-scope.md`](./od-031-mail-dar-v1-scope.md) §4).

### 4.2 Neden sıfırdan değil

Güçlü OSS (Infisical, OpenBao) amaç bazlı erişim, segmentasyon ve self-host ihtiyacını karşılar. Sıfırdan kasa inşa etmek:

- Kripto/KDF/HSM edge case bakım yükü ([`vault-implementation-roadmap.md`](./vault-implementation-roadmap.md) V4/V5)
- Güvenlik yama ve audit döngüsü maliyeti
- Lumos'un asıl değeri **geçit + onay + orkestrasyon** — kasa icat etmek değil ([`vault-secret-token-decision.md`](./vault-secret-token-decision.md))

**Bilinçli sıfırdan = gereksiz build** ([`ozellik-oncesi-hazir-cozum-taramasi`](../../.cursor/rules/ozellik-oncesi-hazir-cozum-taramasi.mdc)).

---

## 5. Private implementation boundary

| Katman | Public `lumos-core` | Private / operatör katmanı |
|--------|---------------------|----------------------------|
| Vault çekirdek (Infisical/OpenBao deploy) | **Yok** | Self-host kurulum, backup, unseal |
| Lumos–vault bridge adapter | **Yok** (stub/ref only) | Amaç kodu → vault token eşlemesi |
| Credential şeması (mail OAuth vb.) | **Yok** | `private/vault-purpose-codes-v1` |
| API route / production endpoint | **Yok** | Private impl |
| Demo-safe | Arayüz protokolü, mock vault ref, grant modeli | — |

**OD-B05:** Bridge fiziksel merge **ertelendi** — vault adapter mevcut bridge sınırını genişletmez; ayrı private paket.

---

## 6. Rollback planı (T5)

| Adım | Aksiyon |
|------|---------|
| R1 | Infisical PoC başarısız → OpenBao alternatif PoC (aynı harman adapter arayüzü) |
| R2 | Her iki OSS yetersiz → SaaS (Doppler/1Password) **ayrı onay** — E4 bilinçli kabul |
| R3 | Lumos public stub'ları etkilenmez; yalnızca private adapter hedefi değişir |

---

## 7. Sonraki adımlar (private impl paketi)

| # | Madde | Katman |
|---|--------|--------|
| V1a | Infisical self-host PoC (tek node) | Private |
| V1b | Amaç kodu → scoped token eşlemesi taslağı | Private |
| V2 | Depolama + dağıtım modeli | Private |
| V3 | Vault–Lumos API sözleşmesi | Private |
| V6 | Bridge entegrasyon (**OD-B05 ayrı — ertelendi**) | Private / backlog |

Public repoda **yalnızca** bu karar özeti + mail/vault demo stub'ları ([`od-031-mail-dar-v1-scope.md`](./od-031-mail-dar-v1-scope.md) pilot).

---

## 8. OD eşleme

| OD | Bu belgedeki karşılık | Durum |
|----|------------------------|--------|
| OD-001 | §4 harman katman | decision-approved / impl-private |
| OD-002 | §5 bridge boundary | decision-approved / impl-private |
| OD-003 | §4.1 amaç kodu eşlemesi notu | decision-approved / impl-private |
| OD-004 | §2 E3 segmentasyon | decision-approved / impl-private |
| OD-005 | KDF/HSM — kasa çekirdeğine devredildi | decision-approved / impl-private |

---

Son güncelleme: 2026-06-20 (V1 teknoloji seçimi — kullanıcı onayı execute)
