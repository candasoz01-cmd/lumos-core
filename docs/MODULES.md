# Lumos Modül Envanteri

| Alan | Değer |
| --- | --- |
| Durum | Yürürlükte — 2026-07-20 taraması |
| Kural | Yüzdeler kanıta dayalı değerlendirmedir; kanıt sütunu boş bırakılmaz |
| Güncelleme | ROADMAP durum haritasıyla birlikte haftalık |

Durum sözlüğü: **Çalışıyor** (canlıda/testli kullanılabilir) · **Geliştiriliyor** ·
**Beklemede** (karar/rebase bekliyor) · **Fikir** (yalnız doküman/karar).

| Modül | Durum | % | Sürüm | Kanıt / not |
| --- | --- | --- | --- | --- |
| Core — agent runner, brain, evidence | Çalışıyor | 80 | v1 | `src/core` (55 py), `src/kando` (22 py); tam takım 1440 test yeşil |
| Kimlik — Google OAuth + oturum | Çalışıyor | 90 | v1 | `api/auth/*` canlı; hata sayfaları TR; state/CSRF korumalı |
| Chat — hosted bridge | Çalışıyor | 70 | v1 | `api/bridge/chat.js` OpenAI/Gemini; limit/UX eksikleri var |
| Panel | Çalışıyor | 70 | v1 | `ui/src/pages/panel.astro` canlı; 4.6k satır tek dosya (borç kaydı var) |
| Görev sistemi | Geliştiriliyor | 60 | v1 | `src/task_engine` (27 py); panel/TaskEngine store ayrıklığı (borç kaydı var) |
| Dosya akışı | Geliştiriliyor | 30 | v1 | patch/file executor var (`src/kando`); kullanıcı-yüzlü akış yok — **v0.5 hedefi** |
| Memory | Geliştiriliyor | 50 | v1 kısmi | `src/memory` secure store, chat memory prompt; Memory Graph (ADR-005) fikir |
| Security | Çalışıyor | 75 | v1 | `src/security` (19 py) crypto/guard/policy + testler; bazı katman prototip |
| iOS ★ | Geliştiriliyor | ~35 | v0.6 | Ayrı repo `candasoz01-cmd/Lumos`; Apple Sign-In + device context merge'lü; gövde sürüyor |
| Entegrasyonlar | Geliştiriliyor | 50 | v1 kısmi | `src/integrations` (48 py); katalog geniş, canlı `verify_connection` sınırlı |
| Board / Orchestration | Geliştiriliyor | 60 | v1 kısmi | #630/#629/#631/#632 main'de (sözleşme+projeksiyon+claim+gateway); gerçek kullanım 0 (borç kaydı var) |
| Deploy / Ops | Çalışıyor | 65 | v1 | Vercel canlı, CI 5 iş; Sentry/Axiom kodu hazır, env bağlı değil (borç kaydı var) |
| API (public yüzey) | Geliştiriliyor | 55 | v1 kısmi | `api/*` 12 uç; sözleşme dokümanı yok |
| Media | Fikir | 10 | **v2** | video executor parçası; STOP LIST kapsamında |
| Quantum | Fikir | 5 | **v2** | ADR-001/013 yalnız doküman; STOP LIST kapsamında |
| Mail | Kapatıldı | — | **v2** | #616 kapatıldı (2026-07-20 kararı); iş ADR-009 ve dokümanlarda kayıtlı |
| Identity/Lumos ID gateway | Geliştiriliyor | 40 | v1 kısmi | ADR-015/016 sözleşmeleri + provider iskeleti main'de |
| Vault / credential context | Beklemede | 20 | karar bekliyor | #633 draft (GitHub read-only connector); v1 kapsam kararı açık |
