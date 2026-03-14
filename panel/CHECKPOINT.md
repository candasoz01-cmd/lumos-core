# Lumos Panel v1 — Teknik Checkpoint

## Hazır ekranlar

| Ekran           | Hash         |
|-----------------|--------------|
| Gösterge Paneli | `#dashboard` |
| Görevler        | `#tasks`     |
| Korumalı Alan   | `#sandbox`   |
| Yapılandırma    | `#config`    |
| Kimlik          | `#identity`  |
| Anahtar Kasası  | `#keystore`  |
| Silinenler      | `#trash`     |
| Kayıtlar        | `#logs`      |
| Sistem Durumu   | `#system`    |

## Ortak bileşenler

- **Layout:** Sidebar, Topbar
- **Görsel:** StatusBadge, MetricCard, SectionCard, ViewHeader, EmptyState
- **Liste / detay:** EventList, DetailPanel
- **Filtre:** log-tabs, task-filters (delegation ile)

## Mock state kapsamı

- Tek kaynak: `js/app.js` içinde `mockState`
- Kapsanan: appMode, sandboxMode, sandboxSource, writingBaseDir, workspaceName, branchName, basePath, guardStatus, recentEvents, warnings, trashItems, trashLocation, logItems, configSnapshot, identityState, keystoreState, systemHealth, taskList, taskFilter, selectedTaskId, selectedTrashId, logFilter
- Tüm ekranlar bu state’ten beslenir; backend/API yok.

## Bilerek dışarıda bırakılanlar

- Gerçek backend / canlı API
- Auth, oturum, passphrase girişi
- WebSocket / canlı güncelleme
- Yeni ekran veya büyük modül
- Kompleks ayar sistemi (sadece config özeti gösterimi)
- Hash routing dışında routing

## Sonraki olası küçük işler

- (Bu turda yapıldı: boş durum metni, kart başlıkları TR, sistem durumu başlıkları TR, görev filtresi Tamamlandı, dashboard guard tekrarı, README kapsam özeti.)
- İleride: rozet görsel ince ayarı, arama kutusu işlevi (şu an placeholder).
