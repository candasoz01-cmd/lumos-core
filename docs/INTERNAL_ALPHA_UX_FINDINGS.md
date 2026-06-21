# Internal Alpha — UX Findings

| Alan | Değer |
|------|-------|
| **Belge türü** | UX finding takibi (Internal Alpha) |
| **Üst sınır** | [`INTERNAL_ALPHA_OPERATIONS.md`](INTERNAL_ALPHA_OPERATIONS.md), [`INTERNAL_ALPHA_RELEASE_SCOPE.md`](INTERNAL_ALPHA_RELEASE_SCOPE.md) |
| **Wave 2** | Kapsam dışı |

---

## Finding #1 — Panel görsel dil ve bilgi mimarisi

| Alan | Değer |
|------|-------|
| **ID** | UX-01 |
| **Kaynak** | Internal Alpha ekip gözlemi |
| **Özet** | Panel teknik olarak çalışsa da genel görünüm vaat edilen olgunluk seviyesini yansıtmıyor; sorun tekil ekranlarda değil, genel görsel dil ve bilgi mimarisinde. |
| **Durum** | **in_progress** |
| **PR** | [#510](https://github.com/candasoz01-cmd/lumos-core/pull/510) |
| **Dal** | `codex/internal-alpha-panel-polish` |

### Hedef (premium dark control-center)

- Parlak/ucuz mavi hissini kaldır; parliament-lacivert vurgu
- Bilgi yoğunluğunu azalt; kart, font, spacing, kontrast profesyonelleştir
- Sol menüde tekrarlayan marka metnini azalt
- Posta/Sosyal taslak alanlarını büyüt
- Kuantum teknik metinlerini sadeleştir (TR/EN)
- RB-17 inactive badge dili korunur (`Önizleme` / `Preview`)

### Uygulanan (bu PR)

- CSS token’ları: `--lumos-panel-navy`, parliament-lacivert accent, koyu yüzeyler
- Shell: header tagline, `panel-module-head` IA ritmi, nav sig gizleme
- Posta/Sosyal: bilgi kartları gizlendi, taslak proto büyütüldü
- i18n: kısaltılmış capability, sosyal/posta/kuantum metinleri; `header.subtitle`, `moduleGroups`

### Kabul kriteri (kapanış)

- [ ] Ekip en az bir haftalık checkpoint’te “panel olgunluk” onayı
- [ ] CI yeşil (`make test`, ui-smoke)
- [ ] P1-02 yolculuk regresyonu yok

---

*Son güncelleme: 2026-06-21 — finding #1 in_progress, PR #510.*
