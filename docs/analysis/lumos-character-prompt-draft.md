# Lumos Karakter Prompt Taslağı — Prompt vs Kod Ayrımı

| Alan | Değer |
|------|-------|
| Durum | **Taslak** — karar destek belgesi; kod değişikliği yok |
| Tarih | 2026-06-26 |
| Kapsam | Lumos karakterinin prompt'ta kalması gereken minimum çekirdek ile kod/dokümantasyonda yaşayan kuralların sınırı |
| İlgili | [`welockai-charter-draft.md`](./welockai-charter-draft.md), [`welockai-trust-model-draft.md`](./welockai-trust-model-draft.md), [`lumos-resource-mode-advisor.md`](./lumos-resource-mode-advisor.md), [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) |

**Sınır notu:** Bu belge public `lumos-core` deposunda demo-güvenli foundation olarak tutulur. Üretim sırları, ticari orkestrasyon ve operasyonel backend bu repoda yer almaz.

---

## 1. Minimal geliştirici / sistem prompt (kopyala-yapıştır)

Karakter kökü kısa kalır; yeni yetenekler bu kökü genişletir, değiştirmez.

### Türkçe (Cursor «Yeni komut istemi» / sistem prompt)

```
Lumos, kullanıcı yerine karar vermez. Önce gözlemler, sonra önerir.
Kalıcı veya dış etkili işlemler için onay ister.
Emin olmadığı bilgiyi kesinmiş gibi sunmaz.

Bu asistanın temel karakteri sabittir; yeni yetenekler karakteri
değiştirmez, yalnızca genişletir. (Kök aynı kök.)
```

### English (Cursor custom prompt equivalent)

```
Lumos does not decide on the user's behalf. It observes first, then suggests.
It asks for approval before permanent or externally impactful actions.
It does not present uncertain information as if it were certain.

This assistant's core character is fixed; new capabilities extend the character,
they do not replace it. (Same root, deeper branches.)
```

**Kullanım:** Bu blok yalnızca **karakter tonu ve davranış ilkelerini** taşır. Kurallar, güvenlik, entegrasyon ve enforcement detayları aşağıdaki tabloda ve kodda kalır.

---

## 2. Prompt'ta olmaması gerekenler (kod / dokümantasyonda yaşar)

Prompt büyüdükçe kaos büyür. Aşağıdaki sorumluluklar prompt'a kopyalanmaz; ilgili kaynağa işaret edilir.

| Sorumluluk | Nerede yaşar | Referans |
|------------|--------------|----------|
| **Karakter** (gözle, öner, onay iste, emin değilsen sus) | **Prompt** | §1 blokları |
| **Kurallar** (karar katmanları, yetki profilleri, adım türleri) | **Çekirdek kod + sözleşme** | [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md), `task_engine/profiles.py` |
| **Güvenlik** (SECURITY_NEVER_AUTO, kilit, keystore, consent) | **Kod + ADR** | [`lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) §2–3, ADR-010/011/012 |
| **ORAA** (kaynak modu danışmanı: gözle → öner → onay → uygula) | **`resource_mode_advisor` modülü** | [`lumos-resource-mode-advisor.md`](./lumos-resource-mode-advisor.md), `src/lumos/resource_mode_advisor.py` |
| **Entegrasyon** (GitHub, Slack, mail, köprü sınırları) | **Modüller + belgeler** | [`integrations-overview.md`](../integrations-overview.md), `modules/` |
| **Trust** (güven modeli, charter, ticari sınır) | **Charter / trust belgeleri** | [`welockai-charter-draft.md`](./welockai-charter-draft.md), [`welockai-trust-model-draft.md`](./welockai-trust-model-draft.md) |

**Kural:** Prompt'ta «asla kalıcı silme yapma» gibi uzun listeler tekrarlanmaz; `.cursor/rules/` ve çekirdek sözleşme enforcement'ı taşır.

---

## 3. Olgunluk içgörüsü — kök basit, dallar kodda

| İlke | Açıklama |
|------|----------|
| **Prompt büyümesi = kaos büyümesi** | Her yeni özellik için prompt'a paragraf eklemek karakteri değil, çelişkili talimat yığınını büyütür. Kök dört cümlede kalır. |
| **Karakter prompt'ta başlar, kodda yaşanır** | Prompt «nasıl konuşur / nasıl düşünür» der; «ne yapabilir / ne yapamaz» kod ve sözleşmede enforce edilir. |
| **Yetenek ≠ karakter değişimi** | Quantum katmanı, panel modülü veya ORAA danışmanı eklemek Lumos'u başka bir asistan yapmaz; aynı kök üzerine dal açar. |

### Bugünkü çalışma referansları (2026-06-26)

| Alan | PR / iz | Not |
|------|---------|-----|
| **ORAA** (kaynak modu danışmanı) | #554–#555 | Gözle → öner → onay → uygula; prompt'ta değil, `resource_mode_advisor` + belgede |
| **Panel** (modül navigasyon, i18n, badge) | #560 | UI yüzeyi; karakter prompt'undan ayrı katman |
| **Quantum layer** | [`lumos-quantum-layer-architecture.md`](./lumos-quantum-layer-architecture.md) | Readiness ve modül iskeleti; karakter kökünü değiştirmez |
| **AnchorUSB** | [`secure-device/`](./secure-device/) | Ayrı track — cihaz güven omurgası; prompt karakter bloğuna karıştırılmaz |

---

## 4. Cursor «Yeni komut istemi» kullanım notu

| Konu | Uygulama |
|------|----------|
| **Model seçimi** | Model (hız / akıl yürütme) karakterden bağımsızdır. Aynı §1 bloğu farklı modellerde kullanılabilir. |
| **Araçlar ve kurallar** | `.cursor/rules/` ve repo kodu prompt'a kopyalanmaz; «kurallar için `.cursor/rules/` ve `docs/lumos-karar-sozlesmesi.md`» tek satır yönlendirme yeterlidir. |
| **Tekrar yasağı** | SECURITY_NEVER_AUTO, trash prensibi, yetki profilleri ve entegrasyon matrisi prompt'ta listelenmez — zaten kod ve workspace kurallarında. |
| **Genişletme** | Yeni modül veya entegrasyon eklendiğinde prompt'a değil, ilgili modül belgesine ve testlere yazılır. |

---

## 5. Çapraz bağlantılar

| Belge | Yol |
|-------|-----|
| WeLockAI charter (ürün / ticari sınır) | [`docs/analysis/welockai-charter-draft.md`](./welockai-charter-draft.md) |
| Trust modeli taslağı | [`docs/analysis/welockai-trust-model-draft.md`](./welockai-trust-model-draft.md) |
| Kaynak modu danışmanı (ORAA) | [`docs/analysis/lumos-resource-mode-advisor.md`](./lumos-resource-mode-advisor.md) |
| Karar sözleşmesi (çekirdek omurga) | [`docs/lumos-karar-sozlesmesi.md`](../lumos-karar-sozlesmesi.md) |
| Quantum katman mimarisi | [`docs/analysis/lumos-quantum-layer-architecture.md`](./lumos-quantum-layer-architecture.md) |
| AnchorUSB (ayrı track) | [`docs/analysis/secure-device/README.md`](./secure-device/README.md) |
| Geliştirici onboarding (opsiyonel) | [`docs/getting-started.md`](../getting-started.md) |
| Katkı rehberi (opsiyonel) | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) |

---

## Özet

- **Prompt:** dört ilke — gözle, öner, onay iste, emin değilsen sus; kök sabit.
- **Kod / docs:** kurallar, güvenlik, ORAA, entegrasyon, trust.
- **Cursor:** model ayrı; kuralları prompt'a taşıma, işaret et.
