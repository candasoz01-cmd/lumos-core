# Lumos Kaynak Modu — Katman Kaydı (Stub)

| Alan | Değer |
|------|-------|
| Tarih | 2026-06-26 |
| Tür | Katman envanteri / yol haritası |
| Ana mimari | [`lumos-resource-mode-advisor.md`](./lumos-resource-mode-advisor.md) |

Bu belge yedi kaynak katmanı için **izleme durumu** ve **tipik aktif sinyalleri** listeler. Uygulama kodu: `src/integrations/resource_mode_advisor.py` (`ResourceLayer` enum).

---

## Özet tablo

| Katman | `ResourceLayer` | Tracker | Mod önerisi | Tipik aktif sinyaller |
|--------|-----------------|---------|-------------|------------------------|
| Quantum | `quantum` | **implemented** | **implemented** | `connect`, `list_catalog`, Aer smoke, job stub |
| Cyber | `cyber` | planned | planned | Güvenlik taraması, threat feed okuma, cihaz alarm |
| Vision | `vision` | planned | planned | Kamera/frame analiz isteği, OCR batch |
| Voice | `voice` | planned | planned | STT/TTS oturumu, sürekli dinleme |
| Integrations | `integrations` | planned | planned | OAuth refresh, connector poll, webhook dinleme |
| GPU | `gpu` | planned | planned | Yerel inference, model yükleme, CUDA oturumu |
| Local models | `local_models` | planned | planned | Ollama/llama.cpp oturumu, model swap |

**Tracker durumu:** `implemented` = `record_event` üretiyor; `planned` = enum + dokümantasyon, henüz olay üreticisi yok.

---

## Katman notları

### Quantum (ilk uygulama)

- Kod: `quantum_usage_tracker.py` → `resource_mode_advisor` (`ResourceLayer.QUANTUM`).
- Provider: `quantum_provider.py` — `list_catalog`, `connect`, `usage_recommendation`.
- Detay: [`lumos-quantum-layer-architecture.md`](./lumos-quantum-layer-architecture.md).

### Cyber

- AnchorUSB / güvenlik çerçevesi ile kavramsal hizalı; ayrı `ResourceLayer.CYBER` telemetrisi henüz yok.
- Planlanan sinyaller: plugin enable, scan tetikleme, alarm ack.

### Vision

- Planlanan sinyaller: frame capture, vision API çağrısı (onaylı), batch OCR.

### Voice

- Planlanan sinyaller: mikrofon oturumu açma, TTS stream, sürekli dinleme modu.

### Integrations

- Mail, GitHub, Slack vb. connector kullanımı; OAuth token refresh sayacı.
- Geniş entegrasyon omurgası: [`integrations-overview.md`](../integrations-overview.md).

### GPU

- Yerel GPU inference / render; sıcak model tutma kararı.

### Local models

- Ollama, llama.cpp, yerel embedding; model keep-alive vs on-demand.

---

## Ortak eşikler (Faz 1)

Tüm katmanlar aynı `recommend_mode` eşiklerini kullanır (katmana özel eşik Faz 2+):

| Sinyal | Eşik | Öneri |
|--------|------|-------|
| `connect` / 24 saat | ≥ 3 | active |
| Olay / 7 gün | ≥ 10 | active |
| Boşta kalma | ≥ 15 gün | passive |
| Yetersiz geçmiş | < 2 olay ve < 3 connect | insufficient_data → varsayılan passive |

---

## Sonraki adımlar

1. Cyber / vision / voice için `record_event` üreticileri (onaylı aksiyonlardan sonra).
2. Panel/CLI «Geç» / «Hayır aktif kalsın» UX — `propose_mode_change` yükü.
3. Faz 2: hafta içi/sonu heuristik önerisi (yine onaylı uygulama).
