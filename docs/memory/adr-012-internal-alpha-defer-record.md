# ADR-012 Internal Alpha Defer Record (G-18 / RB-01)

> **Durum:** `[decision-approved]` — Internal Alpha girişi için resmi defer kaydı; Wave 2+ enforcement **başlatılmaz**.
>
> **Belge ID:** G-18 · RB-01 (Alpha defer)
>
> **Üst sınır:** [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), [`docs/decisions/ADR-012-lumos-security-codex.md`](../decisions/ADR-012-lumos-security-codex.md)
>
> **Canonical kaynaklar:** [`release-blockers.md`](../analysis/release-blockers.md#rb-01--adr-012-security-codex-closed-değil), [`ADR-012-enforcement-decision-matrix.md`](../analysis/ADR-012-enforcement-decision-matrix.md), [`ADR-012-enforcement-prep-assessment.md`](../analysis/ADR-012-enforcement-prep-assessment.md)

**Karar:** Internal Alpha aşamasında ADR-012 Security Codex **CLOSED beklenmez**. Wave 1 Madde 1–2 kapandı (#491–#498); kalan codex maddeleri (Trust Faz 4, sensitivity↔gate, Panel LockState) bilinçli **defer** ile Alpha girişine devam edilir. Commercial Launch öncesi CLOSED veya resmi launch defer kaydı zorunludur.

**Repo snapshot:** `main` @ `24bdbef` (#504 queue kapanış); CI yeşil.

---

## 1. Amaç

Bu belge, [`release-blockers.md`](../analysis/release-blockers.md) RB-01 için **tek imzalı defer kaydı**dır. Alpha giriş kriteri A5 («ADR-012 durumu dokümante; Alpha CLOSED beklemez») bu kayıtla karşılanır. Kod veya Wave 2 enforcement taahhüdü **içermez**.

---

## 2. Aşama beklentisi özeti

| Aşama | ADR-012 CLOSED beklentisi | Bu kayıt |
|-------|---------------------------|----------|
| **Internal Alpha** | **Hayır** | Defer — bu belge |
| Closed Pilot | Hayır (müşteri «güvenli his»; codex kapanışı blokaj değil) | — |
| Open Beta | Hayır (hukuki sadeleştirme ilkeleri) | — |
| **Commercial Launch** | **Evet** — CLOSED veya resmi defer + müşteri iddiası hizası | Launch öncesi ayrı kayıt gerekir |

---

## 3. Checkpoint durumu (2026-06-21)

Kaynak: ADR-012 checkpoint tablosu + Wave 1 merge kanıtı (#491–#498, docs sync #499).

| Madde | Durum | Alpha defer |
|-------|-------|-------------|
| PR-C6 köprü `consume_confirmation` wiring | **Kapandı** (Wave 1 Madde 1) | — |
| P2 `SECURITY_NEVER_AUTO` tam eşleme | **Kapandı** (Wave 1 Madde 2, Seçenek B) | — |
| E2E confirmation (opt-in) | **Kapandı** (#459–#460) | — |
| Confirmation varsayılan-on | **Kapandı (docs)** — opt-in korunur (DL-C18) | Tam default-on Wave 2+ |
| **Trust Faz 4** | Açık | **Defer** — Wave 2+ (Madde 3); Alpha blokaj değil |
| **Sensitivity ↔ gate** | Açık | **Defer** — Wave 2+ (Madde 4); Madde 3 ön koşulu |
| **Panel LockState** | Açık | **Defer** — Wave 2+ (Madde 6); env vekili vs runtime kilit (RB-03) |

**Codex genel durum:** **CLOSED değildir** — bilinçli ve dokümante defer.

---

## 4. Alpha müşteri / ekip yüzü sınırı

Internal Alpha yalnızca ekip içidir. Aşağıdaki iddialar **Alpha'da yapılmaz**:

- «Tam güvenlik codex kapanışı» veya «tüm SECURITY_NEVER_AUTO yolları garanti» pazarlama iddiası
- Production vault / entegrasyon / ödeme vaadi
- Panel LockState ile CLI kilit durumunun tam hizalı olduğu iddiası

Alpha'da yeterli olan: README «early active development», panel **Sınırlı mod** etiketi, demo-safe public boundary ([`public-repo-boundary.md`](public-repo-boundary.md)).

---

## 5. RB çapraz eşleme (Alpha)

| RB | Alpha defer | Not |
|----|-------------|-----|
| RB-01 | **Evet** (bu belge) | Launch'ta kapat/defer kayıtlı |
| RB-02 | Kapandı | Wave 1 Madde 1 |
| RB-03 | Defer | Panel LockState — Wave 2+ |
| RB-04 | Kapandı | Wave 1 Madde 2 |
| RB-05 | Kısmi | Madde 1–2 kapandı; 3–6 defer |
| RB-11 | Defer | Trust Faz 4 |
| RB-12 | Defer | Sensitivity ↔ gate |
| RB-13 | Defer (docs) | Default-on ürün incelemesi ertelendi |

---

## 6. Launch kapanış koşulu (RB-01 tam kapanış)

Commercial Launch girişinde RB-01 için:

1. ADR-012 checkpoint tablosunda kalan maddeler `closed` / `deferred` / `accepted-as-is` olarak kayıt altına alınır, **veya**
2. Codex **CLOSED** geçişi tamamlanır (altı madde + test kanıtı).

Bu Alpha defer kaydı Launch defer kaydının yerine **geçmez**.

---

## 7. Bilinçli kapsam dışı (bu oturum)

Aşağıdakiler bu defer kaydıyla **authorize edilmez** — ayrı kullanıcı onayı ve Wave 2+ sırası gerekir:

- Trust Faz 4 uygulama PR'ları
- Confirmation default-on flip
- Sensitivity ↔ gate enforcement
- Panel LockState runtime hizalama

---

## 8. Ekip onayı (sign-off)

| Rol | Onay | Tarih | Repo ref |
|-----|------|-------|----------|
| Ürün / güvenlik imza yetkisi | Onaylandı — Internal Alpha defer | 2026-06-21 | `6795a41` |
| Docs PR | Bekliyor — merge sonrası hash güncellenir | — | — |

**Sign-off koşulu:** Bu belge merge edildiğinde G-18 «Alpha defer tek kayıt» maddesi **kapandı** sayılır; Launch defer ayrı belgede kalır.

---

## 9. Çapraz referanslar

| ID | Bağlantı |
|----|----------|
| G-24 | [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](../INTERNAL_ALPHA_RELEASE_SCOPE.md) |
| RB-01 | [`release-blockers.md`](../analysis/release-blockers.md#rb-01--adr-012-security-codex-closed-değil) |
| ADR-012 | [`ADR-012-lumos-security-codex.md`](../decisions/ADR-012-lumos-security-codex.md) |
| Wave 1 | #491–#498 merge; checkpoint sync #499 |

---

*Son güncelleme: 2026-06-21 — docs only; enforcement kodu yok.*
