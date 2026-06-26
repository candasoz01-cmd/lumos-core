# Vault — dar v1 keşif ve tasarım (OD-001–005, OD-023)

> **Durum:** `design-approved` (dar v1 kapsam tanımı) / **`implementation-pending`** (prod vault API, secret, credential).  
> **Bu belge:** Keşif + tasarım çerçevesi only — **prod vault ürün kodu yok**; public'te demo-safe adapter stub (`src/integrations/vault/`, PR #414).  
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md); [`public-repo-boundary.md`](./public-repo-boundary.md).

**Kaynak OD:** OD-001 – OD-005 (vault ilke), OD-023/024 (UX dili)  
**Canonical ilke:** [`vault-secret-token-decision.md`](./vault-secret-token-decision.md)  
**UX ilkeleri:** [`od-023-vault-ux-language-decision.md`](./od-023-vault-ux-language-decision.md)  
**Yol haritası stub:** [`vault-implementation-roadmap.md`](./vault-implementation-roadmap.md)

---

## 1. Dar v1 amacı

Onaylı vault **ilkeleri** (OD-001–005) somut uygulamaya geçmeden önce, public repoda güvenli kalacak şekilde üç parçayı netleştirmek:

1. **OD-023 UX copy outline** — kullanıcıya gösterilecek metin iskeleti (teknik detay yok).
2. **Amaç kodu taslağı** — public'te yalnızca kategori iskeleti; tam liste **private belge referansı**.
3. **V1 vault teknoloji değerlendirme çerçevesi** — OSS / SaaS / harman seçenekleri; **sıfırdan zorunlu değil**.

**Dar v1 dışı (bilinçli):** **prod** vault ürün kodu, keystore implementasyonu, bridge API, token formatı, KDF/HSM parametreleri, production endpoint, örnek secret.

**Public'te mevcut (demo-safe stub):** `src/integrations/vault/` — adapter arayüzü + amaç kodu iskeleti; **prod vault ürün kodu değildir** ([`public-repo-boundary.md`](./public-repo-boundary.md) §C, PR #414).

---

## 2. Dar v1 kapsam tablosu

| Parça | Dar v1 | Uygulama |
|-------|--------|----------|
| Katman modeli (Lumos geçit / vault kasa) | Referans — onaylı | `decision-approved` — [`vault-secret-token-decision.md`](./vault-secret-token-decision.md) §4 |
| UX copy outline (panel/chat) | **Bu belge §3** | `design-approved` / copy metin `implementation-pending` |
| Amaç kodu kategori iskeleti | **Bu belge §4** | Tam liste private; API `implementation-pending` |
| Teknoloji değerlendirme çerçevesi | **Bu belge §5** | Seçim kararı ayrı onaylı impl paketi |
| Segmentasyon / şifreleme detayı | İlke referansı only | OD-004/005 private impl |
| Bridge + kimlik entegrasyon akışı | Taslak sıra only | V6 — `implementation-pending`; **OD-B05 ertelendi** |
| Mail/calendar/work-tools credential | Bağımlılık notu | Connector credential → vault dar v1 sonrası onaylı impl |

---

## 3. OD-023 — UX copy outline (public-safe)

Onaylı ilkeler: [`od-023-vault-ux-language-decision.md`](./od-023-vault-ux-language-decision.md) (VX1–VX5). Aşağıdaki outline **metin iskeletidir**; nihai copy `implementation-pending`.

### 3.1 Bağlantı / ilk kurulum

| Yüzey | Outline (Türkçe) | Yasak |
|-------|------------------|-------|
| Başlık | «Güvenli kasa bağlantısı» | «API key», «token», algoritma adı |
| Gövde | «Hassas bilgileriniz Lumos'ta saklanmaz. İzin verdiğinizde Lumos, güvenli kasadan yalnızca bu iş için gerekli erişimi kullanır.» | «Şifreledik: AES-…» |
| Onay kapısı | **Ne:** hangi entegrasyon · **Amaç:** ne yapılacak · **Süre:** oturum / tek iş | Süresiz / genel erişim vaadi |

### 3.2 Credential bağlandı (başarı)

| Yüzey | Outline |
|-------|---------|
| Başarı | «Bağlantı güvenli kasada. Lumos yalnızca verdiğiniz izinlerle erişir.» |
| İptal yolu | «Bağlantıyı istediğiniz zaman kapatabilirsiniz.» |

### 3.3 Encrypted ekseni (yardım / ayar)

| Yüzey | Outline |
|-------|---------|
| Kısa | «Hassas veriler şifreli ve ayrı katmanda korunur.» |
| Uzun (opsiyonel) | «Lumos, gizli anahtarları kendi yüzeyinde tutmaz; erişim onayınızla sınırlıdır.» |

### 3.4 Hata / erişim reddi

| Durum | Outline |
|-------|---------|
| Kilit kapalı | «Devam etmek için kilidi açmanız gerekir.» |
| Amaç reddedildi | «Bu işlem için güvenli kasa erişimi verilmedi. İzinleri kontrol edin.» |
| Profil yetersiz | «Bu işlem mevcut yetki profilinizle yapılamaz.» |

### 3.5 Copy checklist (dar v1)

| # | Madde | Dar v1 |
|---|--------|--------|
| UX-1 | Panel «kasa bağlantısı» akışı metinleri | outline onaylı |
| UX-2 | Chat kısa açıklama şablonu | outline onaylı |
| UX-3 | Onay kapısı ne/amaç/süre alanları | outline onaylı |
| UX-4 | `product-rules.md` UX §3 genişletmesi | `implementation-pending` |
| UX-5 | Canlı ekran / wireframe | `implementation-pending` — private ağırlıklı |

---

## 4. Amaç kodu taslağı (public iskelet)

**OD-003 ilkesi:** Erişim amaçla, kapsamla, onayla sınırlı ve görünür olmalıdır ([`vault-secret-token-decision.md`](./vault-secret-token-decision.md) §6).

### 4.1 Public kategori iskeleti

| Kategori kodu (taslak) | Açıklama (kullanıcı dili) | Örnek kapsam |
|--------------------------|---------------------------|--------------|
| `vault.connect` | Güvenli kasaya ilk bağlantı / yeniden bağlantı | Tek oturum, kullanıcı tetikler |
| `vault.read_credential` | Kayıtlı bağlantı bilgisini **kullanmadan** durum okuma | Meta only — secret yok |
| `integration.mail.read` | Mail okuma (izinli kutu) | Tek hesap, dar v1 mail scope |
| `integration.mail.notify` | Mail bildirim tetikleme | Okuma grant'ına bağlı |
| `integration.*` (genel) | Diğer connector'lar | **Dar v1 dışı** — private liste |

**Kural (firm):** Public repoda tam amaç kodu listesi, TTL, scope JSON şeması ve vault-Lumos API **yazılmaz**.

### 4.2 Private belge referansı

| Konu | Public | Private |
|------|--------|---------|
| Tam amaç kodu listesi | Yalnızca kategori iskeleti (§4.1) | **`private/vault-purpose-codes-v1`** (henüz oluşturulmadı — impl paketi) |
| API sözleşmesi | «Sözleşme private impl» | Aynı private paket |
| İzin profili eşlemesi | İlke: rapor = vault yazma yok | Detay tablo private |

**Dar v1 çıktısı:** Kategori iskeleti + private referans adı; **prod API/endpoint yok**. Public adapter stub (`src/integrations/vault/`) yalnızca demo-safe iskelet — §1 / boundary §C.

---

## 5. V1 vault teknoloji değerlendirme çerçevesi

**İlke:** Güçlü OSS veya uygun SaaS varken sıfırdan vault inşa etmek **zorunlu değildir** ([`ozellik-oncesi-hazir-cozum-taramasi`](../ozellik-oncesi-hazir-cozum-taramasi.md) ile uyumlu). Seçim **ayrı onaylı uygulama paketi** gerektirir.

### 5.1 Değerlendirme eksenleri

| Eksen | Soru | Ağırlık |
|-------|------|---------|
| E1 — Lumos ayrımı | Secret Lumos sürecinde mi kalıyor? | **Bloklayıcı** |
| E2 — Amaç bazlı erişim | Scope/TTL/audit destekleniyor mu? | Yüksek |
| E3 — Segmentasyon | Connector/credential izolasyonu mümkün mü? | Yüksek |
| E4 — Self-host / veri sahipliği | Kullanıcı verisi nerede duruyor? | Yüksek |
| E5 — Operasyon yükü | Bakım, güvenlik yamaları, edge case | Orta |
| E6 — Public repo uyumu | Entegrasyon detayı private'ta kalabilir mi? | **Bloklayıcı** |
| E7 — Maliyet | SaaS lisans / barındırma | Orta |

### 5.2 Seçenek sınıfları (öneri — karar değil)

| Sınıf | Örnek yön (temsilî) | Not |
|-------|---------------------|-----|
| **OSS — self-host kasa** | HashiCorp Vault, Bitwarden SDK/CLI pattern, pass/OSS secret manager | E1/E6 uyumu doğrulanmalı; Lumos yalnızca geçit |
| **SaaS — managed secrets** | 1Password Connect, Doppler, cloud KMS (BYOK) | E4/E7 ve vendor lock-in ayrı değerlendirme |
| **Harman** | OSS çekirdek + Lumos bridge adapter (private) | Önerilen default yön — sıfırdan kripto icat etme yok |
| **Sıfırdan** | Custom vault modülü | Yalnızca bilinçli onay + güçlü gerekçe; **dar v1 default değil** |

**Dar v1 kararı:** Çerçeve onaylandı; **V1 teknoloji seçimi onaylandı** — [`od-vault-v1-technology-selection.md`](od-vault-v1-technology-selection.md) (harman; seçim detayı private).

### 5.3 Değerlendirme checklist (V1 stub → impl paketi)

| # | Madde | Dar v1 | Sonraki paket |
|---|--------|--------|---------------|
| T1 | Eksen skor tablosu (E1–E7) | çerçeve | doldurulacak |
| T2 | OSS aday kısa liste (2–3) | çerçeve | PoC private |
| T3 | SaaS aday kısa liste (0–2) | çerçeve | hukuk/maliyet |
| T4 | Harman mimari diyagram (public-safe) | opsiyonel stub | private detay |
| T5 | Seçim kararı + rollback planı | **onaylı** — [`od-vault-v1-technology-selection.md`](od-vault-v1-technology-selection.md) §4–6 | private PoC |

---

## 6. Dar v1 uygulama sırası (tasarım — prod kod değil)

```
[Dar v1 design — bu belge]
        ↓
[Public demo-safe stub — `src/integrations/vault/` (PR #414); boundary §C]
        ↓
[V1 teknoloji seçimi — onaylı impl paketi, private]
        ↓
[V3 amaç kodu + API sözleşmesi — private]
        ↓
[V6 bridge entegrasyon — OD-B05 ayrı; ertelendi]
        ↓
[Connector credential — mail dar v1, OD-031 scope]
```

**Bağımlılık:** Mail dar v1 ([`od-031-mail-dar-v1-scope.md`](./od-031-mail-dar-v1-scope.md)) vault **credential şeması** için OD-001/002 + onaylı private impl paketini bekler. Public stub credential **ref** iskeleti sağlar; **canlı secret çözümleme** private PoC sonrasıdır. Lumos yüzeyine secret taşınmaz.

---

## 7. Yasak (dar v1 ve public repo)

| # | Yasak |
|---|--------|
| Y1 | Prod vault ürün kodu, keystore, canlı API route |
| Y2 | Örnek token, secret, credential, production URL |
| Y3 | KDF parametreleri, HSM config, şifreleme implementasyonu |
| Y4 | Bridge fiziksel merge (OD-B05 — kullanıcı 2026-06-20: ertelendi) |
| Y5 | Onaysız impl — bu belge uygulama izni vermez |

---

## 8. OD eşleme

| OD | Bu belgedeki karşılık | Durum |
|----|------------------------|--------|
| OD-001 | §2 katman referansı; §5 teknoloji | design-approved / impl-pending |
| OD-002 | §6 sıra; bridge ertelendi | design-approved / impl-pending |
| OD-003 | §4 amaç kodu iskeleti | design-approved / impl-pending |
| OD-004 | §5 E3 segmentasyon ekseni | design-approved / impl-pending |
| OD-005 | Public'te yok — private impl | decision-approved / impl-pending |
| OD-023 | §3 UX copy outline | design-approved / copy impl-pending |
| OD-024 | §3.3 Encrypted ekseni outline | design-approved / impl-pending |

---

## 9. Sonraki adım

1. **Private impl paketi:** Vault PoC (V1a) + amaç kodu token eşlemesi (V1b) — karar: [`od-vault-v1-technology-selection.md`](od-vault-v1-technology-selection.md); operatör runbook: [`ops-runbooks-private-notice.md`](../ops-runbooks-private-notice.md); canonical boundary: [`public-repo-boundary.md`](./public-repo-boundary.md).
2. **UX:** §3 outline → panel/chat copy taslağı (`implementation-pending`).
3. **Amaç kodları:** Private `vault-purpose-codes-v1` tam listesi + vault-Lumos API sözleşmesi.
4. **Mail:** Vault credential hazır olunca [`od-031-mail-dar-v1-scope.md`](./od-031-mail-dar-v1-scope.md) M2 pilot.

**Bu aşamada yapılmaz (prod impl):** canlı vault API, credential yazma, prod secret akışı, bridge merge. **Public'te mevcut (demo-safe):** `src/integrations/vault/` adapter stub + env-gated smoke — prod kapsam sayılmaz ([`public-repo-boundary.md`](./public-repo-boundary.md) §C).

---

Son güncelleme: 2026-06-21 (OD-031 Phase 2 Step 4 — public stub + canonical boundary sync)
