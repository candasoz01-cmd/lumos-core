# OD-023/024 — Vault UX dili ve Encrypted eksen kararı (taslak)

**Durum:** **`decision-approved`** (kullanıcı dili ilkeleri) / **`implementation-pending`** (copy, ekran, teknik spec).  
**Kaynak OD:** OD-023 (`product-rules.md` UX §3), OD-024 (Veri sahipliği Encrypted ekseni).  
**Çapraz:** OD-001–005 vault ilke kararları — [`vault-secret-token-decision.md`](./vault-secret-token-decision.md).

---

## 1. Birleşik karar

| Soru | Onaylı cevap |
|------|----------------|
| «Gizli anahtarlar Lumos yüzeyinde tutulmaz» UX'te nasıl anlatılır? | **Basit, doğrudan dil:** Lumos secret/anahtar **saklamaz**; güvenli kasa (vault) ayrı katmandadır; Lumos yalnızca **izinli geçit**. Teknik detay (KDF, HSM) kullanıcıya açılmaz. |
| Encrypted ekseni ürün dili | **OD-024 → bu belge:** Hassas veri «şifreli ve ayrı katmanda»; Lumos yüzeyinde ham secret yok. Teknik algoritma OD-005 **private impl**. |

---

## 2. Onaylı UX ilkeleri

| # | İlke |
|---|------|
| VX1 | Kullanıcıya **panik/teknik jargon** yerine sahiplik + geçit metaforu. |
| VX2 | Credential bağlantısı «Lumos'a kaydedildi» değil — «güvenli kasaya bağlandı, Lumos izinli erişir». |
| VX3 | Encrypted ekseni: «veriniz şifreli korunur» — algoritma adı public copy'de yok. |
| VX4 | Onay kapıları vault erişiminde **ne/amaç/süre** gösterir (OD-003 ilkesi). |
| VX5 | Public repo/docs: örnek secret, token, anahtar **yok**. |

---

## 3. Implementation-pending

| Konu | Durum |
|------|--------|
| Panel/chat copy taslağı | implementation-pending |
| `product-rules.md` UX §3 metin genişletmesi | implementation-pending |
| Encrypted ekseni yardım metni | implementation-pending |
| Vault bağlantı/onay ekranı | implementation-pending — private katman ağırlıklı |

---

## 4. OD eşleme

| OD | Durum |
|----|--------|
| **OD-023** | decision-approved / implementation-pending |
| **OD-024** | decision-approved / implementation-pending — Encrypted ekseni bu belgede birleşik |

---

Son güncelleme: 2026-06-20 (envanter ab791c14 §10 — Phase 2)
