# Lumos Kaynak Modu Danışmanı — Mimari

| Alan | Değer |
|------|-------|
| Tarih | 2026-06-26 |
| Tür | Mimari / davranış sözleşmesi |
| Kapsam | Tüm kaynak katmanları (quantum, cyber, vision, voice, integrations, gpu, local_models) |
| İlk uygulama | [Quantum Layer](./lumos-quantum-layer-architecture.md) |

---

## İlke: Gözlemler → Önerir → Onay alır → Uygular

Lumos karakterinin kaynak kullanımında **asla otomatik mod değiştirmez**. Akış:

1. **Gözlemle** — `.lumos/resource_usage.jsonl` içine katman bazlı olaylar yazılır (`record_event`).
2. **Öner** — `recommend_mode` / `propose_mode_change` istatistik ve eşiklere göre öneri üretir.
3. **Onay al** — Kullanıcı açıkça «Geç» veya «Hayır aktif kalsın» der; sessiz geçiş yok.
4. **Uygula** — Yalnızca `apply_mode_change(..., user_approved=True)` ile `.lumos/resource_modes.json` güncellenir.

Bu ilke `SECURITY_NEVER_AUTO` ve karar sözleşmesi ile hizalıdır: **mod değişimi dış etkili bir karardır; onaysız uygulanmaz.**

---

## Modlar

| Mod (kod) | Kullanıcı dili | Anlam |
|-----------|----------------|-------|
| **active** | Aktif | Sık kullanım — sıcak oturum, kısa yeniden bağlanma veya arka plan hazırlığı mantıklı |
| **passive** | Beklemeli | Seyrek kullanım — ihtiyaç anında bağlan; gereksiz kaynak tutma |
| **insufficient_data** | Yetersiz veri | Öneri için yeterli geçmiş yok; varsayılan **passive** |

### Aktif mod — tipik sinyaller

- Son 24 saatte ≥ **3** `connect` olayı **veya**
- Son 7 günde ≥ **10** herhangi bir kullanım olayı

### Beklemeli mod — tipik sinyaller

- Eşik altı kullanım **veya**
- Son **15+** gün hiç kullanım yok (boşta kalma)

---

## Veri yolları (çekirdek state değil)

| Dosya | Amaç | Çekirdek state? |
|-------|------|-----------------|
| `.lumos/resource_usage.jsonl` | Katman bazlı kullanım olayları (append-only JSONL) | Hayır — integration telemetry |
| `.lumos/resource_modes.json` | Kullanıcı onaylı uygulanmış modlar | Hayır — tercih kaydı |

`CORE_STATE_PATH_NAMES` (`workspace_contract.py`) listesinde yoktur; sandbox/çekirdek overwrite kurallarına tabi değildir.

---

## Faz planı

### Faz 1 (bu belge + kod)

- Sabit eşikler (yukarıdaki tablo).
- Paylaşılan Python modülü: `src/integrations/resource_mode_advisor.py`.
- Quantum katmanı ilk tam entegrasyon: `quantum_usage_tracker.py` → paylaşılan danışman.
- CLI/panel için `propose_mode_change` yükü; uygulama yalnızca onaylı `apply_mode_change`.

### Faz 2 (gelecek — dokümantasyon)

- Hafta içi / hafta sonu örüntü öğrenme (basit heuristikler).
- Örn. «Pazartesi–Cuma 09:00–18:00 aktif, hafta sonu passive» önerisi; yine **NEVER_AUTO** — yalnızca öneri + onay.

---

## NEVER_AUTO — mod değişimi

| ID | Asla otomatik | Gerekçe |
|----|---------------|---------|
| RM-01 | Katman modunu kullanıcı onayı olmadan değiştirmek | Davranış / kaynak tercihi; geri alınması zor algı |
| RM-02 | Yetersiz veride «active»e zorla geçmek | Yanlış sıcak oturum maliyeti |
| RM-03 | Öğrenilmiş haftalık örüntüyü sessizce uygulamak | Faz 2 bile olsa onay şart |

Kod: `apply_mode_change` `user_approved=False` iken `approval_required` döner veya `ResourceModeApprovalRequired` fırlatır.

---

## API özeti

```text
record_event(layer, action, metadata?)
recommend_mode(layer) → { recommended_mode, reason, stats, ... }
propose_mode_change(layer) → UI/CLI payload (never_auto: true)
apply_mode_change(layer, mode, user_approved=True) → ApplyModeResult
```

Katman enum: `ResourceLayer` — `quantum`, `cyber`, `vision`, `voice`, `integrations`, `gpu`, `local_models`.

---

## Panel UX (ORAA)

Panel, yerel görev sunucusu (`panel/scripts/panel_tasks_server.py`, varsayılan `:8766`) üzerinden ORAA akışını sunar: `GET /resource-mode/propose?layer=quantum` öneri JSON döner; kullanıcı **Geç** veya **Hayır, aktif kalsın** ile `POST /resource-mode/apply` çağrılır (`user_approved: true|false`). Kart yalnızca köprü bağlı veya yerel görev API erişilebilirken görünür; mod değişimi **asla otomatik uygulanmaz** — yalnızca açık onaylı `apply_mode_change`.

Destek / debug raporları için aynı ORAA düzeni: [support-report-oraa.md](../templates/support-report-oraa.md).

---

## Katman kaydı

Detaylı katman tablosu: [`lumos-resource-mode-layers.md`](./lumos-resource-mode-layers.md).

---

## İlgili belgeler

- [Quantum Layer mimarisi](./lumos-quantum-layer-architecture.md) — ilk uygulama
- [Grounded Phase Roadmap](./grounded-phase-roadmap.md) — Katman 3 davranış hafızası
- [Karar sözleşmesi](../lumos-karar-sozlesmesi.md)
