# Vault uygulama yol haritası — stub (OD-001–005)

**Durum:** **`decision-approved`** (ilke) / **`implementation-pending`** (tüm somut adımlar).  
**Public repo sınırı:** Bu belge **yalnızca public-safe stub**; secret, KDF, HSM, API şeması ve credential **private katmanda** tanımlanır.

**Canonical ilke:** [`vault-secret-token-decision.md`](./vault-secret-token-decision.md)  
**İndeks:** OD-001 – OD-005 (`open-decisions-needs-review.md`)

---

## 1. Onaylı ilke özeti (public)

| OD | Konu | Public durum |
|----|------|--------------|
| OD-001 | Vault katman modeli | Lumos secret taşımaz; vault ayrı güvenli katman |
| OD-002 | Token / bridge entegrasyonu | Credential Lumos yüzeyinde açık değil |
| OD-003 | Amaç bazlı erişim | Sınırlı, onaylı, görünür erişim |
| OD-004 | Segmentasyon | Tek ele geçirmede tüm sırlar açığa çıkmamalı |
| OD-005 | Şifreleme / anahtar | Algoritma/KDF/HSM — **private impl** |

---

## 2. Implementation checklist (private katman — public'te detay yok)

| # | Adım | Efor | Public |
|---|------|------|--------|
| V1 | Vault ürün/teknoloji seçimi | XL | Out of scope |
| V2 | Depolama + dağıtım modeli | XL | Out of scope |
| V3 | Amaç kodu listesi + Lumos–vault API sözleşmesi | L | Stub referans only |
| V4 | Connector izolasyonu / segmentasyon | L | Out of scope |
| V5 | KDF, döngü politikası, secure enclave yolu | XL | Out of scope |
| V6 | Bridge + kimlik katmanı entegrasyon akışı | XL | Out of scope |
| V7 | UX dili (OD-023) panel copy | M | [`od-023-vault-ux-language-decision.md`](./od-023-vault-ux-language-decision.md) |

**Sıra (firm):** V1 → V2 → V3 → V4/V5 paralel plan → V6 → V7 (UX public copy erken taslak mümkün).

---

## 3. Bağımlılıklar

- OD-031/032/033 connector credential → V6 sonrası
- OD-012 Computer Use credential → V6
- DL-E03 — «karar onaylı, uygulama bekliyor»

---

## 4. Yasak (public repo)

Vault secret kodu, örnek token, production endpoint, KDF parametreleri, HSM config.

---

Son güncelleme: 2026-06-20 (envanter ab791c14 §12 #1 — Phase 3 stub)
