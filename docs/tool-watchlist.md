# Araç ve teknoloji takip listesi — kalıcı repo kaydı

**Durum:** Takip belgesi (otomatik entegrasyon yok).  
**Genişletilmiş canonical:** `docs/memory/tools-technology-watchlist.md`, `docs/memory/external-integrations-permissions.md`

Bu dosya, projeye **hemen eklenmeyecek** araç ve entegrasyon adaylarını kayıt altında tutar. Watchlist ≠ entegrasyon.

---

## Değerlendirme ilkesi

| # | İlke | Statü |
|---|------|--------|
| TW-001 | Araçlar **rastgele veya toplu** eklenmez. | **aktif kural** |
| TW-002 | İhtiyaç doğduğunda **tek parça** değerlendirilir; çekirdek panel/görev/güvenlik akışı korunur. | **aktif kural** |
| TW-003 | Faydalı görünen araçlar önce **düşük riskli modda** (read/report) test edilir; sonra sürece alınır. | **aktif kural** |
| TW-004 | Bu listedeki maddeler otomatik uygulanmaz. | **aktif kural** |

---

## Cursor ve geliştirme araçları

| Araç | Statü | Not |
|------|--------|-----|
| **Cursor Automations** | **ileride değerlendirilecek** | Zamanı gelince proaktif hatırlatılacak; hemen projeye bağlanmayacak. Uygun aşamada güvenli read/report mode gibi düşük riskli kullanım değerlendirilecek. |
| **Google AI Studio + Cursor + Android Studio** | **takip maddesi** | Mobil/prototip geliştirme akışı — migrated not |

---

## OpenAI ajan ve ses araçları

| Araç / yetenek | Statü | Değerlendirme odağı |
|----------------|--------|---------------------|
| **OpenAI Agents SDK** | **takip maddesi** | Kontrollü kullanıcı-ajan aksiyonları; onay modeli |
| **Realtime / sesli ajan modelleri** | **takip maddesi** | Ses-yazı sürekliliği; STT sonrası güvenlik sınırı |
| **Computer Use** | **takip maddesi** | Onaysız dış yazma riski; izin kapısı gerekir (OD-012) |
| **Codex Plugins** | **takip maddesi** | Public repo + onay modeli uyumu |

**Not:** Sesli mod, yazılı görev motoruna bağlı giriş/geri bildirim katmanı olarak tasarlanır; STT sonrası bağlam/niyet/güvenlik tutarlılık kontrolü zorunludur (`docs/product-rules.md` PR-050–052).

---

## Connector ve dış sistem araçları

| Sistem | Statü | Not |
|--------|-------|-----|
| **GitHub** | **takip maddesi** | Connector; tek tek evaluate |
| **Slack** | **takip maddesi** | Connector; tek tek evaluate |
| **Google Drive** | **takip maddesi** | Connector; tek tek evaluate |
| **Linear** | **takip maddesi** | Connector; tek tek evaluate |

---

## Reverse engineering / prototip (düşük öncelik)

| Araç / kategori | Statü | Not |
|-----------------|--------|-----|
| **Ghidra** | **ileride değerlendirilecek** | RE/firmware; public OSS sınırı (OD-029) |
| **Çin menşeli vibe coding araçları** | **ileride değerlendirilecek** | Güvenlik ve veri sınırı testi gerekir (OD-030) |

---

## CI / kapsam dışı bırakılan araç maddeleri

| ID | Madde özeti | Statü | Not |
|----|-------------|--------|-----|
| TW-D01 | Mail entegrasyonu (okuma/özet) | **geçici ertelendi** | OD-031 |
| TW-D02 | Takvim / kişiler | **karar onaylı — uygulama bekliyor** | OD-032 — [`calendar-contacts-decision.md`](memory/calendar-contacts-decision.md) |
| TW-D03 | Çalışma araçları connector rollout (GitHub, Slack, Drive, Linear, Notion, Asana) | **karar onaylı — uygulama bekliyor** | OD-033 — [`work-tools-connectors-decision.md`](memory/work-tools-connectors-decision.md) |

---

## Kabul kriterleri (watchlist → değerlendirme)

Bir madde uygulamaya geçmeden önce:

1. Onay modeli ve çekirdek sözleşme ile uyum
2. Public repo / demo-safe sınırı
3. Tek parça, dar kapsamlı pilot
4. Karar kaydı: `docs/decision-log.md`

---

Son güncelleme: 2026-06-18
