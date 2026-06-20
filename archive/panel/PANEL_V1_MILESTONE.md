# Lumos Panel v1 — Milestone Özeti

Panel hattı burada bilinçli olarak kilitlenmiştir. Sonraki büyük adım gerçek backend entegrasyonudur.

---

## Hazır ekranlar

Dashboard, Tasks, Sandbox, Config, Identity, Keystore, Trash, Logs, System. Hash routing: `#dashboard`, `#tasks`, `#sandbox`, `#config`, `#identity`, `#keystore`, `#trash`, `#logs`, `#system`.

## Ortak bileşenler

Sidebar, Topbar, StatusBadge, MetricCard, SectionCard, EmptyState, EventList, DetailPanel, ViewHeader.

## Demo senaryo sistemi

Üst çubukta senaryo seçici: Normal operasyon, Korumalı alan açık, Guard engelli, Config uyarı, Silinenler dolu. Tüm ekran verisi seçilen senaryoya göre güncellenir.

## Adapter katmanı

`getDashboardData()`, `getTasksData()`, `getSandboxData()` vb. tek kaynaktan normalize veri döner. Kaynak: demo stub veya (isteğe bağlı) fixture + mapper. Gerçek entegrasyonda sadece bu katmanda veri kaynağı değişir.

## Contract / stub yapısı

`js/contracts.js`: CONTRACTS (ekran şemaları), build*Stub, normalize*. Ekranlar contract çıktısını okur; eksik alanlar güvenli varsayılana çekilir.

## Backend binding map

`BACKEND_BINDING_MAP.md`: Her ekranın backend kaynak adayları, adapter notu, boşluk/risk. Gerçek entegrasyon öncesi referans.

## Payload fixture + mapper hazırlığı

`js/fixtures.js`: Backend-benzeri payload örnekleri, map*PayloadToPanelData. Üst çubukta "Veri kaynağı: Demo | Fixture" ile provası yapılabilir. Detay: `BACKEND_PAYLOAD_FIXTURES.md`.

## Bilinçli olarak yapılmayanlar

Gerçek fetch/API, auth, WebSocket, canlı veri, yeni ekran, backend tarafında değişiklik. Panel sadece mock/stub ve fixture ile çalışır.

## Sonraki büyük adım: gerçek backend entegrasyonu

API yanıtı → mevcut mapper/contract katmanına beslenecek; ekranlar aynı contract'ı okumaya devam eder. Binding map ve fixture/mapper referans alınacak.
