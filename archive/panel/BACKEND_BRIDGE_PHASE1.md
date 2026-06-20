# Backend Bridge — Phase 1

**Bu turda gerçek entegrasyon yapılmadı.** Sadece bridge/provider giriş noktası hazırlandı; fallback akışı korundu.

## Yapılanlar

- **Veri kaynağı soyutlaması:** Demo, fixture ve gerçek backend ayrımı netleştirildi. Render katmanı tek kaynaktan besleniyor gibi çalışır.
- **Backend bridge:** `js/backend-bridge.js` — `readBackendDashboardState()`, `readBackendSandboxState()`, `readBackendSystemState()`. Bugün no-op (null); yarın gerçek okuma buradan bağlanacak.
- **Source provider:** `getDashboardSourceData()`, `getSandboxSourceData()`, `getSystemSourceData()`. Önce backend, yoksa fixture/demo fallback.
- **Adapter zinciri:** backend/fixture → mapper → contract; demo → stub → contract. Sadece Dashboard, Korumalı Alan (Sandbox), Sistem Durumu (System) bu akışa alındı.

## Kapsam dışı (bu turda)

Config, Identity, Keystore, Trash, Logs, Tasks ekranlarına dokunulmadı; mevcut fixture/demo akışı aynı kaldı.

## Sonraki adım

Gerçek veri sağlandığında `LumosBackendBridge.readBackend*` implementasyonu doldurulacak; panel aynı contract'ı okumaya devam eder, fallback bozulmaz.
