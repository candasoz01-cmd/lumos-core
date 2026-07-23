# docs/analysis/ — mimari analiz paketi indeksi (2026-07-23 seti)

> **Kapsam notu:** Bu indeks `docs/analysis/`'daki tüm dosyaların tam listesi değildir — yalnızca 2026-07-23'te üretilen, birbirini tamamlayan iki raporu bağlar. Dizindeki diğer dosyalar kendi tarih/konu başlıklarıyla ayrı ayrı okunmalı.

## Core/Local/Sentinel isimlendirme + mimari analiz seti

| Tarih | Rapor | Amaç |
|-------|-------|------|
| 2026-07-23 | [Naming & Mimari Rapor](./lumos-2026-service-mimari-rapor.md) | Kando/Cando/Bando → Core/Local/Sentinel isimlendirme kararının durumu: `candasoz01-cmd/Lumos` (canonical) ↔ `lumos-core` (bu repo) arası uygulama zinciri, kanıt zinciri, açık lojistik adımlar. v2 — commit `aba81ee`, zaman damgalı kapsam düzeltmesi `ac92e2d` ile güncellendi. |
| 2026-07-23 | [Capability Domains Analizi](./lumos-2026-capability-domains-mimari-tasarim.md) | Identity / Memory / Voice / Vision / Connect'in `lumos-core` içindeki gerçek kod karşılığı, olgunluk durumu, Core/Local/Sentinel ile ilişkisi. Teknik tanımlayıcı cutover'ı ayrı planda bırakır. |

**Okuma sırası:** Önce naming raporu (omurga kararının durumu), sonra capability-domains raporu (omurga dışındaki beş alanın nereye oturabileceği) — ikincisi birincisinin bulgularına dayanır.

**Ortak disiplin (her iki raporda da uygulanır):** karar durumu ile uygulama durumu ayrı yazılır; iddialar dosya/satır/PR numarası ile kanıtlanır; rapor başında tarih/kapsam notu bulunur — bkz. her raporun kendi "Kapsam notu" satırı.
